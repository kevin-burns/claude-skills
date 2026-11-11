#!/usr/bin/env python3
"""Opt-in PreToolUse hook for spec-ready: refuse to write prd.md or spec.md before the gate passes.

Not installed by the skill. To use it, add a PreToolUse hook for Write|Edit|MultiEdit that runs
this file (see the skill's README). Exit 2 blocks the tool call and shows the message to the
agent; exit 0 allows it. Malformed input is allowed: a guard must not break unrelated work.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GUARDED_TOOLS = {"Write", "Edit", "MultiEdit"}
GUARDED_NAMES = {"prd.md", "spec.md"}
MESSAGE = ("spec-ready: the readiness gate has not passed for this directory (or, without a transcript, "
           "the person has not agreed to continue unverified); run gate.py check")


def decide(event: dict) -> tuple[int, str]:
    if event.get("tool_name") not in GUARDED_TOOLS:
        return 0, ""
    file_path = (event.get("tool_input") or {}).get("file_path")
    if not isinstance(file_path, str) or Path(file_path).name not in GUARDED_NAMES:
        return 0, ""
    readiness = Path(file_path).parent / "readiness.json"
    try:
        doc = json.loads(readiness.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 2, MESSAGE
    if not isinstance(doc, dict):
        return 2, MESSAGE
    verified = doc.get("mode") == "verified" and doc.get("pass") is True
    accepted = doc.get("mode") == "attested" and bool(doc.get("attested_ack"))
    return (0, "") if verified or accepted else (2, MESSAGE)


def main() -> int:
    try:
        event = json.loads(sys.stdin.read())
        if not isinstance(event, dict):
            raise ValueError("event is not an object")
    except ValueError as error:
        print(f"spec-ready guard: ignoring unreadable hook input ({error})", file=sys.stderr)
        return 0
    code, message = decide(event)
    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
