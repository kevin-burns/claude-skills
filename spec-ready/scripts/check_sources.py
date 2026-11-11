#!/usr/bin/env python3
"""Check a PRD written by spec-ready: decisions cite the person's turns, figures have sources.

    check_sources.py PRD.md READINESS.json      exit 0 clean, 1 findings (printed one per line)

Rules:
- the header line `Readiness: verified|attested` matches readiness.json's mode;
- in the decision sections every non-empty line cites `[turn:<id>]`, and every cited id is a
  settled turn in readiness.json;
- `## Assumptions` lines start with `Assumption:` (a bullet marker before it is fine);
- outside Assumptions, a line containing a digit and no citation is an unsourced figure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DECISION_SECTIONS = {"problem", "who it is for", "goal", "non-goals", "anti-goal", "success check"}
CITATION = re.compile(r"\[turn:([^\]\s]+)\]")


def _sections(text: str) -> list[tuple[str, int, str]]:
    current, out = "", []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            current = line[3:].strip().lower()
        elif line.strip() and not line.startswith("#"):
            out.append((current, number, line.strip()))
    return out


def check_prd(text: str, readiness: dict) -> list[str]:
    findings = []
    header = re.search(r"^Readiness:\s*(\w+)\s*$", text, re.MULTILINE)
    if not header:
        findings.append("missing header line 'Readiness: verified|attested'")
    elif header.group(1) != readiness.get("mode"):
        findings.append(f"Readiness header says {header.group(1)} but readiness.json says {readiness.get('mode')}")
    settled = {r["turn"] for r in readiness.get("items", []) if r.get("status") == "settled" and r.get("turn")}
    for section, number, line in _sections(text):
        if line.startswith("Readiness:"):
            continue
        cited = CITATION.findall(line)
        for turn in cited:
            if turn not in settled:
                findings.append(f"line {number}: cites turn {turn}, which is not a settled turn")
        if section == "assumptions":
            if not re.sub(r"^[-*]\s*", "", line).startswith("Assumption:"):
                findings.append(f"line {number}: assumptions must start with 'Assumption:'")
            continue
        if section in DECISION_SECTIONS and not cited:
            findings.append(f"line {number}: decision line has no citation: {line[:80]}")
        elif not cited and re.search(r"\d", line):
            findings.append(f"line {number}: unsourced figure: {line[:80]}")
    return findings


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 1
    readiness = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    findings = check_prd(Path(args[0]).read_text(encoding="utf-8"), readiness)
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
