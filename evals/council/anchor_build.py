#!/usr/bin/env python3
"""Build the FIRST and LAST prompts for the anchoring test.

The two conditions model the Director's context at two positions in the same council:

  FIRST  the target member is the first proposer -- nothing precedes it
  LAST   five other members' contributions precede it, byte-identical across replicates

Everything else is held constant: same brief, same target role file, same instruction.
The only variable is what is already in the context when the member writes.

Run with no argument to emit the prefix-member prompts, then again after those runs land
to assemble prompts/last.md.
"""
import pathlib
import sys

COUNCIL = pathlib.Path.home() / ".claude/skills/design-council/members"
HERE = pathlib.Path(__file__).parent
PROMPTS = HERE / "prompts"
RUNS = HERE / "runs"

TARGET = "pragmatist"
PREFIX = ["software-architect", "data-engineer", "devops-sre", "product-manager", "customer-voice"]

FRAME = """You are a member of a Design Council deliberating on the brief below. Produce
ONLY your own contribution, in the format your role defines. Do not synthesise, do not
speak for other members, and do not propose a final recommendation for the council.

## The brief

{brief}
"""

ROLE = """
## Your role

{role}

---

Write your contribution now.
"""


def main() -> int:
    PROMPTS.mkdir(exist_ok=True)
    brief = (HERE / "brief.md").read_text().strip()

    for m in PREFIX:
        role = (COUNCIL / m / "SKILL.md").read_text()
        (PROMPTS / f"prefix-{m}.md").write_text(FRAME.format(brief=brief) + ROLE.format(role=role))
    print(f"wrote {len(PREFIX)} prefix prompts")

    target_role = (COUNCIL / TARGET / "SKILL.md").read_text()
    (PROMPTS / "first.md").write_text(FRAME.format(brief=brief) + ROLE.format(role=target_role))
    print("wrote prompts/first.md")

    # LAST needs the prefix contributions to exist.
    import json
    parts, missing = [], []
    for m in PREFIX:
        p = RUNS / f"prefix-{m}-1.json"
        if not p.exists():
            missing.append(m)
            continue
        d = json.loads(p.read_text())
        if d.get("is_error"):
            missing.append(m)
            continue
        parts.append(f"### Contribution from {m}\n\n{d['result'].strip()}")
    if missing:
        print(f"prefix runs missing/errored for {missing} -- run them, then re-run this", file=sys.stderr)
        return 0
    prefix_block = "\n\n## Contributions already made in this council\n\n" + "\n\n".join(parts) + "\n"
    (PROMPTS / "last.md").write_text(
        FRAME.format(brief=brief) + prefix_block + ROLE.format(role=target_role)
    )
    chars = len(prefix_block)
    print(f"wrote prompts/last.md  (prefix is {chars} chars from {len(parts)} members)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
