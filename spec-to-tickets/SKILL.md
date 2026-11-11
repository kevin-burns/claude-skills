---
name: spec-to-tickets
license: MIT
description: >-
  Turn a spec into a breakdown worth building from: prioritise and check an existing breakdown (or make a minimal one) so every slice is vertical, the first increment is a walking skeleton, every Must traces to the PRD, and each timebox keeps DSDM's MoSCoW contingency. A script checks the result; tickets go to beads, GitHub or Linear only when asked. Use for "break the spec into tickets", "prd-to-tickets", "prioritise these issues", "MoSCoW this backlog", "what do we build first", "slice this into vertical increments". Not for writing the PRD or spec (spec-ready) or a slice's implementation plan (writing-plans).
---

# spec-to-tickets

Breaking a spec into tickets is common; checking the result is not. Breakdowns come back as
horizontal layers, with every ticket important, nothing held in reserve, and tickets nobody can trace
to what the product is for. This skill is a thin layer over whatever breakdown exists: it rewrites it
into one format, proposes priorities from the PRD, and has a script check it. Its centre is
prioritising by outcome: what achieves the best result, and what to build now.

## The rules above all others

1. **Prioritise by outcome.** A Must is a Must because the PRD's goal, success check or anti-goal
   needs it, and the slice says which. Everything else is Should, Could or Won't Have this time.
2. **Vertical first.** A slice cuts through every layer it needs and can be shown working on its own.
   Horizontal work is allowed only as a labelled prefactor or expand/migrate/contract step.
3. **No invented scope.** A slice traces to a user story or a PRD line, or starts `Proposed:`.
4. **The person confirms; the script checks.** You propose priorities and sizes; the person confirms
   them in one round; `check_tickets.py` checks the result.
5. **No personal data in the skill.** DSDM is cited and paraphrased, never copied.

## Steps

Scripts are in this skill's `scripts/` directory; run them with `uv run` or `python3`.

1. **Inputs.** Find the PRD and spec (spec-ready's `prd.md` and `spec.md`, or any others) and, when
   present, `readiness.json` beside the PRD.
2. **Breakdown.** Ask where the existing breakdown is (issue files, a tickets document, a beads list).
   If there is none, make one vertical slice per user story, then merge or split to size.
3. **Rewrite** it into `tickets.md` beside the spec, in the format in `references/tickets-format.md`.
   Take the layers from the spec's implementation decisions (ask once if it names none). The
   original breakdown stays untouched and is named in `source:`.
4. **Propose and confirm, in one round.** For every slice show its MoSCoW, size and trace, grouped
   into increments of the timebox (one week unless the person names another), increment 1 a walking skeleton. The person confirms or changes them; you edit `tickets.md`.
5. **Check.** Run `check_tickets.py check <dir>/tickets.md` and fix what you can. It exits 0 when
   clean, 1 on findings, and exits 2 when it is clean only because of attested overrides. It also
   lists every override it applied and every `Proposed:` slice, so the person can see them. A Must cannot be `Proposed:`: it traces to the PRD's goal, success check or anti-goal. What only the
   person can decide (more than 60% Must in an increment, no Could, a Must with no trace), ask.
   Run check_tickets.py accept only when the person says so:
   `check_tickets.py accept --tickets <dir>/tickets.md --rule <rule> [--slice <id or increment-N>] --turn <id> --quote "<their words>"`,
   where the turn is the one in which they decided and the quote is copied from it. For `mix` and
   `contingency` the slice is the increment, written `increment-N`. If accept says "recorded as
   attested" (no transcript could be read), tell the person: their words were not checked.
6. **Hand over.** Name the slices whose blockers are done as ready. Each gets its plan from
   `superpowers:writing-plans` just in time, when work on it starts: a slice that depends on another
   is planned after that one is built. Create tickets only when the person asks, in what they use:
   beads (`bd create`, with `bd dep add` for blockers), GitHub (`gh issue create`, blockers in the
   body), or Linear (the `use-linearis` skill).

## What the checks are

`references/rules.md` lists the eight checks and why each exists; `references/worked-example.md`
shows a breakdown that passes them; `references/dsdm.md` holds the DSDM points behind MoSCoW,
the 60% guidance and timeboxes.

## Credit

The slicing ideas come from Matt Pocock's `to-tickets` (tracer-bullet vertical slices, blocking
edges, expand-migrate-contract) and Cole Medin's `plan-create-stories` and `piv-slice-epic` (slices
sized for one agent loop, parallel worktrees, just-in-time planning), both MIT; tracer bullets from
Andrew Hunt and David Thomas, *The Pragmatic Programmer*; MoSCoW, the Minimum Usable SubseT and
timeboxing from the DSDM Agile Project Framework, published by the DSDM Consortium.
