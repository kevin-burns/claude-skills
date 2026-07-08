"""Tests for the render-engine bundle fetch/verify logic.

No network: fetches are exercised with file:// URLs pointing at temp fixtures,
which run the real urllib download + hashing + atomic-rename path.
"""
import hashlib
import json
from pathlib import Path

import pytest

import render_excalidraw as rx


def _write(path: Path, data: bytes) -> str:
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_download_and_verify_places_file(tmp_path):
    src = tmp_path / "source.mjs"
    digest = _write(src, b"export const exportToSvg = 1;\n")
    dest = tmp_path / "vendor" / "excalidraw.mjs"

    rx._download_and_verify(src.as_uri(), digest, dest)

    assert dest.read_bytes() == b"export const exportToSvg = 1;\n"
    # no leftover .part temp files beside the destination
    assert list(dest.parent.glob("*.part")) == []


def test_download_and_verify_rejects_bad_hash(tmp_path):
    src = tmp_path / "source.mjs"
    _write(src, b"tampered payload")
    dest = tmp_path / "vendor" / "excalidraw.mjs"

    with pytest.raises(rx.BundleError) as exc:
        rx._download_and_verify(src.as_uri(), "0" * 64, dest)

    assert "integrity check" in str(exc.value)
    assert not dest.exists()
    assert list(dest.parent.glob("*.part")) == []


def test_ensure_bundle_present_skips_download(tmp_path, monkeypatch):
    present = tmp_path / "excalidraw.mjs"
    present.write_bytes(b"already here")
    # Lock points at a nonexistent URL: if _ensure_bundle tried to fetch, it would fail.
    lock = tmp_path / "bundle.lock.json"
    lock.write_text(json.dumps({
        "url": (tmp_path / "does-not-exist.mjs").as_uri(),
        "sha256": "deadbeef",
        "excalidraw_version": "0.18.1",
    }))
    monkeypatch.setattr(rx, "BUNDLE_PATH", present)
    monkeypatch.setattr(rx, "LOCK_PATH", lock)

    assert rx._ensure_bundle() == present
    assert present.read_bytes() == b"already here"


def test_ensure_bundle_downloads_when_absent(tmp_path, monkeypatch):
    src = tmp_path / "source.mjs"
    digest = _write(src, b"fetched engine")
    dest = tmp_path / "vendor" / "excalidraw.mjs"
    lock = tmp_path / "bundle.lock.json"
    lock.write_text(json.dumps({
        "url": src.as_uri(), "sha256": digest, "excalidraw_version": "0.18.1",
    }))
    monkeypatch.setattr(rx, "BUNDLE_PATH", dest)
    monkeypatch.setattr(rx, "LOCK_PATH", lock)

    assert rx._ensure_bundle() == dest
    assert dest.read_bytes() == b"fetched engine"


def test_load_bundle_lock_missing_is_clear_error(tmp_path, monkeypatch):
    monkeypatch.setattr(rx, "LOCK_PATH", tmp_path / "nope.json")
    with pytest.raises(rx.BundleError) as exc:
        rx._load_bundle_lock()
    assert "bundle.lock.json" in str(exc.value)


def test_ensure_bundle_download_failure_is_clear_error(tmp_path, monkeypatch):
    # Bundle absent + an unreachable URL (nonexistent file://) => clean BundleError,
    # no hang, no partial file. Stands in for "offline + missing engine".
    dest = tmp_path / "vendor" / "excalidraw.mjs"
    lock = tmp_path / "bundle.lock.json"
    lock.write_text(json.dumps({
        "url": (tmp_path / "missing.mjs").as_uri(),
        "sha256": "0" * 64,
        "excalidraw_version": "0.18.1",
    }))
    monkeypatch.setattr(rx, "BUNDLE_PATH", dest)
    monkeypatch.setattr(rx, "LOCK_PATH", lock)

    with pytest.raises(rx.BundleError) as exc:
        rx._ensure_bundle()
    assert "couldn't download" in str(exc.value)
    assert not dest.exists()
