#!/usr/bin/env python3
"""Third ablation: arm F strips Layer 2 -- detect, score, report.

Layer 2 is the largest block in SKILL.md with no evidence either way. Rounds one
and two showed the core rules carry the fabrication guardrail and the pattern
list carries vocabulary; nothing has ever tested the review machinery.

  F  the whole skill MINUS "## Layer 2 -- Detect, score, report (review mode)"
     through to "## Layer 3". Core rules, voice calibration, Layer 1, Layer 3
     and all three references stay.

WHAT THIS ARM CANNOT MEASURE, stated up front rather than discovered afterwards:
the harness forces output through a JSON schema (content_type, tells, rewrite),
so Step D's report template and Step C's 1-10 scores have nowhere to land. This
arm bounds Layer 2's effect on CLASSIFICATION, on WHAT GETS FLAGGED, and on
FABRICATION. It says nothing about whether the report reads well, because no arm
in this harness produces a report at all.

What it can still see is real: Step A's classification lands in content_type, and
Step B's scan instruction lands in tells.
"""

import pathlib
import sys

SKILL = pathlib.Path("/Users/kevinburns/Developer/claude-skills/clear-and-human")
OUT = pathlib.Path(__file__).parent / "arms"
REFS = ["ai-patterns.md", "channels.md", "elements-of-style.md"]

L2_START = "## Layer 2 — Detect, score, report (review mode)"
L2_END = "## Layer 3 — Rewrite and restore (rewrite mode)"


def main() -> int:
    md = (SKILL / "SKILL.md").read_text()
    for marker in (L2_START, L2_END):
        if marker not in md:
            print(f"FAIL: marker missing: {marker!r}", file=sys.stderr)
            return 1

    i, j = md.index(L2_START), md.index(L2_END)
    f = md[:i] + md[j:]

    # The horizontal rule that used to separate Layer 2 from Layer 3 is now a
    # stray double rule. Left alone it is cosmetic, but a doubled "---" in the
    # middle of a prompt is exactly the kind of artefact that makes an arm
    # differ from its control for a reason that has nothing to do with the
    # ablation, so it goes.
    f = f.replace("---\n\n---\n", "---\n")

    parts = [
        "You have the following skill available. Follow it.\n",
        "# SKILL: clear-and-human\n",
        f,
    ]
    for name in REFS:
        parts.append(f"\n\n---\n\n# FILE: references/{name}\n\n{(SKILL / 'references' / name).read_text()}")

    OUT.mkdir(exist_ok=True)
    (OUT / "F.md").write_text("\n".join(parts))

    a = OUT / "A.md"
    print(f"F: {len((OUT / 'F.md').read_text()):>6} chars")
    if a.exists():
        base = len(a.read_text())
        cut = base - len((OUT / "F.md").read_text())
        print(f"A: {base:>6} chars   F removes {cut} ({cut / base:.1%} of the payload)")
    for probe in ("AI-Likeness", "Detected as:", "Score (1–10"):
        assert probe not in (OUT / "F.md").read_text(), f"Layer 2 remnant survives: {probe}"
    print("checked: no AI-Likeness, no report template, no scoring table in arm F")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
