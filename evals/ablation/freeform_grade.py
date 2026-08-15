#!/usr/bin/env python3
"""Grade the free-form runs against Layer 2's SPECIFIED output.

The schema-forced matrix cannot test Layer 2, because Layer 2 is mostly a
specification for output shape and the schema overrides output shape. These runs
drop the schema, so what Layer 2 asks for either appears or it does not.

Layer 2 Step C and Step D specify, in the skill's own words:
  - the detected content type, stated at the top of the report
  - a scores table with FOUR dimensions, AI-Likeness always present
  - each score 1-10 with a one-line justification
  - a Flags section quoting the offending text with a suggested fix
  - a "Top 3 changes" list

Each is a string that is either in the output or is not. No judgement involved.
"""

import json
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).parent
RUNS = HERE / "runs-free"

CHECKS = {
    "states type": re.compile(r"detected as|content type|^\s*\*\*type", re.I | re.M),
    "AI-Likeness dim": re.compile(r"ai[- ]likeness", re.I),
    "scores /10": re.compile(r"\b(10|[1-9])\s*/\s*10\b"),
    "scores table": re.compile(r"^\s*\|.*\|", re.M),
    "top 3 changes": re.compile(r"top\s*3|top three", re.I),
    "flags section": re.compile(r"^#+.*\bflags?\b|^\*\*flags?\b", re.I | re.M),
}


def main() -> int:
    cases = sys.argv[1:] or ["1"]
    arms = sorted({p.stem.split("-")[1] for p in RUNS.glob("*-*-*.json")})
    width = max(len(k) for k in CHECKS)

    for case in cases:
        print(f"\nCASE {case} — free-form output, does Layer 2's deliverable appear?\n")
        print(f"  {'check':<{width}}  " + "  ".join(f"{a:>7}" for a in arms))
        print("  " + "-" * (width + 2 + 9 * len(arms)))
        texts = {}
        for arm in arms:
            texts[arm] = []
            for p in sorted(RUNS.glob(f"{case}-{arm}-*.json")):
                # A run still being written parses as nothing. Skip it rather than
                # crash the whole report -- graded mid-matrix this is normal.
                try:
                    env = json.loads(p.read_text())
                except json.JSONDecodeError:
                    print(f"  (skipping incomplete {p.name})")
                    continue
                if not env.get("is_error"):
                    texts[arm].append(env.get("result", "") or "")
        for name, rx in CHECKS.items():
            row = []
            for arm in arms:
                hits = sum(1 for t in texts[arm] if rx.search(t))
                row.append(f"{hits}/{len(texts[arm])}")
            print(f"  {name:<{width}}  " + "  ".join(f"{c:>7}" for c in row))
        print()
        for arm in arms:
            lens = [len(t.split()) for t in texts[arm]]
            if lens:
                print(f"  arm {arm}: {len(lens)} runs, mean {statistics.mean(lens):.0f} words")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
