# Ablation harness

Answers one question about a skill: **does it change what the agent does?**

The method is from Cole Medin's `ablate-ai-layer` ([coleam00/skills](https://github.com/coleam00/skills),
MIT): strip a rule or a file, rerun the *same* task, diff the two. Tracked as
`claude-skills-5qs`.

## Running it

```bash
uv run build_arms.py     # arms A, B, C
uv run build_arms2.py    # arms D, E
uv run build_arms3.py    # arm F
./matrix.sh              # CASES="3 8" ARMS="A C" REPS="1 2 3" to select
uv run grade.py          # coverage masks, noise floor, permutation test
uv run fabrication.py    # invented-stance counts
FREEFORM=1 ./matrix.sh   # drops the JSON schema -- see below
uv run freeform_grade.py # does the ablated layer's specified output appear
```

Each run is `claude -p --safe-mode` in an empty sandbox with every file and search tool
disallowed, so no arm can read back what it was stripped of. About $0.13 of subscription
usage per run. `arms/`, `runs/` and `runs-free/` are generated and gitignored;
`runs-2026-08-15.tar.gz` holds the 156 run envelopes behind the recorded result.

## Four things this harness got wrong before it got them right

Each cost a wrong conclusion, and each is now guarded in code.

**1. Match the harness to the layer.** The forced `--json-schema` is right for measuring
what a skill *notices* and whether it *fabricates*. It is disqualifying for measuring what
a skill *produces* — it overrides output shape, so any arm ablating a report template or a
scoring rubric is guaranteed to look like a null. Arm F read as complete dead weight under
the schema and as 8/8 against 0/8 without it. `FREEFORM=1` exists for this.

**2. Leak-check the assembled text, not the source file.** Arm D's first build checked
`SKILL.md` before the references were inlined, and `channels.md` restates the no-invention
rule twice. The arm would have carried the instruction it was meant to be missing.
`build_arms2.py` now checks the final text — the only version the model sees.

**3. Measure the noise floor before believing a difference.** Compare between-arm agreement
against agreement between *replicates of the same arm*. Without that, a gap is unreadable.
With three replicates the exact permutation test cannot return below p = 0.100 whatever the
effect, so `grade.py` prints the attainable minimum beside every p.

**4. Hand-check every hit before reporting a rate.** The first fabrication metric scored
bracketed placeholders (`[Platform name]`) as invented specifics — when leaving a
placeholder is the *correct* behaviour — and matched "one" in "the right one" as a number.
It reported p = 0.0017 for an effect that was partly an artefact. Only the first-person
channel survived reading every hit individually, and only it is reported as a headline.

## Adding an arm

Copy `build_arms3.py`. It is the shortest of the three and shows the shape: locate the
material by exact marker, assert the removal actually happened, write `arms/<X>.md`. An arm
whose build silently no-ops is worse than no arm — it produces a confident null.
