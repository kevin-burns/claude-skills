---
name: frontier-rounds
description: >
  Interview the user in breadth-first rounds until a design is settled, asking every question
  whose prerequisites are already answered in one batch rather than one at a time. Use when a
  plan, design, spec or decision needs stress-testing before work starts; when the user says
  "grill me", "stress-test this", "poke holes in this", "what am I missing", "interrogate this
  plan", "ask me what you need to know"; or when another skill needs a structured elicitation
  pass. Produces settled decisions, not deliverables. For open-ended idea generation use
  superpowers:brainstorming instead — this is for a design that already exists and needs
  pinning down.
license: MIT
allowed-tools: Read, Grep, Glob, AskUserQuestion, Agent
---

# Frontier Rounds

Interview the user until you reach a shared understanding. Map the work as a **design tree**:
every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already
settled — the questions you can ask *now* without guessing at answers you have not heard yet.
Ask the whole frontier in one round. Then wait.

Each answer reshapes the tree: settled decisions push the frontier outward and unblock questions
that depended on them. Recompute the frontier and ask the next round. **A question whose answer
depends on another question still open in this round belongs to a later round, not this one.**

## Question format

```
❓ **Q1** — **<short title>**: <the question, including options where they exist>

➡️ <your recommended answer, and the reason in a clause>
```

Number every question. Give a recommendation on every one — a question without a recommendation
makes the user do work you could have done. If you genuinely have no view, say which fact would
give you one.

## Facts are your job, never the user's

When a frontier question turns on something the environment can answer — what a file contains,
what a command prints, what version is installed, whether a path exists — **go and find out.
Never ask the user for something you could look up.**

A running lookup is an **unsettled prerequisite, not a blocker on the round**. Only the questions
downstream of it wait; ask the rest of the frontier now.

Dispatching a sub-agent for these lookups is authorised **for this skill only**, and only for
read-only environment facts whose answer is checkable. Pass `model: haiku` and low effort —
this is mechanical work. Never dispatch a sub-agent to decide, design, draft, review, or answer
on the user's behalf: **the decisions are the user's**, and putting them to the user is the
entire point.

## What to consult

When a frontier question is a design decision rather than a preference, reach into the
`software-design-rules` skill for the vocabulary — keyed to the question, not to a role, because
the frontier changes every round:

| The question turns on | Read |
|---|---|
| a boundary, or what depends on what | `rules/clean-architecture.nano.md` |
| whether a module earns its interface | `rules/a-philosophy-of-software-design.nano.md` |
| consistency, schema change, retention | `rules/designing-data-intensive-applications.nano.md` |
| what can hang, retry, or fan out | `rules/release-it.nano.md` |
| whether this is over-built | `rules/refactoring.nano.md` (Speculative Generality) |

**Use the `nano` tier during rounds.** An interview runs long and an 800-word `mini` on every
design question bloats the session least able to afford it. Step up to `mini` only when a single
question is genuinely the whole decision.

## Ask how it will be verified

Before the session ends, settle **how the work will be checked**, because the answer picks the
strategy and it is far cheaper to choose here than to argue with a plan template later:

- **Deterministic pure logic** → TDD. Red-green per task, the way `superpowers:writing-plans`
  specifies it.
- **An enumerable parameter space** → combinatorial coverage. A space you can list is one where
  a hole is a real bug and hand-picked cases will miss it.
- **Prose, a prompt, or a skill** → an ablation. There is no failing test for a markdown file;
  the question is whether removing it changes behaviour, and that is measured, not asserted.
- **A network boundary** → neither. Decide what is faked and what is probed live, and say which.

## The session is done when the frontier is empty

Every branch visited, nothing left silently assumed. **Do not act on it until the user confirms
you have reached a shared understanding**, and do not drift into building — this skill produces
settled decisions, not deliverables. The pull to start work is the signal to hand off.

## Relationship to superpowers

This sits **beside** `superpowers:brainstorming`, and never modifies it. Superpowers is an
independent plugin — the cache carries more than one version, so an edit would be wiped on
upgrade and would fork someone else's work besides.

The difference is the algorithm, not the goal. Brainstorming asks **one question per message,
strictly sequential**, which is right for an idea that has no shape yet. This asks the **whole
frontier per round**, which is right for a design that already exists: it stops serialising
questions that were never dependent on each other.

## Provenance

The design-tree / frontier / rounds algorithm, the recommended-answer-per-question format, and
the "finding facts is your job, never the user's" rule are from Matt Pocock's `grilling` skill
(github.com/mattpocock/skills, MIT, commit 9c9f36c), vendored for reference at
`docs/vendor/writing-for-agents/`. Adapted here in two ways: sub-agent dispatch is scoped to
read-only environment facts rather than left open, and the design-rules table and
verification-strategy step are additions.

Design rules content belongs to the `software-design-rules` skill, which credits its own sources.
