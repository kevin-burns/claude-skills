# Writing a record people want to read

## The sentence test

For every sentence in Decision and Consequences ask: if a reviewer quoted this back to a developer,
would it settle the argument? "Services should prefer asynchronous communication where practical"
settles nothing. "Orders publishes its events through `Outbox` in `events/outbox.py` and never calls
the billing service's HTTP API from a request handler" settles it, and still reads as English.

## Precision by naming

Precision comes from names the code already uses, not from a special style.

- Name the thing: a module, a class or function, a path, a configuration key, a queue or table.
- Say what must happen, or what must never happen. "Must" and "never" are ordinary words; use them
  when the team means them.
- One decision per sentence. A sentence that lists several named things is fine; each is checked on
  its own.
- If the team genuinely means a preference, write it as one and expect it to be read that way.
- If a path would make the sentence hard to read, keep the sentence plain and add a short "Where
  this applies" line after it. Do not twist the sentence around the path.

## What goes where

| Section | Job | Binds? |
|---|---|---|
| Title | the decision in a few words, as a statement | no |
| Status, Date | Proposed, Accepted, Deprecated, Superseded (by which record), Rejected | no |
| Context | why the decision was needed: the forces, the incident, the constraint | no |
| Decision | what was decided, with names | yes |
| Consequences | what becomes easier, harder or forbidden as a result | yes |
| Considered Options | alternatives worth remembering and why they lost | never |

Rejected alternatives are history. A sentence copied from Options must never be read as the rule.

## Header styles to keep

Match whatever the repo uses:

```markdown
Status: Accepted
**Status:** Accepted
| Status | Accepted |
```

or a `## Status` heading with the value underneath, or MADR front matter:

```markdown
---
status: accepted
date: 2026-03-02
---
```

A superseded record says by which record: `Status: Superseded by ADR-9`. The successor carries
`Supersedes: ADR-3` in the same style.

## Default, only when the repo has no records

Directory `docs/adr/`, files `NNNN-short-title.md` starting at `0001`, Nygard shape:

```markdown
# 1. Short decision title

Date: YYYY-MM-DD
Status: Proposed

## Context

## Decision

## Consequences
```

Add `## Considered Options` only when a rejected alternative is worth remembering.

## Worked example

Before (true, but decides nothing a reader can check):

> We should keep the billing code away from the ledger internals where possible, to avoid the
> locking problems we had.

After, with the names the author confirmed (`billing/`, `Ledger`, `ledger/api.py`, `ledger.db`):

> **Context.** Two outages came from billing code holding a ledger transaction open while it waited
> on a network call. The ledger package owns its own locking.
>
> **Decision.** Code under `billing/` reads and writes ledger entries only through `Ledger` in
> `ledger/api.py`. It never imports `ledger.db`.
>
> **Consequences.** Billing cannot hand-tune a ledger query. A one-off data migration that must read
> the table directly is recorded as an exception in the commit that does it.

The reason moved to Context, the rule names what it is about, and nothing the author said was lost.
