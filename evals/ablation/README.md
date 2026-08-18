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
uv run build_arms4.py    # arm G
./matrix.sh              # CASES="3 8" ARMS="A C" REPS="1 2 3" to select
uv run grade.py          # coverage masks, noise floor, permutation test
uv run fabrication.py    # invented-stance counts
FREEFORM=1 ./matrix.sh   # drops the JSON schema -- see below
uv run freeform_grade.py # does the ablated layer's specified output appear
```

Each run is `claude -p --safe-mode` in an empty sandbox with every file and search tool
disallowed, so no arm can read back what it was stripped of. About $0.20 of subscription
usage per run, measured across the arm G matrix on 2026-08-18 — the $0.13 previously
recorded here was low. Generated directories are gitignored; the run envelopes behind each
recorded result are kept as tarballs beside this file: `runs-2026-08-15.tar.gz` (156
envelopes, arms A–F), `runs-2026-08-18-armG.tar.gz` (40 envelopes, the A-vs-G equivalence
result), and `superseded-2026-08-15.tar.gz` (the pre-drift arms — see lesson 5).

## Five things this harness got wrong before it got them right

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

**5. Rebuild every arm, not the one you are adding.** `arms/` is gitignored, so a new
arm is built from today's source while the others sit on disk from whenever they were last
built. On 2026-08-18 arm A was 3 days old and `references/ai-patterns.md` had gained the
reframe taxonomy in between — arm G came out *larger* than its own control. Comparing them
would have measured that commit as if it were the ablation. The banked runs have the same
problem: `matrix.sh` skips any cell whose output already exists, so a stale result is
silently reused. Rebuild all arms, and move `runs/` aside, whenever the skill has moved.
Arm G caught this only because its build asserts a *size decrease* rather than just a
missing marker.

## Adding an arm

Copy `build_arms3.py` for the shape at its simplest: locate the material by exact marker,
assert the removal actually happened, write `arms/<X>.md`. An arm whose build silently
no-ops is worse than no arm — it produces a confident null.

Copy `build_arms4.py` instead when the arm is a *pruning* candidate. It adds the two guards
that only matter then: it asserts a **size decrease** against its own control, which is what
caught the stale arms in lesson 5, and it asserts that material it *cannot* isolate is still
present — three of clear-and-human's citations live in the references as well as in
`SKILL.md`, so cutting the block does not remove them from the payload. Saying which is
which in code is the difference between a bounded result and an overclaim.
