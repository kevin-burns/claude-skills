#!/usr/bin/env python3
"""Grade a code-reviewer run against eval.json.

Usage: uv run python grade.py <eval.json> <findings.json>
Exit 0 if all assertions pass, 1 otherwise.
"""
import json
import re
import sys


def line_of(location: str):
    m = re.search(r":(\d+)", location or "")
    return int(m.group(1)) if m else None


def grade(eval_path: str, out_path: str) -> int:
    spec = json.load(open(eval_path))
    out = json.load(open(out_path))
    findings = out.get("findings", [])
    near = set(spec["bug"]["near_lines"])
    control = set(spec["control"]["lines"])
    verdict = (out.get("verdict") or "").lower()

    bug_findings = [f for f in findings if (line_of(f.get("location")) in near)]
    checks = {
        "catches-bug": bool(bug_findings),
        "severity-adequate": any((f.get("severity") or "").lower() in ("major", "blocking")
                                 for f in bug_findings),
        "category-sane": any((f.get("category") or "").lower() in ("correctness", "edge-case")
                             for f in bug_findings),
        "verdict-not-ship": verdict != "ship",
        "no-false-blocking-on-control": not any(
            (f.get("severity") or "").lower() == "blocking" and line_of(f.get("location")) in control
            for f in findings),
    }

    all_pass = all(checks.values())
    for cid, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {cid}")
    print(f"\nfindings: {len(findings)} | bug-region findings: {len(bug_findings)} | verdict: {verdict or '(none)'}")
    print("ALL PASS" if all_pass else "FAILURES PRESENT")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(grade(sys.argv[1], sys.argv[2]))
