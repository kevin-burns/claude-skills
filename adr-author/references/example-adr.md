# A complete example record

An invented project, written the way this skill aims to write. Copy the shape, not the content.
The notes after it say what each part is doing.

```markdown
# 12. Billing reads the ledger only through its API

Date: 2026-03-02
Status: Accepted
Supersedes: ADR-7

## Context

Billing code used to query the ledger tables directly. When a billing request held a ledger
transaction open while it waited on the payment provider, other writers to the ledger stalled, and
checkout timed out. It happened more than once before the cause was found.

The ledger package already handles its own locking, and it is the only code that knows how its
tables relate. ADR-7 asked billing to "avoid" the tables where it could; reviews kept arguing about
what "where it could" allowed.

## Decision

Code under `billing/` reads and writes ledger entries only through `Ledger` in `ledger/api.py`.
It never imports `ledger.db`.

Amounts cross this boundary as `Money` from `money/money.py`, never as a float.

## Consequences

- Every ledger access from billing is visible in one place, so a slow or held transaction can be
  traced to one call site.
- Billing cannot hand-tune a ledger query. If it needs a read the API does not offer, the ledger
  team adds it to `Ledger`; billing does not work around it.
- A one-off data migration that must read the tables directly says so, with the reason, in the
  commit that does it. It is an exception, not a precedent.
- ADR-7 is superseded: its "avoid where possible" is replaced by the rule above.

## Considered Options

- **Keep direct table access, with a review checklist.** Rejected: ADR-7 was effectively this, and
  reviews could not agree what it allowed.
- **Give billing its own copy of the ledger data.** Rejected: two copies of the money records
  would have to be reconciled, which is the harder problem.
```

## What each part is doing

| Part | Job | What makes it good here |
|---|---|---|
| Title | the decision as a statement | says the rule, not the topic ("Billing reads the ledger only through its API", not "Ledger access") |
| Date, Status | when, and whether it is in force | Accepted because the team agreed it; a new record starts as Proposed |
| Supersedes | which record this replaces | the old record's status changes to "Superseded by ADR-12" in the same change |
| Context | why the decision was needed | the incident and the force behind it, in plain words; nothing here is a rule |
| Decision | what must and must not happen | names the code (`billing/`, `Ledger`, `ledger/api.py`, `ledger.db`, `Money`), one rule per sentence, "only" and "never" meant literally |
| Consequences | what gets easier, harder, or forbidden | includes the cost the team accepts, and how an exception is handled |
| Considered Options | alternatives worth remembering | each says why it lost, so nobody re-proposes it without new information |

## Best practice, as a checklist

- One decision per record. Two decisions that change for different reasons get two records.
- The title states the decision.
- Context explains; Decision and Consequences bind; Considered Options never bind.
- Each rule names the code it is about, using names that exist (or are clearly marked as planned).
- "Must" and "never" mean exactly that. If the team means a preference, say "prefer" and accept that
  it will be read as one.
- Say what the decision rules out, not only what it allows.
- Every fact has a source: the author said it, or the repository shows it. No invented incidents,
  numbers or dates.
- Consequences include the cost, not only the benefit.
- A record is never deleted. When the decision changes, a new record supersedes it, and the old one
  says by which.
- Exceptions are recorded with their reason, the way the team already records them.
- Short is fine. A record that answers "what did we decide, why, and what does it rule out?" is done.
