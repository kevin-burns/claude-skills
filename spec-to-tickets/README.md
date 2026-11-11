# spec-to-tickets

Prioritises and checks a breakdown of a spec before anyone builds from it. See `SKILL.md` for how
the agent uses it; this file is for the person installing it.

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
- An accepted `mix` override without `--slice` applies to every increment.
