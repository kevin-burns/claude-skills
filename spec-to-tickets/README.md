# spec-to-tickets

Prioritises and checks a breakdown of a spec before anyone builds from it. See `SKILL.md` for how
the agent uses it; this file is for the person installing it.

It borrows MoSCoW prioritisation and timeboxing from DSDM. It is not an implementation of DSDM
and covers none of its roles, phases or governance; for the framework itself, read the DSDM Agile
Project Framework handbook.

## What it needs

Nothing beyond the agent: the scripts are Python 3.12+ standard library (`uv run` or `python3`).
Installed beside `spec-ready` (as in this collection), overrides are checked against the person's
own words in the session transcript; without it they are recorded as attested.

## Heavier breakdowns

This skill checks and prioritises; it makes only a minimal breakdown itself. For a large spec, make
the breakdown first with Matt Pocock's `to-tickets` (github.com/mattpocock/skills) or Cole Medin's
`piv-slice-epic` (github.com/coleam00/skills), then run this on the result.

## Limits

- Sizes are S, M, L. The 60% rule is computed on them, so it is as good as the sizes.
- The vertical check reads the layers a slice declares; it cannot see whether the code touches them.
  The layers in the front matter are taken from the spec by the agent, so check them against the
  spec's implementation decisions: an eval run once collapsed four named adapters into one.
- An acceptance criterion that adds a figure ("five-minute", "95%") or a capitalised name
  ("TextEdit") the PRD and spec do not contain must start `Proposed:`. New scope written in plain
  lowercase words ("starts at login") has no form a script can see; that is left to your review.
- A Must's quote is checked to be at least four words from the PRD's goal, success check or
  anti-goal; whether that sentence really justifies the slice is for the person to judge.
- Overrides are checked against the person's turn when a transcript is readable; a hand-edited
  override in tickets.md is still possible, and `check` lists every override it applies.

## Evals

`evals/README.md` has the cases, the method and the results. On 2026-11-11, graded blind by a fresh
Opus grader against six expectations per case: with spec-to-tickets 16/18, without 8/18, Matt
Pocock's `to-tickets` 6/18. The with arm's two misses were unmarked figures in acceptance criteria;
after the `specifics` check, a rerun of those two cases scored 6/6 each. Routing: 142/160, with two
check-only prompts not yet routed.
