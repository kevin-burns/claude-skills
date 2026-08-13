# Running these evals

Ten behavioural cases, 40 assertions. They test the **skill** — whether the prose
instructions produce good output. The `pytest` suite under `../tests/` tests the
**scripts**, which is a different thing. Both are needed; neither substitutes.

First run: **2026-08-13**, against commit `d74b2d1`. Result **35/40**. Before that they
had never been executed, against any version, since the file was written on 2026-06-06.
Two reasons, both fixed:

- `evals.json` sat at the skill root. The schema wants `<skill>/evals/evals.json`, which
  is where `cv-and-human` and `business-plan` keep theirs.
- The runner is not obvious. See below.

## The two harnesses, which do different jobs

**Behavioural** — these cases, with their `expectations`. There is no single command.
`skill-creator`'s SKILL.md documents a three-stage workflow: execute each prompt with the
skill, spawn a grader subagent per `agents/grader.md` writing `grading.json` with fields
`text` / `passed` / `evidence`, then aggregate:

```bash
cd ~/.agents/skills/skill-creator
python3 -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name clear-and-human
```

**Trigger / routing** — a different file, keyed on `query`, measuring whether the
description fires. `scripts/run_eval.py` runs those. **No trigger eval set exists for this
skill.** Pointing it at `evals.json` fails with `TypeError: string indices must be
integers`, because it is looking for `query` and finding `prompt`.

Gotcha that cost an afternoon: running `scripts/run_eval.py` directly raises
`ModuleNotFoundError: No module named 'scripts'`. It must run as a module from the
skill-creator directory — `python3 -m scripts.run_eval`.

## Two things that make a run valid

**Executors must not see the expectations.** Give each one only the `prompt` field.
An agent that knows what is being checked writes to the check, and the run measures
nothing. Grade with a separate agent that sees both.

**Isolate `WRITING_CONTEXT.md`.** `SKILL.md`'s voice-calibration step reads that file from
the project root, and in this repo one exists that is gitignored and personal. Six of the
ten first-run executors picked it up. Their outputs quote it and one lets it drive a
rewrite decision, so **nobody but its author can reproduce that run**.

Run from a scratch directory containing a committed fixture, or none at all — most users
will have no context file, and the no-context path is the one worth testing. The blank
template at `../WRITING_CONTEXT.md` is a reasonable fixture.

## What the first run found

The score is the least useful part. The grader's verdict: *"Yes for review work, with one
caveat. No for generate mode without a human check."*

Both generate-mode failures were **numberless**, which is why nothing caught them — case 7
invented a claim about the user's CI pipeline and then certified in writing that it hadn't,
and case 10 put an invented filesystem path into a rollback command. Core rule 1 in
`SKILL.md` now names numberless invention explicitly, and the self-audit is barred from
certifying what it did not check.

It also caught `fidelity_check.py` returning a confident clean pass on case 9, where the
input contained nothing it tracks — so it would have passed a rewrite that dropped every
claim. It now prints `NOTHING TO CHECK` instead.

## Known weaknesses in these assertions

Recorded because a passing grade on a weak assertion is worse than no assertion. See
`grader.md`, which is explicit that critiquing the eval set is half the grader's job.

- **1.2** is a substring test over the whole output, so an output that merely quotes the
  input back scores full marks. It needs scoping to the flags section.
- **3.2** requires the phrase be flagged "as a permission/gravity phrase". Neither term
  appears anywhere in the skill, so a correct output can fail on vocabulary.
- **5.1**'s second disjunct is broad enough that any competent review passes.
- **7.2**'s wording invites a digits-only reading, which is precisely how the fabrication
  in that case escaped.
- **8.3** polices three named strings and passed a rewrite that kept "This tool is a
  revolution".

Nothing at all checks: placeholder density (seven of ten outputs ended in
`[ADD SPECIFIC EXAMPLE]`, and a skill that replaced every draft with one placeholder would
score near-perfect), whether a narrated script run actually happened, invented authorial
stance, or self-audit placement.
