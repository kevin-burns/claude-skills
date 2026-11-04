# python-drill

A Python refresher and interview drill coach for Claude Code. One question at a time, answers
checked by **running the code** rather than by the model's memory, and spaced repetition so the
topics you miss come back before they fade.

It is for someone who writes enough Python to ship automation and has lost the basics a coding
test asks for: what `line.split()[3]` returns, why a lambda in a loop sees the last value, where
a script with a missing import actually stops.

Part of [claude-skills](../README.md).

## Why running the code is the point

Python edge cases are exactly where a confident answer goes wrong: late-binding closures,
mutable defaults, `round(2.5)`, a generator consumed twice, `split()` against `split(' ')`. A
drill coach that marks you from memory will sometimes mark a right answer wrong. So every
quick-fire is run before it is asked, every coding task runs against tests written before the
problem is shown, and every code-reading exercise is executed to record its real output.

## What it does

- **Daily drill (~15 minutes).** Three predict-the-output questions, one or two small coding
  tasks, and one short code-reading item, picked from the topics that are due and weakest.
- **Review round (~15 minutes).** The code-reading interview format: a short script you have not
  seen, then *would it run as written?*, *walk me through it*, *what does it print for this
  input?*, *what would you change before production?*, and one follow-up. Scored against the
  problems planted in that script.
- **String drill (~10 minutes).** One realistic line (an mbox separator, a log line, a CSV row, a
  path, a URL) and one operation: `split()[n]`, `split(sep, 1)`, `line[9:]`, `strip` against
  `removeprefix`, `find` and its -1 trap, `partition`. You say exactly what `repr()` prints.
- **Mock coding round (~30 minutes).** One live-coding problem with interviewer follow-ups.
- **Explains every miss.** Your answer next to what actually happens, the deciding line traced
  with real values, the fix, and one line to remember.
- **Never repeats an exercise.** `scripts/make_variant.py` generates code-reading exercises from
  eight families (mailbox, regex, csv, json, logs, gotchas, sql, strings), with randomised inputs
  and randomised planted problems, and keeps a list of what you have seen.
- **Tracks progress** with Leitner boxes (1, 2, 4, 8, 16 days) across 64 topics in five tracks:
  core, algorithms, code review, automation and pandas.

## What it does **not** do

- **It does not teach from scratch.** It assumes you once knew this; it is for recall, not a course.
- **It ships no book content.** The curriculum names a chapter per topic as further reading;
  every question is written fresh or generated.
- **It is not for use during a real interview or test.** Many employers forbid AI tools and some
  check.
- **It does not judge pandas from memory.** pandas changed a lot in 2.x and 3.x; the skill tells
  the model to check the current docs before calling an answer wrong.

## Install

Two ways in, depending on what you want.

**As part of the collection**: all the skills, one plugin:

```bash
claude plugin marketplace add kevin-burns/claude-skills
claude plugin install claude-skills@kevin-burns
```

**By hand**, if you would rather not use a marketplace: copy the `python-drill/` directory into
`~/.claude/skills/`. Everything the skill needs is inside it.

### Check it actually loaded

```bash
claude plugin details claude-skills@kevin-burns
```

You want `python-drill` listed under **Skills** in the component inventory.

**A trap worth knowing:** `claude --safe-mode` disables plugin-provided skills, so a skill
installed this way will not appear in a safe-mode session. That is not a broken install.

Then say "python drill", "review round" or "string drill".

## Requirements

Python 3.10 or newer. The three scripts are standard library only. Progress and the seen-list
live in `$PYTHON_DRILL_HOME` (default `~/.local/share/python-drill/`), outside the skill.
Optional: `uv`, for pandas coding tasks (`run_tests.py --pandas`) and for the three fixed
practice scripts that use SQLAlchemy.

## Usage

The skill drives the scripts; you answer questions. To run them yourself:

```bash
python3 scripts/progress.py due --n 4                 # what to drill today
python3 scripts/progress.py stats                     # coverage and weakest topics
python3 scripts/make_variant.py new --rotate          # a fresh code-reading exercise
python3 scripts/make_variant.py topics                # which topics the generator covers
python3 scripts/run_tests.py solution.py tests.py     # run a solution against check() tests
```

`make_variant.py new` prints the script, its input and the question. The answer (real output or
exception, the planted problems, the topics) goes to a separate `answers/` folder, so showing the
exercise never shows the answer.

## Testing

```bash
cd python-drill && uv run --no-project --with pytest python -m pytest tests -q
```

34 tests. Two of them re-run reference material so it cannot drift: every row of
`references/string-ops.md` is executed and compared with the result it shows, and the fixed
practice scripts in `fixtures/scenarios/` are run against the outputs `references/scenarios.md`
claims. `python3 scripts/make_variant.py selftest` checks every generator family for
uniqueness, determinism, valid Python and identical output across two runs.

The scripts in `fixtures/scenarios/` contain deliberate bugs and are excluded from `ruff` and
`bandit` for the same reason as the agent eval fixtures: `--fix` would answer the exercise.

## Provenance

Original code and exercises. `references/sources.md` links to public material on the same
topics (Python for Everybody's mailbox chapters, code-review exercise collections, the Python
FAQ on common gotchas) without copying from it.
