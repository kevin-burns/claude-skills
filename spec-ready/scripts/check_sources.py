#!/usr/bin/env python3
"""Check a PRD written by spec-ready: decisions cite the person's turns, figures have sources.

    check_sources.py PRD.md READINESS.json [--spec SPEC.md]
                                                exit 0 clean, 1 findings (printed one per line)

Rules:
- the header lines `Readiness: verified|attested` and
  `Verifier: independent|agent-relayed|self-assessed|none` match readiness.json;
- in the decision sections every non-empty line cites `[turn:<id>]`, and every cited id is a
  settled turn in readiness.json;
- `## Assumptions` lines start with `Assumption:` and `## Open questions` lines with
  `Open question:` (a bullet marker before either is fine);
- outside Assumptions, a line containing a digit and no citation is an unsourced figure;
- in spec.md, each user story and each out-of-scope line cites a settled turn or starts
  `Proposed:` (implementation decisions are the design, and need neither).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SPEC_SOURCED_SECTIONS = {"user stories", "out of scope"}
DECISION_SECTIONS = {"problem", "who it is for", "goal", "non-goals", "anti-goal", "success check", "risks"}
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
    verifier = re.search(r"^Verifier:\s*([\w-]+)\s*$", text, re.MULTILINE)
    if not verifier:
        findings.append("missing header line 'Verifier: independent|agent-relayed|self-assessed|none'")
    elif verifier.group(1) != readiness.get("verification"):
        findings.append(f"Verifier header says {verifier.group(1)} but readiness.json says "
                        f"{readiness.get('verification')}")
    settled = {r["turn"] for r in readiness.get("items", []) if r.get("status") == "settled" and r.get("turn")}
    person = set(readiness.get("person_turns", []))
    for section, number, line in _sections(text):
        if line.startswith(("Readiness:", "Verifier:")):
            continue
        cited = CITATION.findall(line)
        # Decision lines cite settled turns; anything else may cite any of the person's turns.
        allowed = settled if section in DECISION_SECTIONS else settled | person
        for turn in cited:
            if turn not in allowed:
                kind = "a settled turn" if section in DECISION_SECTIONS else "one of the person's turns"
                findings.append(f"line {number}: cites turn {turn}, which is not {kind}")
        if section == "assumptions":
            if not re.sub(r"^[-*]\s*", "", line).startswith("Assumption:"):
                findings.append(f"line {number}: assumptions must start with 'Assumption:'")
            continue
        if section == "open questions":
            if not re.sub(r"^[-*]\s*", "", line).startswith("Open question:"):
                findings.append(f"line {number}: open questions must start with 'Open question:'")
            continue
        if section in DECISION_SECTIONS and not cited:
            findings.append(f"line {number}: decision line has no citation: {line[:80]}")
        elif not cited and re.search(r"\d", line):
            findings.append(f"line {number}: unsourced figure: {line[:80]}")
    return findings


def check_spec(text: str, readiness: dict) -> list[str]:
    findings = []
    settled = {r["turn"] for r in readiness.get("items", []) if r.get("status") == "settled" and r.get("turn")}
    for section, number, line in _sections(text):
        if section not in SPEC_SOURCED_SECTIONS:
            continue
        body = re.sub(r"^([-*]|\d+\.)\s*", "", line)
        cited = CITATION.findall(line)
        for turn in cited:
            if turn not in settled:
                findings.append(f"spec.md line {number}: cites turn {turn}, which is not a settled turn")
        if not cited and not body.startswith("Proposed:"):
            what = "user story" if section == "user stories" else "out of scope line"
            findings.append(f"spec.md line {number}: {what} neither cites a turn nor starts 'Proposed:': {line[:70]}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a spec-ready PRD (and spec) for sources.")
    parser.add_argument("prd")
    parser.add_argument("readiness")
    parser.add_argument("--spec")
    args = parser.parse_args(argv)
    readiness = json.loads(Path(args.readiness).read_text(encoding="utf-8"))
    findings = check_prd(Path(args.prd).read_text(encoding="utf-8"), readiness)
    if args.spec:
        findings += check_spec(Path(args.spec).read_text(encoding="utf-8"), readiness)
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
