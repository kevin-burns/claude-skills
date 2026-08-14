# Changelog

Notable changes to the skills in this repo.

Entries are written to be useful to **both a human skimming for what's new and an agent deciding
whether a skill applies**. Each one says what the skill does, *when to reach for it*, and — the part
that usually matters more — **what it deliberately won't do**. A boundary is a design decision here,
not a missing feature, so it is recorded as such.

Dates are the date the work landed on `main`.

---

## 2026-08-14

### Added — `fidelity_check.py` can see the claim that leaves with the markup

The script tracked numbers, quoted spans, URLs and code spans. It now also diffs a closed list
of **claim words**: the words that rank, scope, compare or require. New section at the foot of
the report, on by default, and each row quotes the sentence the word sat in so a finding is
somewhere you can go rather than a count you have to grep for.

**Why this was a hole and not a nice-to-have.** clear-and-human's second core rule is *"change
delivery, not substance"*, and the script exists precisely because a rule the model grades
itself against is not a check. But the rule's most common breach touched none of the four
tracked span types. Take the boldface off *"the **single most important** new build"* and you
have deleted a ranking against every other item in the document, in what looks exactly like
markup cleanup. Tidy *"it is simultaneously A, B and C"* into a clean rule of three and you have
deleted the claim that they hold at once. Neither rewrite moves a number, a quote, a URL or a
code span. Both used to pass clean.

**Both examples come from [`blader/humanizer`](https://github.com/blader/humanizer) issue
[#212](https://github.com/blader/humanizer/issues/212)**, filed 9 August 2026 and still open and
unanswered on 14 August. Their report names it better than we had: *"several style rules can
remove information while appearing to only remove shape."* That is not a bug in their skill in
particular — it is a property of the style rules both skills apply — and their two examples are
now fixtures in our test suite.

**What it deliberately does not do:**

- **It does not judge.** Every row may be a correct cut, and plenty are — the report says so in
  its own preamble. It names the word, quotes the sentence, and stops. Deciding whether the
  claim survives the deletion needs a reader.
- **It ignores intensifiers.** *Very, really, quite, extremely* assert nothing on their own;
  "very large" and "large" make the same claim with different force, and cutting them is the
  textbook omit-needless-words edit. A check that fires on every correct run is one nobody reads.
- **It ignores bare `not` and `no`.** Strunk's *put statements in positive form* is Layer 1 of
  this same skill, so correct rewrites delete these constantly. The emphatic negations a style
  edit has no business touching — *never, none, neither, nor, cannot* — are kept.
- **It does not silence the vacuity warning.** Claim words are near-ubiquitous in real prose, so
  counting them toward "was there anything here to check" would suppress `NOTHING TO CHECK` on
  exactly the numberless drafts it was added for. Two counters, and the warning still reports
  only the four hard span types. A report built from claim words alone now carries that warning
  as a footer.

One group is not assembled by judgement: **requirement** is the RFC 2119 key-word list (Bradner,
S., BCP 14, RFC 2119, March 1997), so downgrading a doc's *must* to a *should* shows up as one
word vanishing and another appearing. Borrowed as a word list only — RFC 8174 (Leiba, B., May
2017) confines the defined meanings to the uppercase forms, and this matches case-insensitively
over ordinary prose. The other three groups say in the source that they are judgement calls.

**Measured before shipping it on by default.** Run across two real prose edits from this repo's
own history — a 2,360-word README restructure and a 2,065-word reference-file rewrite — it
produced 8 rows and 3 rows. The first row of the first run was a deleted *"the main reason"*.

## 2026-08-13

### Added — `ai-patterns.md` learns to spot a writer rating their own evidence

One entry in the Structural section, for a family the list had no name for:

> **Evidence-rating asides:** "which is the part I didn't expect", "and that's the interesting
> bit", "works better than you'd expect", "which is where it gets strange".

Signposting facing backwards. The list already covers the forward version — *"Let's dive in",
"Here's what you need to know"* — announcing what is coming. These do the same job to what has
just arrived: they tell the reader how to feel about evidence instead of presenting it.

**Found by ear, not by rule.** Kevin flagged four of these across two days in a draft I had
written, and each time the check was the same: measure it against his own published corpus.
"cuts both ways", "the part I didn't expect", "than you'd expect", "than expected" — **zero
occurrences across eight documents**. What he does instead is state the fact and let it carry:
*"The real drift identity turned out to be a different app registration entirely."*

Two notes ride along with the entry because both cost time to work out. The
hedged-comparative form usually **also splits the verb from its complement**, so the repair is
word order rather than vocabulary — an agent asked to make prose "more natural" will reach for
a thesaurus and fail. And the entry says to check the author's own corpus before flagging,
because a writer who genuinely uses these is not doing anything wrong. That is the standing
rule for every item on the page, and it is worth restating on the one that is easiest to
over-apply.


### Added — the repo installs on Codex too

`.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json`, alongside the Claude pair
added the same day:

```
codex plugin marketplace add https://github.com/kevin-burns/claude-skills
codex plugin add claude-skills@kevin-burns
```

Verified on `codex-cli 0.147.0` — installs, and all **21 skills load**, namespaced
`claude-skills:<name>` exactly as Claude Code namespaces them.

**The field that decided this was worth doing was undocumented, so it got tested.** OpenAI's
reference says only that `skills` "points to bundled components relative to the plugin root" —
no type. Every one of **23 real-world manifests** found by code search uses a *string*, always
`"./skills/"`, which would have meant moving all 21 skill directories and breaking every symlink,
the packaged `.skill` files and `register_report.py --baseline` paths. So a throwaway plugin was
built with `"skills": ["./alpha", "./beta"]` — two skill directories at the root, no `skills/`
folder, our exact shape — installed, and Codex asked to enumerate. Both loaded. **The array form
works and no restructure was needed.**

One trap worth recording: the marketplace entry's `source` is an **object**,
`{"source": "local", "path": "./"}`, not the bare string Claude's marketplace uses. Get it wrong
and the marketplace registers with **no error** and lists zero plugins.

Not included: submission to OpenAI's public plugin directory. That is a separate decision about
publishing under a personal name, not a packaging detail.

### Changed — `excalidraw-diagram` can now decline to draw

One sentence, added as the **Necessity Test** ahead of the two tests that were already there:
*"Would a table or a paragraph do the same work? If yes, write that instead and say why…
Declining to draw is a valid deliberation."*

Borrowed openly from [`cathrynlavery/diagram-design`](https://github.com/cathrynlavery/diagram-design),
whose pre-output checklist asks the same question and asks it first. It is the best idea in that
skill and it costs a sentence.

It belongs here more than the three feature gaps found alongside it. This skill exists to produce
**branded diagrams for enterprise presentations** — it was forked from `coleam00`'s because that
one was sluggish and gave no palette control, and palette control is the point. Measured against
that job, a diagram that should have been a table is the common failure, not a missing Mermaid
importer. Mermaid/draw.io import, an accessible-SVG contract and static geometry tests are now
**P4** and stay there until somebody asks.


### Fixed — the zero-contraction rule was falsifiable by the author's own pre-LLM writing

`ai-patterns.md` ended its expanded-contractions entry with a flat assertion: *"A long draft
with short words and casual asides but zero contractions has been through a find-and-replace,
not written that way."* No threshold, no hedge, and in a file whose own opening says a match is
a reason to look rather than a verdict.

**Two dead blogs, recovered from the Internet Archive, falsify it as written.** Fifteen
documents from 2008–2012 — a decade before any model could have touched them — average **3.7
contractions per 1,000 words**, and **6 of the 15 sit at exactly zero**. They are warm on every
other measure: 27.6 first person, 25.2 second person, nominalisation 17.6.

The rule survives with two qualifiers it should always have carried:

- **Length carries the signal.** Those six average 313 words, where 11 per 1,000 predicts about
  three contractions — so zero means nothing. At 1,800 words it predicts twenty, and zero means
  something. **Roughly 800 words is the floor** below which the observation is too weak to raise.
- **Channel beats length.** The same author's technical blog runs 11–29 per 1,000; his product
  blog ran 3.7. One fifth the rate, same person, no LLM in sight, because it is a different job.
  Compare against the author's own corpus with `register_report.py --baseline <dir>` rather than
  a global range. The eight-document range published on 2026-08-12 is a range for one channel.

"has been through a find-and-replace" is now "is worth asking about", which is what the rest of
the file already claims a pattern match means.


### Added — the repo installs as a Claude Code plugin

`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` make the whole set installable
in two commands:

```
/plugin marketplace add kevin-burns/claude-skills
/plugin install claude-skills@kevin-burns
```

No directories moved. The 21 skills sit at the repo root rather than under `skills/`, and the
manifest's `skills` field points at them in place.

**One plugin, not twenty-one, and the repo settles it.** Twelve of the 21 skills name a sibling
inside their description — `cv-and-human` points at `cv-evidence-base`, `report-builder` at
`c7search`, `dev-fleet` at `source-snapshot`. Split them and every one of those pointers is a dead
end for anyone who installed half the set, including the `cv-and-human` ↔ `cv-evidence-base` fork
tuned at 84/84.

**What it costs, measured rather than estimated.** `claude plugin details` reports **~5.9k tokens
always-on** for the full set — every skill's description is loaded in every session so Claude can
decide when to reach for one, before any skill fires. That figure is now in the README next to the
install command, because someone who wants two of these skills should symlink two of them.

**Two findings from testing the install, both recorded rather than papered over.** The manifest's
`agents` field — documented as replacing the default `agents/` scan — loaded **zero** agents on
Claude Code 2.1.231 when given the file paths the reference prescribes, and rejected directory
paths outright with `agents: Invalid input`. The default scan works, so the field is omitted; the
consequence is that `agents/commit-style.md`, a playbook `commit-pr` reads rather than an agent,
loads as a ninth agent with empty metadata. Separately, `agents/coherence-checker.md` had a
description YAML could not parse — an unquoted `advisory: it reports` — so at runtime it loaded
with **every frontmatter field silently dropped**, including its `tools` and `model`. That one
predates the plugin work and affected the existing install path too; packaging is just what
surfaced it.

Symlinking is still the right path for anyone editing these skills, and the README now says which
to choose and why rather than listing both neutrally: a plugin install is a snapshot in
`~/.claude/plugins/cache/`, a symlink keeps this repo the source of truth.

Also documented: **these skills work outside Claude Code**, since a skill is a directory with a
`SKILL.md` and nothing more. OpenCode reads `~/.claude/skills/` directly, so a symlink already made
for Claude Code needs no second install; Codex reads `~/.agents/skills/`. The
subagents are the part that doesn't travel: `agents/*.md` uses Claude Code's frontmatter.

> **Correction, 2026-08-13:** this entry originally said neither had a plugin/marketplace format.
> That is wrong. Codex has `.codex-plugin/plugin.json` with marketplaces at
> `.agents/plugins/marketplace.json`, plus a public directory shared with ChatGPT. Tracked as
> `claude-skills-8y4`.

### Added — `clear-and-human` finally has a README, and it answers the obvious question

Fifteen of the 21 skills shipped the per-skill "what it does / what it *doesn't* do" README that
`CONTRIBUTING.md` requires. The flagship did not. It does now, and `check_conventions.py` no
longer grandfathers it.

The section that earns its place is **"Isn't this just humanizer?"**, because that is the first
reaction a reader has, and [`blader/humanizer`](https://github.com/blader/humanizer) is genuinely
one of this skill's sources — the self-audit here *is* its audit loop. The answer is four
differences, each checked against its `SKILL.md` rather than described from memory:

- **No register axis.** In its 412 lines, "contraction" appears **zero** times, "Biber" zero,
  "measure" zero. It is a catalogue of phrase-level and typographic tells and it does that job
  well. But the failure that prompted the measurement layer here — 1,375 words, zero
  contractions, warm on five stiffness features out of six — is invisible to a pattern list. It
  only shows up if you count.
- **Three rules blunter than the evidence supports**, all three of which this skill shipped too
  until a red-team pass corrected them: em-dashes as a hard constraint, curly quotes as a flat
  ChatGPT tell, and hedging listed as an AI pattern when two peer-reviewed studies put hedges on
  the *human* side.
- **Its checks on the prose are the model grading its own output.** The repository's only script
  is `scripts/validate-package.py`, a packaging validator. Its no-fabrication rule is strong — but
  run 1 of these evals caught an output that **certified in writing that it had invented
  nothing**, having invented a claim about the user's CI pipeline. That is why
  `fidelity_check.py` exists.
- **No stated position on detectors** — "detector" and "GPTZero" appear zero times.

Stated plainly in the README, because it is the honest reading: humanizer is a better *pattern
catalogue* than the list here, and this skill inherited a chunk of it. What it does not do is
measure, or check its own output mechanically.

### Changed — `clear-and-human` withdraws a claim it could not defend, and sources its wordlist

Two PRs (#7, #8) from a red-team pass, two research agents, and the first two runs of
behavioural evals that had never been executed since the file was written. Most of what
follows is a retraction. That is the point of recording it.

**Withdrawn: the two register axes are no longer called "independent."** That was a
falsifiable empirical claim resting on four documents. Establishing it needs roughly
95–100 same-channel documents by one author — the 95% CI half-width around ρ=0 is ±0.36
at N=30, which does not even exclude the correlation Biber's own loadings imply. Running
the test on the nine documents available returned nothing significant either way: the
largest of fifteen correlations was −0.61 against a critical value of 0.666.

Two justifications replace it, neither needing statistics. Biber reads Dimension 1 as
**two parameters himself** at 1988:107 — purpose, and production circumstances — and
Heylighen & Dewaele (1999) read the same page the same way while objecting that he has
*"some difficulty fitting the empirically derived factor into a single theoretical
construct."* Separately, Thonney (2013) reports first person as a rhetorical choice
varying by discipline and within genre, which is what licenses reporting person and never
flagging it. The contrary evidence is recorded in the docstring rather than omitted:
Heylighen & Dewaele factor-analysed a single held-constant situation and still recovered
pronouns loading on one explicitness factor.

**Three features did not measure what their citations described.** Demonstratives counted
complementiser and relativiser *that* — "I said that he left", "the thing that matters" —
so Biber's demonstrative *pronoun* loading of .76 sat beside a number measuring something
else. Now matched conservatively in clause-initial position, verified 8/8 on discriminating
cases. Rates fell from 10–29 per 1000 words to 0–3, which is the right order of magnitude
and also makes the feature a candidate for deletion. Analytic negation overlaps
contractions by design and is now documented as such, including the consequence: expanding
every contraction leaves the negation rate exactly unchanged.

**`fidelity_check.py` was returning a confident pass over an empty set.** On an input with
no numbers, quotes, URLs or code spans it printed "No tracked differences" — and would have
printed it for a rewrite that dropped every claim. It now prints **NOTHING TO CHECK** and
says so plainly: *"It would report a clean result for a rewrite that dropped every claim in
the text. This is not a pass."*

**The vocabulary list is now two-thirds sourced, having never been sourced at all.** Kobak
et al. (2025, *Science Advances* 11(27):eadt3813) derived 900 excess words from 15
million-plus PubMed abstracts by extrapolating each word's 2021–22 trend and measuring the
gap; the annotated list is published under MIT at `berenslab/llm-excess-vocab`. **32 of our
56 appear in its 407 style words. 24 do not**, and both lists are written out. The 24 are
not thereby wrong — the corpus is biomedical, so *synergy*, *scalable* and *paradigm* would
not surface there — but the file now states the partition instead of presenting 56
assertions as one list.

**What it deliberately won't do:**

- **Import the other 407 style words.** They describe an academic-abstract register, and
  pulling them into a skill used for blogs and product writing would drag that register
  with them. The list is maintained upstream; a copy here goes stale. Cite it, don't mirror
  it.
- **Mirror Wikipedia's pattern list.** Same reason, more sharply: that page has 1,986
  revisions and was edited the day before this entry. It also carries an editorial rule
  requiring a reliable non-pop-science source per word, which our inherited entries do not
  meet.
- **Treat wordiness as evidence of a machine.** "in order to" and its relatives are listed
  upstream under signs of *human* writing, observed over 25 years. Hedges likewise: Jiang &
  Hyland (2025) found ChatGPT essays carry *"a significantly lower frequency of
  interactional metadiscourse, such as hedges, boosters, and attitude markers"*, and
  Mizumoto et al. (2024) found human essays higher in modals and epistemic markers. Both
  classes are now tightening edits, explicitly barred from counting toward AI-likeness.
- **Apply typographic rules model-agnostically.** A July 2026 study cited upstream found
  only Claude using em dashes more than professional writers, with ChatGPT using fewer, and
  GPT-5.1 changed to suppress them. Curly quotes fire on ordinary macOS and Word output and
  miss two current model families. Both are now author-relative.
- **Rank "uniform sentence length" as the loudest tell.** The ranking had no source, and the
  upstream page does not discuss the topic at all.

**The evals ran for the first time**, and the score was the least useful part. Run 1: 35/40,
with both generate-mode failures *numberless* — an invented claim about the user's CI
pipeline plus a false self-certification, and an invented filesystem path in a rollback
command. Core rule 1 now states that a specific need not contain a digit and names the four
kinds that got through; the self-audit may no longer certify what it did not check, nor
claim a script was run without showing its output. Run 2: **41/47** on a harder set, with
the grader's verdict *"generate mode is safe now"* and eleven quoted script invocations
reproducing byte-for-byte.

Known and unfixed: inflation survives paraphrase — "this tool is a revolution" became "a
genuine shift in what's possible" — so the skill strips lexical markers reliably and the
rhetorical move unreliably. The self-audit still occasionally invents a word count. And
nothing checks whether an output's claims about files on disk are true.

`evals/README.md` records how to run any of this, which nobody previously knew.

---

## 2026-08-12

### Added — `clear-and-human` measures register instead of judging it by eye

> **Correction, 2026-08-13:** this entry called the two axes *independent*. That claim was
> withdrawn the next day — see the 2026-08-13 entry above. It is struck rather than
> rewritten, because what shipped on 2026-08-12 did assert it.

**What:** two standard-library scripts, and the rule that measuring the skill's own output
turned up. `scripts/register_report.py` reports where a draft sits on two ~~independent~~ axes,
printing the source behind each feature and no score. `scripts/fidelity_check.py` diffs a
draft against its rewrite and flags any number, quote, URL or code span that appeared,
vanished or changed. Neither needs a corpus or any configuration, so both work on a first
run for anyone who installs the skill.

**The rule that was missing:** the skill had nothing to say about contractions, in a file
whose whole job is making prose sound like a person. Contractions carry the highest loading
of any single feature, .90, on Biber's involved/informational dimension. Measuring eight of
Kevin's published posts found one at **zero contractions across 1,375 words** while otherwise
reading warm: the shortest words in the corpus at 4.61 characters, low nominalisation, and
the highest analytic negation of anything he has published. Five of six stiffness features
said warm. Only contractions said stiff. That is a find-and-replace applied over warm prose,
not a formal register, which is what Pavlick & Tetreault (2016) measured when they found
contraction expansion in 16% of human formalising rewrites.

**When to reach for the scripts:** when a draft reads as formal and you cannot say which
feature is doing it, or when you need to prove a rewrite invented nothing. A number present
in the rewrite but absent from the original is the shape of a fabricated statistic, and that
is the one thing a model cannot reliably check about its own output.

**Person and stiffness are separate axes,** and `references/channels.md` now says so. A
product write-up legitimately has no "I". Person density is reported as context and never
flagged; stiffness is flagged regardless of stance, because none of its features require
first person. Stance is declared or asked for, never inferred, since a stiff impersonal
draft and a correct impersonal draft are identical on person density.

**What it deliberately won't do:**

- **Detect AI.** Liang et al. (*Patterns* 4(7):100779) measured a **61.22%** average
  false-positive rate across seven detectors on 91 essays by non-native English writers,
  with 19.78% flagged by all seven. A skill published under an MIT licence should not ship
  that failure mode to strangers.
- **Score burstiness.** No academic grounding was located for it, and GPTZero dropped
  perplexity and burstiness in autumn 2023. The numeric thresholds circulating online trace
  to marketing copy.
- **Compute a readability index.** Flesch (1948), Kincaid et al. (1975) and Coleman & Liau
  (1975) were validated on schoolchildren's textbooks and Navy trainees, not on whether prose
  sounds like a person. Optimising toward one is grammar-checker work, which this is not.
- **Give a verdict.** No score, no grade, no pass/fail, no threshold to write toward. Both
  scripts print rates and citations. `register_report.py` refuses below 200 words rather than
  emit a rate that is mostly noise.
- **Guess at proper nouns by default.** Without a POS tagger the heuristic returns 88
  "proper nouns" on this skill's own reference file, including *Apply*, *Cut* and *Delete*.
  It sits behind `--names`.

**Also raises the repo's Python floor to 3.12.** 3.9 reached end-of-life on 2025-10-31 and
every PEP 723 script here already pinned `>=3.10` or `>=3.12`. The cost is real and recorded
in `CONTRIBUTING.md`: macOS ships 3.9.6 as `/usr/bin/python3`, so the documented plain-python3
path no longer works on a stock Mac, and CI loses the 3.9 leg that had caught two defects
newer interpreters hide. `job-feeds` keeps its 3.9+ claim, checked rather than assumed, marked
as working but no longer CI-watched.

72 tests on 3.12 and 3.13. PR #5.

---

## 2026-08-10

### Fixed — `cv-and-human`'s description was truncated past 1,536 characters

**What was wrong:** Claude Code truncates the combined `description` and `when_to_use`
text at **1,536 characters** in the skill listing. This description ran to **1,816**, so
its last 280 characters were written and never read. What sat in them was the carve-out
routing open positioning questions to `cv-evidence-base` — half of the fork measured at
**84/84** across 3 reps on 2026-07-29 and recorded two entries below. It had been
invisible to the router ever since.

Now **1,446 characters**, with 90 to spare. `cv-evidence-base` moved from 79 characters
past the cap to 205 inside it.

**Why nothing caught it:** truncation is not an error, so no run failed. And the contract
test asserting `cv-evidence-base` appears in the description passed throughout, because
it read the file rather than the listing. It now reads a `_visible_description()` cut at
the cap, and a second test asserts the cap directly. Both are falsified by mutation.

**One near miss worth recording.** The first trim removed three phrases that no test
asserts, and all 31 tests still passed. The router harness targets all three: `"Punch up
the experience bullets on my LinkedIn profile"`, `"Help me with my personal brand
positioning on LinkedIn"`, `"Am I pigeonholed as a DevOps engineer?"`. The last one was
the risk. `pigeonholed` sits inside the **Do NOT use** clause, so deleting it takes away
a barrier rather than a trigger, and this skill would have started absorbing work that
belongs to `cv-evidence-base` — the fork the change existed to protect. All three are
back, paid for out of capability prose that does no routing work.

**On where boundaries go:** the displaced "not for a blank-page CV or generic career
advice" line moved into the body's *What this skill will NOT do*, not into `references/`.
Reference files bind only when a workflow step points at them, so a scope statement there
would not bind at all. The description is capped and carries routing; the body carries
what has to hold on every run; `references/` carries depth a step fetches.

**Verified by** re-running the router harness: 168 live calls over 28 utterances × 3 reps
× 2 arms. Baseline **84/84**, proposed **84/84**, zero regressions per utterance against
the 2026-07-29 run.

---

## 2026-08-05

### Added — `job-feeds`

**What:** aggregates eight sanctioned public job feeds into one deduplicated SQLite store,
matches postings against career lanes you define, and renders a filterable self-contained HTML
report. Sources: Arbeitnow, Jobicy, Remotive, Remote OK, Working Nomads, 4 Day Week, We Work
Remotely and Python.org Jobs — weighted towards the German and EU-remote market.

**When to reach for it:** monitoring job boards over time rather than searching once. Because it
keeps a `first_seen` per posting, it answers the question the feeds themselves cannot — what is
genuinely new since you last looked. Every feed returns a rolling window with no notion of
newness, so without a local store each fetch looks like a fresh set of results.

**What it deliberately won't do:**

- **Scrape.** Only documented JSON APIs and RSS feeds. No HTML parsing, no sitemaps, no JS
  rendering.
- **Work around a block.** Two boards were dropped from the source list for this reason:
  Himalayas returns 403 to any honestly-identified client despite its `robots.txt` saying
  otherwise, and aijobs.net has no feed at its documented path. Spoofing a browser past either
  would be circumventing an access control.
- **Touch LinkedIn.** Different auth model, different risk, separate tool.
- **Republish.** Personal aggregation only. In the EU the *sui generis* database right
  (§§ 87a–87e UrhG) attaches to a substantial extract even though no individual posting is
  copyrightable.
- **Store recruiter contact details.** Emails and phone numbers are stripped at ingest, before
  anything reaches disk.
- **Strip attribution.** Remote OK requires a dofollow backlink as a condition of API access;
  the report carries it.
- **Invent data.** Three sources publish no dates at all; those rows render as `—`, never as
  today.
- **Rank or judge fit.** It matches your regexes and shows what matched.

**Two design notes worth recording.** A source whose payload loses a required field is rejected
*wholesale* and reported as `degraded`, rather than half-parsed — a partial parse yields rows
full of silent nulls, which reads as a quiet day rather than a broken feed. And rate-limit state
lives outside the database on purpose, so rebuilding `jobs.db` cannot make the tool forget it
already polled.

Standard library only, so `python3` works as a runner alongside `uv`. No API keys, no accounts.

---

## 2026-07-29 (later)

### Added — `cv-evidence-base`, and a routing fork with `cv-and-human`

**What:** a skill that interrogates a CV to recover the evidence that never made it onto the
page, and grades which role archetypes the person is genuinely credible for — deriving those
archetypes from what they demonstrably did rather than from their job titles, and naming at
least one they are **not** credible for every time. It elicits through oblique questions
(difficulty, causation, counterfactuals, what colleagues rely on you for) because direct
questions return the bullets already on the page. It maintains two files across sessions: a
durable `evidence-base.md` and a perishable, target-specific `action-ledger.md`.

**Reach for it when:** someone has *no target role yet* — they ask what they could
realistically go for, whether they're pigeonholed, why they get no callbacks, what they're
missing, or hand over a CV with no instruction at all ("does this look OK", "be honest with
me"). Also for a career change, a step up, or going freelance.

**Won't do:** rewrite or reformat the CV. It drafts the top third and stops. It never invents
a number or a scale — a claim that would be stronger with a figure the person doesn't have
becomes a *quantify* action, not an estimate — and every entry is tagged `confirmed`,
`approximate` or `unverified`, with unverified material barred from drafted prose unless the
uncertainty stays visible.

**Provenance and the reason it is separate.** It was built by a second agent that had no
knowledge of `cv-and-human`, then reviewed by a design council which ruled **keep separate,
do not merge**. The deciding evidence was empirical rather than architectural: in the bundled
evals, the *baseline* (no skill) answered "am I positioned right?" by restructuring the CV —
and in doing so invented a certification count and produced an umbrella date range that
silently absorbed a seven-month gap into a continuous engagement. Nobody invented an
achievement; **the reformatting itself manufactured claims the source could not support.**
That is the failure mode of transform-first tools when the evidence is thin, and it is what
this skill exists upstream of. Measured effect over three evals: 100% / 100% / 100% with the
skill against 40% / 36% / 90% without (one run per cell — no variance data, and the
benchmark's token figures are unusable because capture failed on four of six runs).

### Changed — the `cv-and-human` ↔ `cv-evidence-base` routing fork

Both descriptions were re-cut around one discriminator: **a named document operation**
(tailor, ATS-proof, parse-check, de-slop, rewrite a LinkedIn field) routes to `cv-and-human`;
**an open positioning question** with no target role routes to `cv-evidence-base`. Each skill
now names the other and says when to hand over.

**Measured before and after, and the result is worth recording honestly.** The pre-change
descriptions overlapped in the text — both claimed the bare-CV-no-instruction case outright —
and that looked like a live defect. It wasn't: the baseline arm scored **84/84** across 3 reps
on a 28-utterance labelled set, and the revised arm also scored **84/84**, with no regression
on the LinkedIn triggers shipped the previous day. The router was resolving the overlap
correctly on its own. The edits stand on clarity and on removing a latent ambiguity, **not**
on a measured failure — and the prediction that there was one was wrong.

`cv-and-human` also gained a Step 1 instruction to stop and redirect when a CV's material is
too thin to tailor, because tailoring thin material produces a well-optimised document
arguing a weaker case than the candidate could support — and that is where the temptation to
invent lives.

**Also:** `cv-evidence-base` ships a README, 17 contract tests, and eval assertions —
including four derived from the measured baseline failures, which generic "no fabricated
numbers" checks did not catch: invented counts of the CV's own contents, stripped hedges
(`~400` → `400`), and restructuring that merges date ranges over a gap.

**One defect found by testing and fixed before release.** The anti-fabrication rule governed
*invented* numbers but said nothing about numbers the skill produces **about the CV itself**.
Two independent runs described a Jul 2023 → Mar 2024 employment gap as "eight months" when
the blank months are August to February — seven; one also reported "fourteen lines of
technologies" for thirteen. These read as observations rather than claims, which is precisely
why they slip: nobody double-checks a figure they think they just read off the page. The rule
now says count it and be right, or hedge it visibly — and calls out gap arithmetic
specifically, since it is the number a screener is most likely to check, and a candidate who
repeats "eight-month gap" in an interview was handed that error by a tool whose whole promise
is that it doesn't do that.

**On the fixtures:** the technical eval fixture is a **fictional CV** (`alex-doyle-cv.md`).
It was originally a real one, which would have published a working email address and mobile
number to a public repo permanently. It is structurally faithful — the certification stack,
the AI-vs-platform positioning gap, the `~400` and `~35–40%` hedges, the Jul 2023–Mar 2024
gap, the orphan skills and the eight-year-stale management role are all preserved, because
those are exactly what the assertions grade. Only identity was changed.

---

## 2026-07-29

### Changed — `terragrunt-skill` brought up to Terragrunt v1.1.1

The skill was pinned to **v1.1.0** (2026-07-01) and is now current with
[**v1.1.1**](https://github.com/gruntwork-io/terragrunt/releases/tag/v1.1.1) (2026-07-14).

**What actually changed upstream:** v1.1.1 is a bug-fix release with **no new GA surface**. It adds
two opt-in **experiments**, both on the `terraform` block, and both now documented in
`references/hcl-blocks.md` with the same version-gating the skill already applies elsewhere:

- **`oci`** — module sources from OCI Distribution registries: `source = "oci://ghcr.io/acme/terraform-modules/vpc?tag=1.0.0"`
- **`version-attribute`** — a `version` constraint for `tfr://` registry modules, e.g. `version = "~> 3.3"`, instead of pinning the version inside the source URL

**A correction worth calling out.** `SKILL.md` previously implied only two experiments remained
active after v1.1.0. Ten were active as of v1.1.1, six of which this skill has never documented.
The skill now says so plainly and tells the agent that an unfamiliar `--experiment` value is *not*
evidence of an error — look it up instead of flagging it. The same incomplete list in
`references/scale-and-performance.md` was corrected.

**Also added:** `terragrunt-crash-*.log` panic reports (new in v1.1.1) at the top of
`references/error-patterns.md`, flagged as a Terragrunt crash rather than a config error, so it
isn't diagnosed against a catalogue that cannot explain it. And an explicit note that
`terraform.source` cannot reference `dependency` outputs — module sources must resolve before the
dependency graph runs. v1.1.1 only improved the *error message* for this, but it is a real
constraint that was previously undocumented here.

**Verification honesty.** The twelve other v1.1.1 bug fixes need no documentation change — the skill
never documented any of those behaviours as limitations, so there is nothing to retract. Reference
footers now distinguish what was **spot-checked against docs** at v1.1.0 from what was **reviewed
against the v1.1.1 release notes**, rather than claiming a full re-verification that did not happen.

---

## 2026-07-28 / 2026-07-29

### Added — `cv-and-human` gains a LinkedIn profile mode

**What:** the skill now handles a second career document: a LinkedIn profile, on a **job-seeker
lens** — headline, About, and skills, optimised for LinkedIn Recruiter search and the human scan.

**Reach for it when:** someone wants their LinkedIn profile optimised, a headline or About section
rewritten, asks why they aren't showing up in recruiter searches, or wants their profile to match
their CV. Plain CV/ATS work is unchanged and still the skill's core.

**Why it lives here rather than in a new skill:** LinkedIn Recruiter search *is* automated screening
over a career document, so the host skill's thesis carries over unchanged — lock down the knowable,
controllable surface, feed the noisy judgment layer true material, never promise a score.

**The one structural difference that shapes the whole mode:** a CV is tailored 1:1 to a job
description; a profile is one artifact read by many people. You cannot keyword-tailor to twelve roles
at once without producing soup, which is why positioning comes before keywords, and why target-role
keywords are allowed in skills, experience and the *tail* of About but are **barred from the headline
and the first ~200 characters** — the only parts most humans read.

**Won't do:** any LinkedIn engagement automation — connecting, posting, commenting, messaging,
following or applying. That is a deliberate line, not a gap: it protects a real account against ToS
enforcement. It also won't scrape or fetch linkedin.com, invent roles/metrics/skills/endorsements,
promise search ranking, or write LinkedIn *posts* (those go to `hook-and-human` for persuasive copy,
`clear-and-human` for neutral).

**New tooling:** `scripts/li_profile_check.py` — character counts, the "see more" fold check, keyword
coverage, per-skill length. It counts **UTF-16 code units**, matching the browser-side counter
LinkedIn actually uses, so an emoji costs two characters exactly as it does in the real field.
Getting this wrong in the obvious way (Python's `len()`) would report a headline as fitting when
LinkedIn will truncate it.

**Also:** `cv-and-human` predated the repo's conventions and now has a README, evals and tests.

### Changed — routing between the three writing skills

`cv-and-human`, `clear-and-human` and `hook-and-human` had their trigger descriptions edited
**together**, so "my LinkedIn profile" reaches the profile mode while "write a LinkedIn post" still
reaches the marketing skill.

**If you edit any of those three descriptions, treat them as measured artifacts.** Dropping
`clear-and-human`'s CV carve-out was measured to regress "my resume sounds AI-written" routing from
4/4 to 2/4. `cv-and-human/tests/test_skill_contract.py` guards the invariants in well under a second
with no API cost — run it before assuming an edit is safe.

### Added — `travel-planning`

**What:** turns a trip request into a day-by-day itinerary plus a reconciled budget, as an editable
Markdown document.

**Reach for it when:** someone wants a trip planned, paced and budgeted — even if they never say
"itinerary".

**Won't do:** make bookings, transact, or read live seat/room inventory. It will do a best-effort web
lookup to anchor costs in typical or seasonal prices, and those are **labelled as estimates, not live
quotes**. Booking is steered to the actual booking sites, with the honest note that no single site is
reliably cheapest.

### Added — `business-plan`

**What:** a full narrative business plan, a one-page summary, and a ~300-word investor pitch.

**Reach for it when:** someone wants to plan, pitch or pressure-test a venture — size a market, tear
down competitors, build a go-to-market, produce investor-facing financials.

**Its defining feature is honesty.** It researches and cites market and competitor facts, computes
financials from *your* assumptions via a deterministic projector (`scripts/financials.py`), and marks
anything unknown as an explicit validate-this placeholder. It **never invents a market size, a
competitor's price, or a revenue number**, and it ends with a straight go / no-go / reshape verdict
rather than encouragement.

### Added — `nano-banana-pro-json` gains three creation modes

Beyond its photographic core, the image skill now carries recipes for:

- **Logos and brand identity** — brand brief → flat-vector prompt, then a **free local raster→SVG
  trace** of the winning concept (the step commercial logo generators charge for). Won't do trademark
  clearance or font-licence checks, and text in generated marks can be imperfect — verify any wordmark
  before shipping.
- **Product and marketing images** — e-commerce specs, identity-lock for a real product, consistent
  shot sets. Won't fabricate prices, claims or label text, and can subtly alter a real product's
  details, so verify against reality.
- **Infographics and diagrams** — layout and style vocabulary, labels supplied verbatim. It renders
  the *look* of an infographic, not trustworthy data: it garbles text and **invents numbers**. Supply
  the facts and verify them; for real data visualisation use `report-builder`.

Also added `4:5` and `3:4` aspect ratios, which the product and infographic recipes need.

### Added — the per-skill README convention

Every skill now carries a README covering **what it does / how to use it well / what it does NOT do**,
linking back to the repo README. The "does NOT do" section is the load-bearing one — it is what stops
a skill being reached for in situations it will handle badly. Documented in `CONTRIBUTING.md`.

---

## 2026-07-08

### Changed — `excalidraw-diagram` no longer ships its render engine

The 2.9 MB `excalidraw.mjs` bundle is no longer committed. It is fetched once from a pinned GitHub
Release on first render and verified against a recorded sha256, so the repo stays small and the
engine version stays pinned and tamper-evident.

### Added — `excalidraw-diagram` cloud icon-library ingestion

Ingests named vector icon libraries (AWS, Azure) with deterministic placement, so diagrams use real
provider iconography rather than approximations.
