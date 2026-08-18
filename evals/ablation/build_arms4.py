#!/usr/bin/env python3
"""Fourth ablation: arm G strips the Provenance block, keeping the exclusions.

This arm inverts the harness's usual question, and that has to be said first.
Arms A-F asked "is this material dead weight?", where a null is a limitation.
Arm G asks "is it SAFE TO CUT?", where a null is the RESULT. An underpowered
null here does not mean equivalent, it means we could not tell -- and read as
the former it licenses cutting load-bearing material. Hence more replicates
than the three used before, and hence reading the gap against the within-arm
floor rather than reading the p-value alone.

  G  the whole skill MINUS "## Provenance" through the citation list, KEEPING
     the "Deliberately excluded" paragraph under a renamed heading.

WHY THE EXCLUSIONS PARAGRAPH STAYS. It is not provenance. It is a live guardrail
-- the thing that stops a future agent reaching for an AI-detector score or
burstiness, both of which have measured reasons to be refused. Independent
evidence it is the right call: Matt Pocock's codebase-design carries a
structurally identical "Rejected framings" section for exactly the same purpose
(github.com/mattpocock/skills, MIT, commit 9c9f36c).

WHY THIS MODELS A RELOCATION AS A REMOVAL. In the repo the action is to move
these ~450 words to references/. The harness inlines every reference into the
payload, so a literal relocation would be a no-op -- same words, new position,
testing ORDER rather than PRESENCE. But a reference file nothing points at is
never loaded in real use, so absence from the payload IS the real-world effect.
If a pointer to it is ever added, that is a different arm and needs its own run.

THE ONE CONFOUND, stated rather than discovered. The "## Provenance" heading is
renamed to "## Deliberately excluded" so the surviving paragraph keeps a home
and the heading COUNT is unchanged. That is one word of new text. Everything
else is pure deletion.
"""

import pathlib
import sys

SKILL = pathlib.Path("/Users/kevinburns/Developer/claude-skills/clear-and-human")
OUT = pathlib.Path(__file__).parent / "arms"
REFS = ["ai-patterns.md", "channels.md", "elements-of-style.md"]

PROV_HEAD = "## Provenance"
EXCL_START = "Deliberately excluded, and it matters that they are:"
TAIL_BULLET = "- `ognjengt/founder-skills` (MIT)"

# Must be gone from arm G. Only citations that live NOWHERE ELSE in the payload.
# "founder-skills" alone is too loose a probe: Voice calibration names the
# FOUNDER_CONTEXT.md convention in the BODY (line 38), which must survive. Match
# the provenance bullet's own form instead.
GONE = ["Herbold", "Milička", "Dawkins", "Reinhart", "Bradner", "`ognjengt/founder-skills`"]

# Cited in SKILL.md AND in a reference, so cutting the block does not remove them
# from the payload. Measured 2026-08-18: Biber appears in SKILL.md, ai-patterns.md
# AND channels.md; Pavlick and the-humanizer in SKILL.md and ai-patterns.md.
#
# This is a real duplication finding in its own right -- one meaning in three
# places is the single-source-of-truth failure -- but for THIS arm it is a
# constraint: arm G cannot isolate them, and saying so is the difference between
# a bounded result and an overclaim. Asserted rather than ignored, so that a
# future edit to the references cannot silently change what this arm measures.
DUPLICATED = ["Biber", "Pavlick", "the-humanizer"]

# Must survive in arm G -- the guardrail and its evidence.
KEPT = ["Deliberately excluded", "61.22%", "burstiness", "not a detector and not a grammar checker",
        "the convention used by founder-skills"]  # body, not provenance -- must survive


def main() -> int:
    md = (SKILL / "SKILL.md").read_text()
    for marker in (PROV_HEAD, EXCL_START, TAIL_BULLET):
        if marker not in md:
            print(f"FAIL: marker missing: {marker!r}", file=sys.stderr)
            return 1

    i = md.index(PROV_HEAD)
    excl = md[md.index(EXCL_START):md.index(TAIL_BULLET)].rstrip()
    g = md[:i] + "## Deliberately excluded\n\n" + excl + "\n"

    parts = [
        "You have the following skill available. Follow it.\n",
        "# SKILL: clear-and-human\n",
        g,
    ]
    for name in REFS:
        parts.append(f"\n\n---\n\n# FILE: references/{name}\n\n{(SKILL / 'references' / name).read_text()}")

    OUT.mkdir(exist_ok=True)
    text = "\n".join(parts)
    (OUT / "G.md").write_text(text)

    # An arm whose build silently no-ops produces a confident null, and a
    # confident null is exactly the failure mode this arm is most exposed to.
    for probe in GONE:
        assert probe not in text, f"arm G still carries {probe!r} -- the cut did not happen"
    for probe in KEPT:
        assert probe in text, f"arm G lost the guardrail: {probe!r}"
    for probe in DUPLICATED:
        assert probe in text, (
            f"{probe!r} vanished from the payload -- it was reachable via a reference "
            "when this arm was designed. The duplication changed; re-scope the arm."
        )

    a = OUT / "A.md"
    print(f"G: {len(text):>6} chars")
    if a.exists():
        base = len(a.read_text())
        cut = base - len(text)
        print(f"A: {base:>6} chars   G removes {cut} ({cut / base:.1%} of the payload)")
        if cut < 2000:
            print(f"WARNING: expected ~2.5k chars removed, got {cut}", file=sys.stderr)
            return 1
    print(f"checked: {len(GONE)} SKILL.md-only citations gone, {len(KEPT)} guardrail markers kept, "
          f"{len(DUPLICATED)} still reachable via references (arm cannot isolate these)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
