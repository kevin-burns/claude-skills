#!/usr/bin/env python3
"""Fail the build on any bandit finding that is not in the baseline.

WHY THIS IS NOT `test -s` ON THE EXIT CODE. bandit exits 0 when it cannot read
the files it was handed. Measured 2026-09-06: a mis-quoted file list arrived as
one enormous argument, bandit recorded {"reason": "File name too long"}, scanned
zero lines, wrote an empty report and exited 0. A gate built on that exit code
would have passed forever while checking nothing. So the report is read back and
asserted on -- a scan that found nothing and a scan that ran nothing must not
look the same.

Stdlib only, like check_conventions.py: a stray third-party import fails here
rather than passing on a pre-populated runner.
"""
from __future__ import annotations

import json
import sys


def main(argv: list[str]) -> int:
    # The report path is required rather than defaulted. A default of
    # "/tmp/bandit.json" is both a bandit B108 and a way for this checker to
    # silently grade a STALE report from an earlier run if the caller forgets
    # the argument -- which is the same class of quiet pass it exists to stop.
    if len(argv) != 2:
        print("usage: check_bandit.py <bandit-json-report>")
        return 2
    path = argv[1]
    try:
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"::error::bandit report at {path} is unreadable: {exc}")
        return 1

    errors = report.get("errors") or []
    loc = report.get("metrics", {}).get("_totals", {}).get("loc", 0)
    if errors or not loc:
        print(f"::error::bandit scanned nothing usable (loc={loc}, errors={len(errors)})")
        for entry in errors:
            print(f"  {entry.get('reason')}: {str(entry.get('filename', ''))[:120]}")
        return 1

    new = report.get("results") or []
    print(f"bandit: scanned {loc} loc, {len(new)} finding(s) outside the baseline")
    for item in new:
        print(f"::error file={item['filename']},line={item['line_number']}::"
              f"{item['test_id']} ({item['issue_severity']}) {item['issue_text']}")
    if new:
        print("::error::a new medium-or-higher finding is not baselined. Fix it, or "
              "-- if it is genuinely safe -- regenerate .bandit-baseline.json and say "
              "why in the commit message. Do not add '# nosec'.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
