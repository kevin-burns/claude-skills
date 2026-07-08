"""Render Excalidraw JSON to PNG using Playwright + headless Chromium.

Rendering is offline: the fonts are vendored under ``vendor/`` and the Excalidraw
engine (``vendor/excalidraw.mjs``) is downloaded once on first run from a pinned,
sha256-verified GitHub Release (see ``vendor/bundle.lock.json``) — like
``playwright install chromium``. Everything is then served over a loopback HTTP
server, so subsequent renders never touch the network.

Usage:
    cd .claude/skills/excalidraw-diagram/references
    uv run python render_excalidraw.py <path-to-file.excalidraw> [--output path.png] [--scale 2] [--width 1920]

First-time setup:
    cd .claude/skills/excalidraw-diagram/references
    uv sync
    uv run playwright install chromium
"""

from __future__ import annotations

import argparse
import functools
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib
import os
import tempfile
import urllib.error
import urllib.request

REFERENCES_DIR = Path(__file__).parent
MODULE_READY_TIMEOUT_MS = 8000
RENDER_TIMEOUT_MS = 15000

VENDOR_DIR = REFERENCES_DIR / "vendor"
BUNDLE_PATH = VENDOR_DIR / "excalidraw.mjs"
LOCK_PATH = VENDOR_DIR / "bundle.lock.json"
DOWNLOAD_TIMEOUT_S = 30
_DOWNLOAD_CHUNK = 65536


class BundleError(Exception):
    """The render-engine bundle is missing and could not be fetched/verified."""


def _load_bundle_lock() -> dict:
    """Read vendor/bundle.lock.json (url + sha256 for the render engine)."""
    try:
        return json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise BundleError(
            f"references/vendor/bundle.lock.json is missing or invalid ({e}); "
            "cannot locate the render engine."
        )


def _download_and_verify(url: str, sha256: str, dest: Path) -> None:
    """Download ``url`` into ``dest`` atomically, verifying it hashes to ``sha256``.

    Streams to a temp file beside ``dest``, hashing as it goes; on a hash
    mismatch (or any error) it removes the temp file and raises, so a failed
    fetch never leaves a partial or unverified bundle in place.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=".excalidraw.mjs.", suffix=".part")
    tmp = Path(tmp_name)
    try:
        digest = hashlib.sha256()
        req = urllib.request.Request(url, headers={"User-Agent": "excalidraw-diagram-skill"})
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_S) as resp:
            while True:
                chunk = resp.read(_DOWNLOAD_CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual != sha256:
            raise BundleError(
                f"downloaded bundle failed its integrity check (expected {sha256}, "
                f"got {actual}). Refusing to use it. This may mean the release asset "
                "was changed. Rebuild with references/scripts/vendor.sh."
            )
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()


def _ensure_bundle() -> Path:
    """Return the render-engine bundle path, downloading it once if absent.

    A present bundle is used as-is (no network, no re-hash) — it was verified at
    download time. This mirrors ``playwright install chromium``: the engine is
    fetched once, then every render is fully offline.
    """
    if BUNDLE_PATH.exists():
        return BUNDLE_PATH
    lock = _load_bundle_lock()
    url = lock["url"]
    sha256 = lock["sha256"]
    print("Downloading the Excalidraw render engine (first run, ~8 MB)...", file=sys.stderr)
    try:
        _download_and_verify(url, sha256, BUNDLE_PATH)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise BundleError(
                f"{url} returned 404 — the release asset for excalidraw "
                f"{lock.get('excalidraw_version', '?')} hasn't been published yet. "
                "Build it locally with references/scripts/vendor.sh."
            )
        raise BundleError(
            f"couldn't download the Excalidraw render engine from {url}: HTTP {e.code}. "
            "Check your connection, or build it locally with references/scripts/vendor.sh."
        )
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise BundleError(
            f"couldn't download the Excalidraw render engine from {url}: {e}. "
            "Check your connection, or build it locally with references/scripts/vendor.sh."
        )
    return BUNDLE_PATH


def validate_excalidraw(data: dict) -> list[str]:
    """Validate Excalidraw JSON structure. Returns list of errors (empty = valid)."""
    errors: list[str] = []

    if data.get("type") != "excalidraw":
        errors.append(f"Expected type 'excalidraw', got '{data.get('type')}'")

    if "elements" not in data:
        errors.append("Missing 'elements' array")
    elif not isinstance(data["elements"], list):
        errors.append("'elements' must be an array")
    elif len(data["elements"]) == 0:
        errors.append("'elements' array is empty — nothing to render")

    return errors


def compute_bounding_box(elements: list[dict]) -> tuple[float, float, float, float]:
    """Compute bounding box (min_x, min_y, max_x, max_y) across all elements."""
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for el in elements:
        if el.get("isDeleted"):
            continue
        x = el.get("x", 0)
        y = el.get("y", 0)
        w = el.get("width", 0)
        h = el.get("height", 0)

        # For arrows/lines, points array defines the shape relative to x,y
        if el.get("type") in ("arrow", "line") and "points" in el:
            for px, py in el["points"]:
                min_x = min(min_x, x + px)
                min_y = min(min_y, y + py)
                max_x = max(max_x, x + px)
                max_y = max(max_y, y + py)
        else:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + abs(w))
            max_y = max(max_y, y + abs(h))

    if min_x == float("inf"):
        return (0, 0, 800, 600)

    return (min_x, min_y, max_x, max_y)


class _QuietHandler(SimpleHTTPRequestHandler):
    """Serves the references/ directory, silently, with correct module MIME types."""

    # Ensure ES modules are served as JavaScript (strict MIME checking blocks
    # octet-stream). Python's default map doesn't always include .mjs.
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".mjs": "text/javascript",
        ".js": "text/javascript",
    }

    def log_message(self, *args, **kwargs):  # noqa: D401 - silence access logs
        pass


def _start_server() -> tuple[ThreadingHTTPServer, int]:
    """Start a loopback HTTP server rooted at references/. Returns (server, port)."""
    handler = functools.partial(_QuietHandler, directory=str(REFERENCES_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def _dump_diagnostics(console_errors: list[str], page_errors: list[str], failed_requests: list[str]) -> None:
    """Print collected browser diagnostics so failures are self-explanatory."""
    if console_errors:
        print("  Console messages:", file=sys.stderr)
        for msg in console_errors:
            print(f"    {msg}", file=sys.stderr)
    if page_errors:
        print("  Page errors:", file=sys.stderr)
        for msg in page_errors:
            print(f"    {msg}", file=sys.stderr)
    if failed_requests:
        print("  Failed requests:", file=sys.stderr)
        for req in failed_requests:
            print(f"    {req}", file=sys.stderr)
    if not (console_errors or page_errors or failed_requests):
        print("  (no console errors, page errors, or failed requests captured)", file=sys.stderr)


def render(
    excalidraw_path: Path,
    output_path: Path | None = None,
    scale: int = 2,
    max_width: int = 1920,
) -> Path:
    """Render an .excalidraw file to PNG. Returns the output PNG path."""
    # Import playwright here so validation errors show before import errors
    try:
        from playwright.sync_api import TimeoutError as PWTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed.", file=sys.stderr)
        print("Run: cd .claude/skills/excalidraw-diagram/references && uv sync && uv run playwright install chromium", file=sys.stderr)
        sys.exit(1)

    # Read and validate
    raw = excalidraw_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {excalidraw_path}: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_excalidraw(data)
    if errors:
        print("ERROR: Invalid Excalidraw file:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    # Ensure the render engine is present (downloaded once on first run), then use it.
    try:
        _ensure_bundle()
    except BundleError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Compute viewport size from element bounding box
    elements = [e for e in data["elements"] if not e.get("isDeleted")]
    min_x, min_y, max_x, max_y = compute_bounding_box(elements)
    padding = 80
    diagram_w = max_x - min_x + padding * 2
    diagram_h = max_y - min_y + padding * 2

    # Cap viewport width, let height be natural
    vp_width = min(int(diagram_w), max_width)
    vp_height = max(int(diagram_h), 600)

    if output_path is None:
        output_path = excalidraw_path.with_suffix(".png")

    # Diagnostics collected from the browser so a failure explains itself
    # instead of surfacing as an opaque timeout.
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[str] = []

    server, port = _start_server()
    template_url = f"http://127.0.0.1:{port}/render_template.html"

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                if "Executable doesn't exist" in str(e) or "browserType.launch" in str(e):
                    print("ERROR: Chromium not installed for Playwright.", file=sys.stderr)
                    print("Run: cd .claude/skills/excalidraw-diagram/references && uv run playwright install chromium", file=sys.stderr)
                    sys.exit(1)
                raise

            page = browser.new_page(
                viewport={"width": vp_width, "height": vp_height},
                device_scale_factor=scale,
            )

            # Attach listeners BEFORE navigation so nothing is missed.
            page.on("console", lambda m: console_errors.append(f"[{m.type}] {m.text}") if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e: page_errors.append(str(e)))
            page.on("requestfailed", lambda r: failed_requests.append(f"{r.url} — {r.failure}"))

            page.goto(template_url)

            # Wait for the vendored module to load. Because everything is local,
            # this should be near-instant; a timeout means something is broken,
            # so report the real cause instead of a bare TimeoutError.
            try:
                page.wait_for_function("window.__moduleReady === true", timeout=MODULE_READY_TIMEOUT_MS)
            except PWTimeoutError:
                print("ERROR: Excalidraw engine failed to load (window.__moduleReady never set).", file=sys.stderr)
                _dump_diagnostics(console_errors, page_errors, failed_requests)
                browser.close()
                sys.exit(1)

            # Inject the diagram data and render
            json_str = json.dumps(data)
            result = page.evaluate(f"window.renderDiagram({json_str})")

            if not result or not result.get("success"):
                error_msg = result.get("error", "Unknown render error") if result else "renderDiagram returned null"
                print(f"ERROR: Render failed: {error_msg}", file=sys.stderr)
                _dump_diagnostics(console_errors, page_errors, failed_requests)
                browser.close()
                sys.exit(1)

            page.wait_for_function("window.__renderComplete === true", timeout=RENDER_TIMEOUT_MS)

            svg_el = page.query_selector("#root svg")
            if svg_el is None:
                print("ERROR: No SVG element found after render.", file=sys.stderr)
                _dump_diagnostics(console_errors, page_errors, failed_requests)
                browser.close()
                sys.exit(1)

            svg_el.screenshot(path=str(output_path))
            browser.close()
    finally:
        server.shutdown()

    # Any failed request is a red flag: rendering is meant to be fully local.
    if failed_requests:
        print("WARNING: network requests failed during a render that should be fully offline:", file=sys.stderr)
        for req in failed_requests:
            print(f"  - {req}", file=sys.stderr)
        print("Fonts or the engine may not have loaded correctly.", file=sys.stderr)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Excalidraw JSON to PNG")
    parser.add_argument("input", type=Path, help="Path to .excalidraw JSON file")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output PNG path (default: same name with .png)")
    parser.add_argument("--scale", "-s", type=int, default=2, help="Device scale factor (default: 2)")
    parser.add_argument("--width", "-w", type=int, default=1920, help="Max viewport width (default: 1920)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    png_path = render(args.input, args.output, args.scale, args.width)
    print(str(png_path))


if __name__ == "__main__":
    main()
