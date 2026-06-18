#!/usr/bin/env python3
"""Grade a coherence-checker run against eval.json.

Usage: uv run python grade.py <eval.json> <coherence.json>
Exit 0 if all assertions pass, 1 otherwise.

The agent is run out-of-band (it needs the fixture dir + SPEC.md + the round-trip test);
save its JSON return to <coherence.json>, then grade it here. Mirrors the code-reviewer eval.
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
    near = set(spec["planted"]["near_lines"])
    control = set(spec["control"]["lines"])
    verdict = (out.get("verdict") or "").lower()
    loop_back = (out.get("loop_back_target") or "").lower()

    # A catch is either an explicit inverse-pair finding or one located at the planted lines.
    catch = [f for f in findings
             if f.get("check") == "inverse-pair" or line_of(f.get("location")) in near]
    checks = {
        "catches-inverse-pair": bool(catch),
        "check-labelled-inverse-pair": any(f.get("check") == "inverse-pair" for f in catch),
        "verdict-fail": verdict == "fail",
        "loop-back-builder": loop_back == "code-builder",
        "no-false-flag-on-control": not any(line_of(f.get("location")) in control for f in findings),
    }

    all_pass = all(checks.values())
    for cid, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {cid}")
    print(f"\nfindings: {len(findings)} | inverse-pair catches: {len(catch)} | "
          f"verdict: {verdict or '(none)'} | loop_back: {loop_back or '(none)'}")
    print("ALL PASS" if all_pass else "FAILURES PRESENT")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(grade(sys.argv[1], sys.argv[2]))
