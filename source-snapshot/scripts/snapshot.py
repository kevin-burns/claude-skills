#!/usr/bin/env python3
"""snapshot.py — resilient content extractor for the source-snapshot skill.

Picks an available extractor by content type, falls back when the preferred one is
missing, and fails cleanly (never crashes, never fabricates) when none is available.
Writes a provenance-stamped Markdown artifact and emits a JSON envelope.

Two modes:
  plan   Decide which extractor *would* be used given what's installed (no fetch).
         Deterministic; used by the eval and to dry-run before committing to a fetch.
  run    Actually extract a URL/file with the chosen extractor and write the artifact.

Extractor routing:
  prose (articles/docs-as-reading)  ->  defuddle > readability > markitdown
  doc   (PDF/Office/structured)     ->  markitdown
markitdown is the most reliable fallback (works via `uvx 'markitdown[all]'` even with
no local install). Resolution can be overridden for tests/CI with --have.

Exit codes: 0 ok | 1 no-extractor / not-found | 2 usage | 3 extraction error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK, EXIT_NONE, EXIT_USAGE, EXIT_RUN = 0, 1, 2, 3

# Preference order per content type. First available wins.
PREFERENCE = {
    "prose": ["defuddle", "readability", "markitdown"],
    "doc": ["markitdown"],
}

# How each extractor handles a source, and how to detect it. Detection is conservative:
# only tools runnable *without* a network download count as available (markitdown also
# counts via uvx, which may fetch on first use — flagged as fetchable).
EXTRACTORS = {
    "defuddle": {"kinds": {"prose"}},
    "readability": {"kinds": {"prose"}},
    "markitdown": {"kinds": {"prose", "doc"}},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def detect_available() -> dict:
    """Return {extractor: how} for extractors runnable on this machine."""
    avail = {}
    if shutil.which("defuddle"):
        avail["defuddle"] = "defuddle (PATH)"
    if shutil.which("readable") or shutil.which("readability"):
        avail["readability"] = "readability (PATH)"
    if shutil.which("markitdown"):
        avail["markitdown"] = "markitdown (PATH)"
    elif shutil.which("uvx"):
        avail["markitdown"] = "markitdown (uvx, fetchable)"
    return avail


def choose(content_type: str, available: set) -> tuple[str | None, list, str]:
    """Return (chosen, skipped_missing, reason). chosen is None if nothing fits."""
    prefs = PREFERENCE.get(content_type)
    if prefs is None:
        raise ValueError(f"unknown content_type '{content_type}' (use prose|doc)")
    skipped = []
    for ex in prefs:
        if ex in available:
            reason = (f"{ex} selected"
                      + (f"; {', '.join(skipped)} not available" if skipped else ""))
            return ex, skipped, reason
        skipped.append(ex)
    return None, skipped, (f"no extractor for '{content_type}'; none of "
                           f"{prefs} available")


def emit(command, data, error, fmt) -> None:
    if fmt == "json":
        print(json.dumps({"ok": error is None, "command": command,
                          "data": data, "error": error}, indent=2))
    elif error:
        print(f"error: {error['message']}", file=sys.stderr)
    else:
        print(json.dumps(data, indent=2))


def _resolve_available(args) -> dict:
    """--have overrides detection; 'none' means simulate nothing installed."""
    if args.have is None:
        return detect_available()
    if args.have.strip().lower() in ("none", ""):
        return {}
    return {e.strip(): "(forced via --have)" for e in args.have.split(",") if e.strip()}


def cmd_plan(args) -> int:
    available = _resolve_available(args)
    try:
        chosen, skipped, reason = choose(args.content_type, set(available))
    except ValueError as e:
        emit("plan", None, {"message": str(e), "code": EXIT_USAGE}, args.format)
        return EXIT_USAGE
    if chosen is None:
        emit("plan", None,
             {"message": reason + ". Install one (e.g. `uvx 'markitdown[all]'` is the "
                         "easiest) or pass --content-type correctly.", "code": EXIT_NONE},
             args.format)
        return EXIT_NONE
    emit("plan", {"content_type": args.content_type, "available": sorted(available),
                  "chosen": chosen, "via": available[chosen],
                  "fell_back_from": skipped, "reason": reason}, None, args.format)
    return EXIT_OK


def _cmd_template(env_var: str, default: str, source: str) -> list:
    """Build an argv from an env-overridable template; {src} marks the source slot."""
    template = os.environ.get(env_var, default)
    parts = shlex.split(template)
    if any("{src}" in p for p in parts):
        return [p.replace("{src}", source) for p in parts]
    return parts + [source]


def _run_extractor(extractor: str, source: str) -> str:
    """Return extracted Markdown. Raises RuntimeError on failure.

    markitdown is verified on this machine. The defuddle/readability defaults are
    best-effort and UNVERIFIED here (neither tool was installed to test against) —
    override them with SNAPSHOT_DEFUDDLE_CMD / SNAPSHOT_READABILITY_CMD (use {src}
    for the source) to match your actual install, e.g.
      SNAPSHOT_DEFUDDLE_CMD="npx defuddle-cli {src} --md"
    """
    if extractor == "markitdown":
        cmd = (["markitdown", source] if shutil.which("markitdown")
               else ["uvx", "markitdown[all]", source])
    elif extractor == "defuddle":
        cmd = _cmd_template("SNAPSHOT_DEFUDDLE_CMD", "defuddle {src} --md", source)
    elif extractor == "readability":
        cmd = _cmd_template("SNAPSHOT_READABILITY_CMD", "readable {src}", source)
    else:
        raise RuntimeError(f"no runner for extractor '{extractor}'")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError(f"{cmd[0]} not found on PATH: {e}") from e
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {proc.stderr.strip()[:300]}")
    return proc.stdout


def cmd_run(args) -> int:
    available = _resolve_available(args)
    try:
        chosen, skipped, reason = choose(args.content_type, set(available))
    except ValueError as e:
        emit("run", None, {"message": str(e), "code": EXIT_USAGE}, args.format)
        return EXIT_USAGE
    if chosen is None:
        emit("run", None, {"message": reason, "code": EXIT_NONE}, args.format)
        return EXIT_NONE
    try:
        body = _run_extractor(chosen, args.source)
    except RuntimeError as e:
        emit("run", None, {"message": str(e), "code": EXIT_RUN}, args.format)
        return EXIT_RUN

    digest = hashlib.sha256(body.encode()).hexdigest()
    retrieved = args.retrieved_at or _now()
    front = (f"---\nsource_url: {args.source}\nretrieved_at: {retrieved}\n"
             f"extractor: {chosen}\ncontent_sha256: {digest}\n"
             + (f"pinned_version: \"{args.pinned_version}\"\n" if args.pinned_version else "")
             + "---\n\n")
    artifact = front + body
    out = Path(args.out) if args.out else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(artifact)
    emit("run", {"source": args.source, "extractor": chosen, "fell_back_from": skipped,
                 "content_sha256": digest, "bytes": len(artifact),
                 "out": str(out) if out else None, "retrieved_at": retrieved},
         None, args.format)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Resilient content snapshot extractor")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--have", help="override detected extractors (csv, or 'none'); for tests/CI")
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("plan", help="choose an extractor without fetching")
    pl.add_argument("--content-type", choices=["prose", "doc"], required=True)
    pl.set_defaults(func=cmd_plan)

    rn = sub.add_parser("run", help="extract a source and write a provenance-stamped artifact")
    rn.add_argument("source", help="URL or file path")
    rn.add_argument("--content-type", choices=["prose", "doc"], required=True)
    rn.add_argument("--out", help="artifact output path (.md)")
    rn.add_argument("--pinned-version", help="version to record for versioned sources")
    rn.add_argument("--retrieved-at", help="ISO timestamp to record (else now, UTC)")
    rn.set_defaults(func=cmd_run)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
