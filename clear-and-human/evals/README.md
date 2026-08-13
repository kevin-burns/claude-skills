# Running these evals

Eleven behavioural cases, 47 assertions. They test the **skill** — whether the prose
instructions produce good output. The `pytest` suite under `../tests/` tests the
**scripts**, which is a different thing. Both are needed; neither substitutes.

Two runs so far, both on **2026-08-13**:

| Run | Set | Against | Result |
|---|---|---|---|
| 1 | 10 cases, 40 assertions | commit `d74b2d1` | **35/40** |
| 2 | 11 cases, 47 assertions (the current file) | after PR #7 | **41/47** |

Before run 1 they had never been executed, against any version, since the file was written
on 2026-06-06. Two reasons, both fixed:

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

## The weak assertions, and what replaced them

Run 1 exposed five assertions that a wrong output could pass, which is worse than having no
assertion at all — see `grader.md`, which is explicit that critiquing the eval set is half
the grader's job. All five were rewritten before run 2:

| Was | Now |
|---|---|
| **1.2** a substring test over the whole output, so quoting the input back scored full marks | scoped to *"the report's own flags/findings section — not merely by quoting the input back"* |
| **3.2** required the phrase be flagged *"as a permission/gravity phrase"*; neither term appears anywhere in the skill, so a correct output failed on vocabulary | that wording is gone from the file |
| **5.1**'s second disjunct passed any competent review | now requires the output either name the clean-but-hollow reading or argue against it and name which tells it found instead |
| **7.2** invited a digits-only reading, which is how the fabrication in that case escaped | names the numberless kinds explicitly: *"This explicitly includes claims containing NO DIGIT"* |
| **8.3** policed three named strings and passed a rewrite that kept *"This tool is a revolution"* | extended to *"retains no unqualified superlative resting on nothing"* |

Two of the four things nothing checked are now checked: **8.4** bounds placeholder density
(*"placeholders such as `[ADD SPECIFIC EXAMPLE]` do not outnumber the substantive sentences
retained"*), and **8.2** requires the revised version to *follow* the self-audit rather than
the audit being a postscript.

## Still not checked, after both runs

Tracked as `claude-skills-een`. These survived run 2 and no assertion covers them:

- **Inflation survives paraphrase.** *"This tool is a revolution"* became *"a genuine shift
  in what's possible"* — the skill strips lexical markers reliably and the rhetorical move
  unreliably.
- **The self-audit still occasionally invents a word count**, which is core rule 1 breached
  by the very pass that exists to catch it.
- **Nothing checks whether an output's claims about files on disk are true**, or whether a
  narrated script run actually happened.
