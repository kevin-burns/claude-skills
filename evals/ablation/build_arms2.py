#!/usr/bin/env python3
"""Second ablation: isolate the no-invention rule inside SKILL.md.

Round one established that removing references/ai-patterns.md changed nothing
(arm B, 2/16 vs arm A 1/16) while removing the whole skill changed a great deal
(arm C, 11/16). So the guardrail is somewhere in SKILL.md, but round one never
said where. These two arms bracket it:

  D  necessity  -- the whole skill MINUS core rule 1 and every restatement of it.
                   If D behaves like C, rule 1 is the load-bearing sentence.
  E  sufficiency -- ONLY the core rules block, nothing else at all.
                   If E behaves like A, rule 1 is not just necessary but enough.

Core rule 1 names the exact failure mode round one measured: "An authorial
stance. 'I've watched this approach turn into growth that holds up' -- an
eyewitness claim, published under the user's name, invented to add warmth."
Arm C produced precisely that in 8 of 8 LinkedIn runs. This tests whether that
bullet is what stops it.
"""

import pathlib
import re
import sys

SKILL = pathlib.Path("/Users/kevinburns/Developer/claude-skills/clear-and-human")
OUT = pathlib.Path(__file__).parent / "arms"
REFS = ["ai-patterns.md", "channels.md", "elements-of-style.md"]

RULES_HEAD = "## Core rules (all modes, non-negotiable)"
RULE2_HEAD = "2. **Preserve meaning.**"
VOICE_HEAD = "## Voice calibration (optional but improves everything)"

# Restatements of the rule that live outside the rule itself. Removed for arm D
# so the ablation is of the INSTRUCTION, not merely of one paragraph.
#
# The first build of this arm missed the last three, because the leak check ran
# against SKILL.md before the references were inlined -- and two of them live in
# channels.md. An arm that still carries "no invented specifics" is not an
# ablation of the no-invention rule. The check now runs on the final assembled
# text, which is the only version the model ever sees.
D_DROP = [
    "The context file supplies the approved facts; it does **not** relax core rule 1. Anything not in the file or the draft is still off-limits to invent.",  # noqa: E501
    "8. Honor the no-invention rule: if texture requires a fact you don't have, leave a placeholder.",  # noqa: E501
    "Defaults to a neutral, factual voice and never invents specifics to add texture.",
    '- **Do not assert that nothing was invented.** Say what you checked and how. "No number in the rewrite is absent from the original — fidelity_check reports 0 appeared" is a claim you can stand behind. "Nothing was invented" is not, and one output made exactly that claim in the same breath as inventing a metric about the user\'s CI pipeline.',  # noqa: E501
    " No invented version numbers, flags, or outputs.",
    " so no invented specifics, and",
]

LEAK = re.compile(r"core rule 1|no-invention|invented specifics|never invents? specifics|nothing was invented", re.I)


def inline(skill_md: str, refs: list[str]) -> str:
    parts = [
        "You have the following skill available. Follow it.\n",
        "# SKILL: clear-and-human\n",
        skill_md,
    ]
    for name in refs:
        parts.append(f"\n\n---\n\n# FILE: references/{name}\n\n{(SKILL / 'references' / name).read_text()}")
    return "\n".join(parts)


def span(text: str, start_marker: str, end_marker: str) -> tuple[int, int]:
    i = text.index(start_marker)
    j = text.index(end_marker, i)
    return i, j


def main() -> int:
    md = (SKILL / "SKILL.md").read_text()

    # --- arm D: strip core rule 1, keep rules 2-4, renumber to 1-3 -----------
    r1_start, r1_end = span(md, "1. **Never invent specifics to add texture.**", RULE2_HEAD)
    d = md[:r1_start] + md[r1_end:]
    for old, new in (("2. **Preserve meaning.**", "1. **Preserve meaning.**"),
                     ("3. **Match the intended voice**", "2. **Match the intended voice**"),
                     ("4. **Clean is not enough.**", "3. **Clean is not enough.**")):
        if old not in d:
            print(f"FAIL: renumber target missing: {old!r}", file=sys.stderr)
            return 1
        d = d.replace(old, new, 1)
    # Layer 3's list ran 1-8; item 8 is gone, so the list simply ends at 7.
    d_refs = {}
    for name in REFS:
        d_refs[name] = (SKILL / "references" / name).read_text()
    for phrase in D_DROP:
        if phrase in d:
            d = d.replace(phrase, "")
            continue
        hit = next((n for n, body in d_refs.items() if phrase in body), None)
        if hit is None:
            print(f"FAIL: drop target missing: {phrase[:60]!r}", file=sys.stderr)
            return 1
        d_refs[hit] = d_refs[hit].replace(phrase, "")

    assembled = d + "".join(d_refs.values())
    leaks = LEAK.findall(assembled)
    if leaks:
        print(f"FAIL: {len(leaks)} restatement(s) survive in arm D: {leaks}", file=sys.stderr)
        return 1

    # --- arm E: the core rules block alone -----------------------------------
    e_start, e_end = span(md, RULES_HEAD, VOICE_HEAD)
    e = md[e_start:e_end].rstrip() + "\n"

    OUT.mkdir(exist_ok=True)
    d_full = "\n".join(
        ["You have the following skill available. Follow it.\n", "# SKILL: clear-and-human\n", d]
        + [f"\n\n---\n\n# FILE: references/{n}\n\n{d_refs[n]}" for n in REFS]
    )
    (OUT / "D.md").write_text(d_full)
    (OUT / "E.md").write_text(
        "You have the following skill available. Follow it.\n\n# SKILL: clear-and-human\n\n" + e
    )

    a = OUT / "A.md"
    if a.exists():
        print(f"A (round one): {len(a.read_text()):>6} chars")
    for name in ("D", "E"):
        print(f"{name}: {len((OUT / f'{name}.md').read_text()):>6} chars")
    print(f"\nD removed {len(md) - len(d)} chars of SKILL.md ({(len(md) - len(d)) / len(md):.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
