---
name: adr-author
license: MIT
description: >-
  Write or amend an architecture decision record (ADR) that a team will want to read and that names exactly what it decides: the modules, functions, paths or settings, and what must or must never happen. Asks whether the decision deserves a record, interviews briefly, follows the repo's existing ADR format and numbering, shows the draft before writing, and self-checks it (hedged decisions, names missing from the code, status and supersede links). Also amends or supersedes a record when the code turned out to be right. Use for "write an ADR", "record this decision", "document the architecture decision we made", "turn this into a decision record", "supersede ADR 4", "our ADR no longer matches the code", or a one-off exception to an existing ADR. Does not judge code against records, and does not make the decision. General prose and docs are clear-and-human.
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
   If one fails, say which and stop: write no draft, unless the author still wants it written.
3. **Was it questioned?** If the decision was made in this conversation and nobody pushed on it, ask
   "record as-is?" first. Skip this when the author states a decision they had already made.
4. **Short interview.** Ask only for what is missing: the context and forces, the decision, what it
   rules out, the consequences, the alternatives worth remembering. One batch of questions at a
   time; never re-ask what the author already said.
5. **Keep the author's words.** Make one scratch directory for this record, outside the
   repository, and print its path:
   `D="$(mktemp -d "${TMPDIR:-/tmp}/adr-author.XXXXXX")"; echo "$D"`. Shell state does not survive
   between commands, so reuse the printed path, never a fixed name another record may have used.
   Save what the author said about the decision, verbatim, to `$D/notes.md`. The self-check uses it
   to prove every figure in the record came from the author.

## Every fact needs a source

Context must say what goes wrong without the decision: the harm it prevents. "Newcomers keep
writing to the table directly" says what happens, not what it breaks; ask the author what it
breaks before writing, and never supply a harm yourself.

A record is evidence for the people who read it later. Every factual claim in it must come from
the author's words or from the repository: an incident, a number, a date, a duration, a cost, a
count, "we tried X", "this caused Y". Show a short source list with the draft, one line per claim:
the claim, then "author" or a file and line in the repository. A claim with no source is asked
about, or becomes a visible gap. It is never written in, however plausible it sounds, and never
inferred from the code ("the services were coupled" is a claim; the author has to say it).

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
names (pass only those to `--confirmed`; the script checks them against your notes of the
author's words), and put each one where the rule is, in Decision or Consequences; a name that appears only in
Context is not part of the decision. A sentence with no confirmed name stays as the author wrote it and goes in the report. A
decision about code that does not exist yet keeps its intended names and says they are planned.

The decision goes in Decision and Consequences; the reasons go in Context; rejected alternatives go
in Considered Options and never bind. `references/writing-guide.md` has the full guidance, and
`references/example-adr.md` is one complete record to imitate, with a best-practice checklist.

## Draft, show, then write

- Status is **Proposed** unless the author says the team has accepted it.
- Never invent rationale, constraints, consequences or alternatives. A gap becomes a question, or a
  visible placeholder such as `[CONSEQUENCE NEEDED]` in the draft (developer-kit adr-drafting).
- Show the path, title, status, full draft and source list. **Show the full draft as text in your
  reply, before the command that writes the record**, not only inside that command: the author
  approves what they can read. Never say a draft was shown when it was not.
  Write the file only after the author approves. **If the request already approves** the draft ("approve it as you show it"), that counts
  as approval: show the draft and write it in the same turn. Treat that wording the same way every
  time.
- **Never write a record that still has a placeholder** unless the author says to. Ask the open
  questions first; if the author says "leave it", drop the sentence rather than ship the gap.
- **Save the approved draft** to `$D/approved-draft.md` before you write the record. The
  comparison below is only worth anything if the draft was saved first; the script refuses a draft
  file that is newer than the record. Never sleep, touch or copy files to get past a check; a check
  you had to trick has told you something, so report it instead.

## Self-check, then a second look

Run the self-check on the written file. It uses no model and no network.

```bash
CHECK="$( { for f in "$PWD/.claude/skills/adr-author/scripts/check_record.py" "$HOME/.claude/skills/adr-author/scripts/check_record.py" "$HOME/.agents/skills/adr-author/scripts/check_record.py"; do [ -f "$f" ] && echo "$f"; done; find -L "$HOME/.claude" "$HOME/.agents" "$HOME/.codex" -path '*adr-author/scripts/check_record.py' 2>/dev/null; } | head -1)"
echo "$CHECK"
python3 "$CHECK" docs/adr/0007-billing-reads-ledger-through-api.md --repo . --sources "$D/notes.md"
python3 "$CHECK" docs/adr/0007-billing-reads-ledger-through-api.md --repo . --sources "$D/notes.md" --intended PlannedName
```

It needs Python 3.12 or later and nothing else; `uv run` works too. If `find` prints nothing, the
skill is installed somewhere else: use that directory's `scripts/check_record.py`.

It reports, in plain words: figures (numbers, dates, percentages, durations, counts, amounts) that
are not in the author's notes; decision sentences that hedge ("should", "prefer") and so decide
nothing yet; names that appear nowhere in the repository; a missing status; a number already taken
or out of sequence; supersede links that are one-sided; decision language sitting in Context or the
options; mixed filename styles. **Each finding is a question for the author, never an automatic
fix.** A hedge may be a deliberate preference; a missing name may be planned code.

Make at most one revision round from the answers. Then compare the final file with the approved
draft and show the author the diff for a **second approval**; the first approval never covers
revisions:

```bash
python3 "$CHECK" docs/adr/0007-billing-reads-ledger-through-api.md --repo . --against "$D/approved-draft.md" --confirmed ledger/api.py Ledger
```

It reports anything that vanished, any figure that appeared, any change to a word that sets the
decision's strength (must, never, only, all...), and any name added without confirmation. Never
create the "approved draft" file from the record you just wrote; that compares the record with
itself. When editing a record that is already committed, use `--baseline` instead (see amend mode).

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
