#!/usr/bin/env python3
"""Build the three ablation arms for clear-and-human.

A = SKILL.md + all three references, inlined.
B = identical to A, minus references/ai-patterns.md and minus every pointer to it.
C = nothing (no skill).

The only difference between A and B is the pattern list and the sentences that
point at it. Every other byte is shared, so a difference in output is
attributable to the list rather than to anything else in the skill.
"""

import pathlib
import re
import sys

SKILL = pathlib.Path("/Users/kevinburns/Developer/claude-skills/clear-and-human")
OUT = pathlib.Path(__file__).parent / "arms"

# Each entry: (exact substring in SKILL.md, replacement for arm B).
# Every replacement removes the pointer while keeping the surrounding instruction
# intact, so arm B is still told to do the thing -- just without the curated list.
#
# The long lines below carry `noqa: E501` because they are exact-match needles against
# SKILL.md. Wrapping one would stop it matching, and main() exits non-zero if any needle
# is missing -- so a drift in SKILL.md fails loudly rather than silently building an arm
# that was never ablated.
B_EDITS = [
    (
        "Apply the universal pattern list in `references/ai-patterns.md` to all content, then the channel-specific markers from `references/channels.md`.",  # noqa: E501
        "Scan for AI-writing patterns across all content, then apply the channel-specific markers from `references/channels.md`.",  # noqa: E501
    ),
    (
        "1. Replace every flagged pattern with natural language (see `references/ai-patterns.md` for before/after).",
        "1. Replace every flagged pattern with natural language.",
    ),
    (
        ' (see `references/ai-patterns.md`, which records that the "loudest tell" claim had no source)',
        "",
    ),
    (
        "**Em-dashes and curly quotes are not on this list** — they are author-relative and model-specific, and `references/ai-patterns.md` holds the current rule with its evidence. Follow the reference, not a blanket cut. A graded eval caught this file and that one giving opposite instructions, and the reference was the better-reasoned of the two.",  # noqa: E501
        "**Em-dashes and curly quotes are not on this list** — they are author-relative and model-specific.",
    ),
    (
        ' — see the expanded-contractions entry in `references/ai-patterns.md`',
        "",
    ),
    (
        "If you noticed a recurring AI tell that isn't in `references/ai-patterns.md`, surface it to the user as a suggestion with a concrete example, and let them decide whether to add it.",  # noqa: E501
        "If you noticed a recurring AI tell worth recording, surface it to the user as a suggestion with a concrete example, and let them decide whether to add it.",  # noqa: E501
    ),
]

REFS = ["ai-patterns.md", "channels.md", "elements-of-style.md"]


def inline(skill_md: str, refs: list[str]) -> str:
    parts = [
        "You have the following skill available. Follow it.\n",
        "# SKILL: clear-and-human\n",
        skill_md,
    ]
    for name in refs:
        body = (SKILL / "references" / name).read_text()
        parts.append(f"\n\n---\n\n# FILE: references/{name}\n\n{body}")
    return "\n".join(parts)


def main() -> int:
    skill_md = (SKILL / "SKILL.md").read_text()

    arm_a = inline(skill_md, REFS)

    b_md = skill_md
    for needle, repl in B_EDITS:
        if needle not in b_md:
            print(f"FAIL: edit target not found: {needle[:70]!r}", file=sys.stderr)
            return 1
        b_md = b_md.replace(needle, repl)

    leftover = re.findall(r"ai-patterns\.md", b_md)
    if leftover:
        print(f"FAIL: {len(leftover)} ai-patterns.md pointer(s) survive in arm B", file=sys.stderr)
        return 1

    arm_b = inline(b_md, ["channels.md", "elements-of-style.md"])

    OUT.mkdir(exist_ok=True)
    (OUT / "A.md").write_text(arm_a)
    (OUT / "B.md").write_text(arm_b)
    (OUT / "C.md").write_text("")

    for name in ("A", "B", "C"):
        p = OUT / f"{name}.md"
        print(f"{name}: {len(p.read_text()):>6} chars  {p}")
    print(f"A - B = {len(arm_a) - len(arm_b)} chars removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
