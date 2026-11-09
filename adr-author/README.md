# adr-author

An Agent Skill that writes and amends architecture decision records (ADRs): records a team wants to
read, and that name exactly what they decide, so a reviewer, a newcomer or a tool can tell later
whether the code still follows them.

## What it does

- Asks whether there is a decision at all, and whether it deserves a record (hard to reverse,
  surprising without context, a real trade-off).
- Interviews briefly, then follows the repository's existing ADR format, numbering and header style.
  Two mixed schemes are reported, not silently resolved.
- Proposes the code names each decision is about (modules, functions, paths, settings) and uses only
  the ones the author confirms.
- Shows the draft before writing, with status Proposed, and invents nothing.
- Self-checks the record with `scripts/check_record.py` (standard library only, no model, no network):
  hedged decisions, names missing from the code, status, numbering, one-sided supersede links,
  decision language outside the Decision section.
- Compares the final record with the approved draft and asks for a second approval of any change.
- Amends, supersedes or records an exception when the code turned out to be right.

It never commits; it suggests a commit message.

## What it does not do

It does not judge code against records, choose between options, or rewrite a whole ADR set. A
record it writes can also be enforced by a separate checker such as adrcheck, if a team wants that.

## Install

Nothing to install beyond the agent and git. The script needs Python 3.12 or later; `uv run` or
`python3` both work.

## Tests and evals

```bash
uv run --with pytest python -m pytest adr-author/tests -q
```

`evals/` holds the behaviour cases, the fixture builder and the cold-reader grader; see
`evals/README.md`.

## Credit

Ideas borrowed, with thanks (all MIT; no text copied):

- the three-part test for whether a decision deserves a record, and asking "record as-is?" for an
  unquestioned decision: Matt Pocock's ADR format (mattpocock/skills, domain-modeling), as packaged in
  pandoscope/skills `writing-adrs`;
- matching the existing convention and reporting a conflict rather than adding a second scheme, and
  keeping the details an edit must not lose: Addy Osmani's `documentation-and-adrs`
  (addyosmani/agent-skills);
- approval before writing, Proposed as the default status, and never inventing rationale:
  `adr-drafting` (giuseppe-trisciuoglio/developer-kit).
