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

## Run 3 — 2026-09-03, and the failure the checklist could not see

A **targeted subset** of eight cases (2, 4, 7, 8, 9, 10, 14, 15) against `d840850` + `2772b6d`.
**34/38.** Not comparable to run 2's 41/47 — different set, different size. Eight executors and
three graders, all on sonnet, run per the isolation rules above.

**The score is again the least useful part.** Grader B found that case 10's pasted
`register_report.py` block does not reproduce: nominalisation 9.7 claimed against 12.1 actual, a
25% gap. Independently re-verified before it was filed — deterministic script, md5-stable file,
two identical runs. Contractions matched **exactly** while nominalisation did not, which is the
signature of a check that predates an edit rather than one that was invented.

**No expectation in the set checks script-output fidelity, so case 10 scored 3/4 while carrying
it.** Both scripts now print `measured: <name> sha256:<digest>`, and `SKILL.md` requires the
artefact to be frozen before the checks run.

**A standing instruction for every future grader, whatever the case:** re-run each script
invocation the output claims to have made and check the pasted result reproduces. Grader A did
this unprompted across six invocations and all six matched byte-for-byte; grader B did it and
found the one that did not. This catches a class the numbered expectations structurally cannot.

### The four failures, and the pattern in three of them

| | what happened |
|---|---|
| **7.2** | Generate mode wrote *"we shipped a new CI pipeline **this week**"* — an invented timeline with no digit — then asserted *"The post carries exactly one fact"*. It fabricated **and certified it had not**. Run 1's failure in a new guise, caught by the expectation rewritten after run 1. |
| **8.3** | Kept *"It's a revolution."* Its own audit: *"still an unsupported hype claim… I'm not going to manufacture the evidence that would justify it"* — then shipped it. |
| **9.7** | *"So I kept all three, just de-mechanized the phrasing."* Word-level polish offered as structural variation. |
| **10.3** | Bare `/etc/nginx/` beside bracketed `<path-to-cert>` in the same step. The all-or-nothing placeholder rule, added after run 1, failing again. |

**Three of the four self-audits named the defect and delivered it anyway.** That is a different
problem from not noticing, and it is not addressed by telling the audit to look harder.

### What held

Case 4 is **4/4** — the em-dash regression PR #7 caused has not returned, despite PR #62 editing
the same Layer 3 region. Cases 14 and 15 are **11/11** from a grader briefed on the
same-sitting authorship conflict, which checked the provenance itself and then constructed a
wrong output for every expectation.

### Weak expectations named by the graders — rewrite these before a full run

`8.2` checks order only and passed on identical text with "none needed" · `8.4` counts
placeholders rather than information · `9.1`–`9.6` would pass a verbatim copy, leaving the whole
did-it-rewrite-anything job on `9.7` alone · `10.2` draws no line between a real software default
and an invented environment fact · `14.4` has an OR-branch a fabricated next action would pass ·
`14.3` and `15.2` track `ai-patterns.md`'s own wording closely enough that passing partly
confirms the executor read it · `4.3` requires the convention be acknowledged, not that the
acknowledgement be sound · `7.3` and `2.1` are near-unfalsifiable.

### The structural gap, which is the most valuable finding here

> *"A skill called clear-and-human could pass every expectation in this set while producing a
> report that is, on the whole, textbook AI-shaped prose."*

**Nothing grades the voice of the deliverable.** Every output wrapped its work in `## Self-audit`,
`## Bottom line`, bolded inline labels and numbered meta-commentary — the structuring this skill
exists to remove. The set grades fabrication exhaustively and never asks whether what it printed
reads human.

### One harness defect, ours

All eight executors were pointed at a single fixture directory and collided on scratch files.
Case 9 noticed and moved to a case-specific path; the others did not report it. The shared
`WRITING_CONTEXT.md` was verified unchanged afterwards, so the reads were clean. **Give each
executor its own working directory.**

## Run 4 — 2026-09-04, a verification run, and it did its job

**The four cases that failed run 3, re-run against the rules written to fix them.** 22/24.

| case | run 3 | run 4 | |
|---|---|---|---|
| 7 | 2/3 | **4/4** | the fact ledger works — the invented timeline is gone |
| 8 | 3/4 | **5/5** | the three exits work — the named-and-shipped defect is genuinely absent |
| 9 | 7/8 | **8/9** | **still fails 9.7** |
| 10 | 3/4 | **5/6** | fails 10.5, and **10.5 was a bad expectation** |

Executors each had their own working directory, closing run 3's harness defect.

### Case 9 is the real failure, and it is more interesting than the first one

The defect did not go. **It got better at describing itself.** Grader D: *"the same defect from
before, now wrapped in more convincing self-critique language."* The first sentence kept the
identical three-clause coordination; only the third clause got longer.

**The cause was an underspecified instruction, not disobedience.** "Vary sentence rhythm" was
read as length, which is defensible — and shape was left alone. Prose could not settle that
argument, so `register_report.py` now counts the thing being argued about:

```
  sentence 1: 3-item series  SURVIVED unchanged
```

on the exact rewrite that failed twice. Expectation 9.7 now requires that block and explicitly
refuses the output's own account of having varied the structure.

### Case 10's failure was mine

10.5 was the fact-ledger expectation **copied verbatim from case 7**, where the user supplies the
facts and the writing is about their project. A runbook's content is domain knowledge, so at the
letter it would fail *every correct runbook, including an ideal one*. Grader E called it
correctly: *"decoration in this instance… reused boilerplate, not a targeted test of the actual
risk."* Rescoped to the reader's **environment** — paths, filenames, distribution — with general
software behaviour explicitly out of scope.

**An expectation that cannot be satisfied is as bad as one that cannot fail**, and this set has
now produced one of each.

### One new finding, outside every expectation

Case 8 offered the user two versions and pasted real, reproducing script output — **without
saying which version was measured.** Grader E: *"real evidence, ambiguous referent."* The
`measured:` digest identifies bytes; it cannot identify which of two deliverables you meant.
`SKILL.md` now requires the version to be named.

### What run 4 establishes about the method

The mechanical checks are the ones that hold. Grader D: *"the mechanical checks are genuine
tests; the qualitative ones are real only when the grader refuses to accept the model's
self-description of its own fix — which is exactly the failure mode a same-sitting author writing
both the rule and its test would be least likely to have stress-tested."*

Both graders were told the fixes and their tests shared an author and a sitting, and asked to
assume the tests were shaped to pass. **Both found something.** Brief them that way every time.
