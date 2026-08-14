# clear-and-human

> Construct, review, score and rewrite prose so it reads like a person wrote it — with two
> standard-library scripts that measure register and check that a rewrite invented nothing.
> Part of [claude-skills](../README.md).

## What it does

Three layers, used singly or together depending on what you hand it.

**Construct** (generate mode) applies Strunk's constructive rules while drafting — active voice,
positive form, concrete language, needless words out, emphatic word last.

**Detect, score, report** (review mode) classifies the content type — docs, blog,
youtube-script, linkedin, email, slack — applies the universal pattern list in
`references/ai-patterns.md` plus the channel rules in `references/channels.md`, and returns a
scored report with every flag quoted verbatim and a concrete fix beside it.

**Rewrite and restore** replaces flagged patterns, varies rhythm, restores contractions the
draft expanded, and runs a self-audit that has to name what still reads as machine-written
before the final version — not after it.

Two optional scripts do the parts a model cannot do reliably by reading:

- **`scripts/register_report.py`** prints where a draft sits on two axes — PERSON (first- and
  second-person density) and STIFFNESS (contractions, analytic negation, demonstratives,
  nominalisation, word length, lexical diversity) — as rates per thousand words, each with the
  paper it comes from. **No score, no grade, no threshold.** Print a target and people write at
  the target. It refuses to report below 200 words, because one contraction in forty words
  swings the rate by 25.
- **`scripts/fidelity_check.py`** diffs a draft against its rewrite and reports every number,
  quoted span, URL and code span that appeared, vanished or changed. A number in the rewrite
  that is not in the original is the signature of a fabricated statistic, so it gets its own
  banner. On input containing nothing it tracks it prints `NOTHING TO CHECK` and says plainly
  that this isn't a pass. It also diffs a closed list of **claim words** — the words that rank,
  scope, compare or require — and quotes the sentence each one sat in, because the way a rewrite
  usually loses information is not by deleting a fact but by deleting the word that made the fact
  a claim. Cut the boldface from *"the **single most important** build"* and the ranking leaves
  with the markup.

## "Isn't this just humanizer?"

Fair question — [`blader/humanizer`](https://github.com/blader/humanizer) (MIT) is one of this
skill's sources, credited in `SKILL.md`, and its self-audit loop is where the audit pass here
comes from. It's good at what it does: 33 patterns with before/after pairs, voice calibration
that outranks the pattern list, and a no-fabrication rule.

Four differences, checked against its `SKILL.md` rather than described from memory.

**It has no register axis.** In 412 lines, "contraction" appears zero times, "Biber" zero,
"measure" zero. That's not a criticism — it is a catalogue of phrase-level and typographic
tells, and it does that job. But the failure that prompted this skill's measurement layer was a
1,375-word post with **zero contractions**, warm on five stiffness features out of six. Nothing
in a pattern catalogue sees that. It only shows up if you count.

**Three of its rules are blunter than the evidence supports**, and this skill shipped the same
mistakes before a red-team pass corrected them:

| | humanizer | here |
|---|---|---|
| Em-dashes | *"The final rewrite contains no em dashes… a hard constraint, not a 'use sparingly' preference"*, with a voice-sample override | author-relative and model-specific: only Claude uses em dashes more than professional writers, ChatGPT uses fewer, so a blanket cut is backwards for one model family |
| Curly quotes | flat rule, ChatGPT tell | qualified — macOS and Word emit them from ordinary human typing |
| Hedging | pattern #24, *"Excessive Hedging"*, listed as an AI tell | a wordiness edit, explicitly **not** an AI tell: Jiang & Hyland (2025) and Mizumoto et al. (2024) both put hedges on the *human* side |

**Its checks on the prose are the model judging its own output.** The repository's only script is
`scripts/validate-package.py`, a packaging validator. Its no-fabrication rule is strong and its
audit asks the question outright — but the answer is an attestation. This skill's first eval run
caught exactly that failing: an output that **certified in writing that it had invented nothing**,
having invented a claim about the user's CI pipeline. `fidelity_check.py` exists because a rule
the model grades itself against isn't a check.

The clearest illustration is one their own users found. Issue
[#212](https://github.com/blader/humanizer/issues/212), open and unanswered as of 14 August 2026,
reports that *"several style rules can remove information while appearing to only remove shape"* —
a superlative that ranked one item against every other in a document, deleted along with the
boldface it sat in. That failure is not specific to their skill; the equivalent rule here reads
*"change delivery, not substance"* and was, until this week, also model-attested. Both of the
examples in that issue are now fixtures in `tests/test_fidelity_check.py`, and both are reported
by the claim-word diff.

**It states no position on detectors** — "detector" and "GPTZero" appear zero times. This skill
states one, below, and cites the measurement behind it.

The honest summary: humanizer's a better *pattern catalogue* than the list here, and this skill
inherited a chunk of it. What it does not do is measure, and it does not check its own output
mechanically. That is the whole difference.

## How to use it well

- **Give it a writing sample, or a `WRITING_CONTEXT.md`.** Stripping AI patterns without
  supplying a voice leaves a void that reads as cleanly machine-written. The skill looks for
  `WRITING_CONTEXT.md` at the project root, then `FOUNDER_CONTEXT.md`, before asking.
- **Declare the stance; do not let it be inferred.** A stiff impersonal draft and a correctly
  impersonal draft are identical on person density. `register_report.py` takes `--stance` and
  prints `unset` if you do not pass one — it never guesses from the text.
- **Read the flags, not the scores.** The scores are a summary; the quoted flags are the work.
- **Run the two scripts when a draft reads formal and you can't say why.** `register_report.py`
  will tell you which feature is doing it.
- **Run `fidelity_check.py` on anything with numbers in it**, before publishing. It is the only
  mechanical check on the no-invention rule.
- **Read its claim-word rows even when the number rows are clean.** They are where a rewrite
  quietly stops ranking, scoping or requiring something. The script names the word and quotes
  its sentence; deciding whether the claim survives without it is yours.
- **Scope self-measurement.** A section reporting a document's own numbers is part of that
  document, so writing it moves them. Measure "everything above this heading" and say so.

## What it does NOT do

- **It does not score text for AI-likeness, and it never will.** Liang et al. (2023, *Patterns*
  4(7):100779) ran seven GPT detectors over 91 TOEFL essays by non-native English speakers and
  measured a **61.22% average false-positive rate**; nearly a fifth were flagged by all seven
  unanimously. A tool that produces a number people treat as a verdict inherits that failure.
- **It does not treat its pattern list as evidence of machine origin.** `ai-patterns.md` opens by
  saying so, quoting the upstream Wikipedia guidance that these are *"only potential signs of a
  problem, not the problem itself"*. A match is a reason to look.
- **It does not claim the two register axes are independent.** That claim was withdrawn: bounding
  the correlation tightly enough would need roughly a hundred same-channel documents by one
  author. Person is reported and never flagged because it is a rhetorical choice (Thonney 2013),
  not because it is statistically unrelated to stiffness.
- **It does not publish a threshold for any feature.** There's no "good" contraction rate.
- **It does not invent specifics to add texture.** No fabricated numbers, names, quotes, dates or
  citations. Where a concrete example would help, it leaves `[ADD SPECIFIC EXAMPLE]` rather than
  inventing one.
- **It does not use burstiness or readability indices.** No academic grounding for the first
  (GPTZero dropped it in autumn 2023); the second was validated on schoolchildren and Navy
  trainees, for a different question.
- **It is not a grammar checker.** The model already knows grammar. Stiffness is what it gets
  wrong.
- **It does not edit its own files.** Noticed a recurring tell that's missing? It surfaces it as
  a suggestion for you to accept, rather than rewriting itself.

## Requirements

**Nothing for the writing itself** — the skill is prose all the way down.

The two scripts are **standard library only**, so `uv run` or `python3` both work. **Python 3.12
or newer** (`dict | None` in signatures is evaluated at import time, so 3.9 — which macOS still
ships as `/usr/bin/python3` — fails at `--help`). Run them by absolute path so they work from any
working directory:

```bash
uv run ~/.claude/skills/clear-and-human/scripts/register_report.py draft.md
uv run ~/.claude/skills/clear-and-human/scripts/register_report.py --json draft.md
uv run ~/.claude/skills/clear-and-human/scripts/fidelity_check.py draft.md rewrite.md
```

Flags worth knowing: `register_report.py` takes `--stance personal|impersonal|unset` and
`--baseline <dir>`, which adds a comparison column against a directory of your own writing — the
report is complete without it. `fidelity_check.py` takes `--names` to diff capitalised words as
proper nouns, off by default because without a POS tagger it is noisy on reordered prose.

## Testing

Two suites, testing different things — both are needed and neither substitutes.

- **`tests/`** — 92 pytest tests over the two scripts, green on Python 3.12 and 3.13.
- **`evals/`** — 11 behavioural cases, 47 assertions, testing whether the *prose instructions*
  produce good output. See `evals/README.md` for how to run them, what two runs found, and the
  three defects that survived both.

## Provenance

Merged and adapted, all MIT or public domain:

- `the-humanizer.md` — channel detection, scoring rubric, structured report.
- [`blader/humanizer`](https://github.com/blader/humanizer) (MIT) — soul/voice section and the
  self-audit loop.
- `softaworks/agent-toolkit/writing-clearly-and-concisely` (MIT; orig. @joshuadavidthomas) — the
  Strunk layer.
- *The Elements of Style*, Strunk 1918 (public domain).
- `ognjengt/founder-skills` (MIT) — the shared-context-file pattern.

The scripts' features come from the register and authorship literature, not from AI-detection
tooling: Biber (1988) for the involved/informational loadings, Herbold et al. (2023, *Scientific
Reports* 13:18617) for suffix-counted nominalisation, Pavlick & Tetreault (2016, *TACL* 4, 61–74)
for contraction expansion as a discrete formalising edit. The vocabulary list is partly sourced to
Kobak et al. (2025, *Science Advances* 11(27):eadt3813) — 32 of its 56 words appear in that
dataset's 407 style words, 24 do not, and the file states the split rather than presenting all 56
as one list.

Full citations, including the contrary evidence, are in `SKILL.md` and the script docstrings.
