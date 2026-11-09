---
name: adr-author
description: >-
  Write or amend an architecture decision record (ADR) that a team will want to read and that names exactly what it decides: the modules, functions, paths or settings, and what must or must never happen. Asks whether the decision deserves a record, interviews briefly, follows the repo's existing ADR format and numbering, shows the draft before writing, and self-checks it (hedged decisions, names missing from the code, status and supersede links). Also amends or supersedes a record when the code turned out to be right. Use for "write an ADR", "record this decision", "supersede ADR 4", "our ADR no longer matches the code". Does not judge code against records, and does not make the decision. General prose and docs are clear-and-human.
---

# adr-author

Writes the record of a decision a team has already made, precisely enough that a reviewer, a
newcomer or a tool can tell later whether the code still follows it. Amends the record when the
code turns out to be right.

**The rule above all others: a record is for people first.** Precision here is a discipline, not a
format. Make a sentence more precise only by naming what it already meant. Never rephrase it into
a different shape, never drop a qualifier, condition or trade-off, and keep the reasons in Context
where a person reads them.

## Before writing anything

1. **Is there a decision?** If the user is still choosing ("Kafka or SQS?"), say there is nothing to
   record yet and stop. Offer frontier-rounds or design-council to make the decision.
2. **Does it deserve a record?** All three must hold (Matt Pocock's ADR criteria):
   - hard to reverse: changing your mind later costs something real;
   - surprising without context: a future reader would ask "why on earth did they do this?";
   - a real trade-off: there were genuine alternatives.
   If one fails, say which and stop, unless the author still wants it written.
3. **Was it questioned?** If the decision was made in this conversation and nobody pushed on it, ask
   "record as-is?" first. Skip this when the author states a decision they had already made.
4. **Short interview.** Ask only for what is missing: the context and forces, the decision, what it
   rules out, the consequences, the alternatives worth remembering. One batch of questions at a
   time; never re-ask what the author already said.

## Follow the repo's convention

Read the ADR directory (look for `docs/adr`, `docs/decisions`, `doc/adr`, `adr`, `architecture/adr`,
or an existing `.adr-dir` file). Match what is there: location, file extension, numbering and
filename pattern, heading set, template family (Nygard, MADR, Y-statement), and how the status,
date and supersede lines are written (plain line, bold label, table row, front matter or a Status
heading). If two schemes are mixed, **report the conflict and ask which to follow**; do not pick one
silently (Addy Osmani's documentation-and-adrs). Only with no existing records, use the default in
`references/writing-guide.md`.

## Name what the decision is about

For each decision sentence, search the repository for the names it means: a module, a function or
class, a path, a configuration key. **Propose them and let the author confirm.** Use only confirmed
names. A sentence with no confirmed name stays as the author wrote it and goes in the report. A
decision about code that does not exist yet keeps its intended names and says they are planned.

The decision goes in Decision and Consequences; the reasons go in Context; rejected alternatives go
in Considered Options and never bind. `references/writing-guide.md` has the full guidance and a
worked example.

## Draft, show, then write

- Status is **Proposed** unless the author says the team has accepted it.
- Never invent rationale, constraints, consequences or alternatives. A gap becomes a question, or a
  visible placeholder such as `[CONSEQUENCE NEEDED]` (developer-kit adr-drafting).
- Show the path, title, status and full draft. Write the file only after the author approves.

## Self-check, then a second look

Run the self-check on the written file. It uses no model and no network.

```bash
UV="$(command -v uv || ls "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)"
check_record() { "$UV" run "$HOME/.claude/skills/adr-author/scripts/check_record.py" "$@"; }

check_record docs/adr/0007-billing-reads-ledger-through-api.md --repo .
check_record docs/adr/0007-billing-reads-ledger-through-api.md --repo . --intended PlannedName
```

Without `uv`, run the same file with `python3` (3.12 or later). If the skill is installed somewhere
else, use that directory's `scripts/check_record.py`.

It reports, in plain words: decision sentences that hedge ("should", "prefer") and so decide
nothing yet; names that appear nowhere in the repository; a missing status; a number already taken
or out of sequence; supersede links that are one-sided; decision language sitting in Context or the
options; mixed filename styles. **Each finding is a question for the author, never an automatic
fix.** A hedge may be a deliberate preference; a missing name may be planned code.

Make at most one revision round from the answers. Then compare the final file with the approved
draft and show the author the diff for a **second approval**; the first approval never covers
revisions:

```bash
check_record docs/adr/0007-billing-reads-ledger-through-api.md --repo . --against /tmp/approved-draft.md --confirmed ledger/api.py Ledger
```

It reports anything that vanished, any change to a word that sets the decision's strength (must,
never, only, all...), and any name added without confirmation.

## Amend mode: when the code turned out to be right

The input is a description of the mismatch from anyone: the author, a reviewer, a pull request
comment, or a checking tool's report pasted as text. No particular format is needed.

Ask the one question that decides the shape: **is the old decision wrong now, narrower than
written, or right with a one-off exception?** Then follow `references/amend.md`:

- wrong now: a superseding record, and the old record's status changed to say which record
  replaced it, both in the same change;
- narrower: amend Decision or Consequences and keep the history in the repo's style;
- one-off: record the exception the way the team already does; if it has no way, propose a short
  note in the record and ask.

The same self-check, comparison and two approvals apply.

## Finish

Report: the file path; what the record now commits the team to, in plain words; names not yet in
the code; open questions. Never run `git add`, `git commit` or `git push`. List the changed files
and suggest a commit message with no AI attribution.

A record written this way can also be enforced by a checking tool such as adrcheck, if the team wants that.

## What this skill does not do

- It does not judge whether code follows a record.
- It does not choose between options; it records a choice already made.
- It does not convert or rewrite a whole ADR set.
- It does not polish general prose (clear-and-human) or check readability (readability).
