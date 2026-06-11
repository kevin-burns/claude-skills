#!/usr/bin/env python3
"""Grade a fact-verifier run against eval.json.

Usage: uv run python grade.py <eval.json> <verdicts.json>
Exit 0 if all claims pass, 1 otherwise.
"""
import json
import sys


def grade(eval_path: str, verdicts_path: str) -> int:
    spec = json.load(open(eval_path))
    out = json.load(open(verdicts_path))
    by_claim = {v["claim"]: v for v in out.get("verdicts", [])}

    all_pass = True
    for c in spec["claims"]:
        v = by_claim.get(c["claim"])
        checks: list[tuple[str, bool]] = []
        if v is None:
            checks.append(("verdict present", False))
        else:
            checks.append((f"verdict == {c['expected_verdict']}",
                           v.get("verdict") == c["expected_verdict"]))
            if "expected_citation_contains" in c:
                checks.append((f"citation contains '{c['expected_citation_contains']}'",
                               c["expected_citation_contains"] in (v.get("citation") or "")))
            if "expected_correct_value" in c:
                checks.append((f"correct_value == {c['expected_correct_value']}",
                               str(v.get("correct_value", "")).strip() == c["expected_correct_value"]))
            if "expected_lookup_contains" in c:
                checks.append((f"lookup_command contains '{c['expected_lookup_contains']}'",
                               c["expected_lookup_contains"] in (v.get("lookup_command") or "")))
        passed = all(ok for _, ok in checks)
        all_pass &= passed
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {c['id']}")
        for label, ok in checks:
            print(f"        {'ok' if ok else 'XX'}  {label}")

    print(f"\n{'ALL PASS' if all_pass else 'FAILURES PRESENT'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(grade(sys.argv[1], sys.argv[2]))
