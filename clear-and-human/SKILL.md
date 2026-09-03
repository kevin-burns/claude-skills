---
name: clear-and-human
description: >
  Construct, review, score, and rewrite written content so it reads like a specific human wrote it, not an AI. Use this skill whenever the user wants to: write or draft prose for humans (docs, README, runbook, ADR, PR/commit message, blog post, LinkedIn post, email, Slack message, or a spoken explainer/tutorial video script); humanize or de-slop AI-generated text; check whether writing "sounds like AI"; review a draft for AI texture; rewrite content in their own voice; score a draft for authenticity or clarity; or tighten and sharpen prose. Also trigger on "humanize", "make it sound human", "sounds like AI", "does this sound like AI", "voice check", "review my draft", "rewrite in my voice", "tighten this up", "edit for clarity", "video script", "explainer script". Auto-detects content type and applies channel-specific rules. Defaults to a neutral, factual voice and never invents specifics to add texture. For deliberately persuasive marketing copy (ads, hooks, LinkedIn/Bluesky growth posts, video titles and thumbnails) use hook-and-human instead. For a CV/resume or a LinkedIn PROFILE - including de-slopping or humanizing one, or rewriting a headline, About section or experience bullets - use cv-and-human instead.
license: MIT
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion
---

# Clear and Human

A writing skill in three layers: **construct** good prose (Strunk), **detect/score/report** AI texture (channel-aware review), and **restore** a human voice (de-slop + voice match + self-audit). Use one layer or all three depending on what the user hands you.

## Pick the mode first

- **Generate** — user wants new prose ("write a runbook for X"). Run Construct, then Restore, then a light self-audit. Skip scoring unless asked.
- **Review** — user pastes a draft and wants feedback ("does this sound like AI?"). Run Detect → Score → Report. Offer a rewrite.
- **Rewrite** — user pastes a draft and wants it fixed ("humanize this"). Run Detect → Rewrite → Self-audit. Show the report only if useful.

If unclear, default to **Review** and offer the rewrite at the end.

## Core rules (all modes, non-negotiable)

1. **Never invent specifics to add texture.** No fabricated numbers, names, quotes, dates, or citations. If a draft is vague and a concrete example would help, flag it and leave a `[ADD SPECIFIC EXAMPLE]` placeholder. Sounding human never outranks being correct — this matters most in technical docs.

   **A specific does not have to contain a digit.** A graded eval found both generate-mode failures were numberless, which is why they got past every check. Treat all of these as fabrication:
   - **A claim about state.** "Test coverage stayed the same" — invented, in a post whose context file approved exactly one fact.
   - **A file path, directory or filename.** `/etc/nginx/ssl/` is not an nginx, Debian or certbot default. It was put in a rollback command, where following it verbatim mid-outage restores nothing.
   - **An authorial stance.** "I've watched this approach turn into growth that holds up" — an eyewitness claim, published under the user's name, invented to add warmth.
   - **A measurement of the text you are reviewing.** Two reviews stated a word count and a sentence-length range that were both wrong. Count it with `scripts/register_report.py`, quote the figure it prints, or say nothing.

   **Placeholders are all-or-nothing.** If any environment-specific value is bracketed, bracket every one. Half-marking is worse than none: a bracketed `<domain>` beside a bare path tells the reader the path is real.
2. **Preserve meaning.** Change delivery, not substance. Never add or drop an argument during a rewrite. The trap is that several style rules remove information while appearing to remove only shape: cut the boldface off *"the **single most important** build"* and the ranking goes with it; tidy *"it is simultaneously A, B and C"* into a clean rule of three and the claim that they hold at once goes with it. The CLAIM WORDS section of `scripts/fidelity_check.py` lists the ranking, scope, comparison and requirement words a rewrite dropped, so this rule has something behind it other than your own attestation.
3. **Match the intended voice**, not a generic "good writing" voice. Use the user's sample if provided (see Voice calibration). Absent a sample, default to neutral-factual, not marketing-operator.

   **An unidiomatic construction is not therefore wrong, and it is never an AI tell.** This skill refuses AI-detector scores partly because Liang et al. measured a 61.22% false-positive rate against non-native English writers — and then, until this rule existed, handed Layer 3 a set of rewrite defaults that would quietly edit a non-native writer toward native idiom. The detection question was guarded and the *rewrite* question was not.

   Measured on a real corpus, 12 pieces and 12,425 words by a confirmed non-native writer: *"Calgary-born, Vancouver located musician"*, *"her voice … but need in no way hide"*, *"It is your livingroom dolling up as a venue"*. Regressed to "Vancouver-based", "doesn't need to hide", these become ordinary blog English and nobody's voice in particular. **Flag such a construction as a question for the author — "is 'Vancouver located' deliberate?" — never as a fix to apply.** Same posture the pattern list already takes: a reason to look, not a verdict.

   The caveat travels with the finding: **n=1 author.** Strong enough to change how the skill behaves, not strong enough to state as a norm about non-native writers, and "median 2.9" is not a target.
4. **The portability test.** If a sentence could move unchanged to another person, company, country or product, it is probably filler. Cut it, or replace it with a fact, example, mechanism, consequence or judgement specific to this subject. This is the mechanism behind several rules stated separately below, which is why it is worth naming once on its own.
5. **Clean is not enough.** Text with zero AI tells but no opinion, no specifics, and uniform rhythm is still slop. Flag "clean but hollow" explicitly.

## Voice calibration (optional but improves everything)

**First, look for a persistent context file.** Check the project root for `WRITING_CONTEXT.md`, and if absent, `FOUNDER_CONTEXT.md` (the convention used by founder-skills, so one file serves both skill sets). If found, read it and pull: brand/personal voice, audience/ICP, the offer, real case studies and numbers you're allowed to cite, and the list of phrases the user never uses. Use these instead of asking.

If no context file exists and the task isn't trivially short, ask for 1–3 paragraphs of the user's own writing plus, if they'll share it: how they open, sentence-length tendency, prose vs lists, how they close, and phrases they never use. Offer to save the answers as `WRITING_CONTEXT.md` so the next run skips the questions. Then mirror *their* patterns in the rewrite — don't just strip AI patterns and leave a void. If no sample is offered, run the full pipeline anyway and note that calibration would sharpen the result.

The context file supplies the approved facts; it does **not** relax core rule 1. Anything not in the file or the draft is still off-limits to invent.

---

## Layer 1 — Construct (generate mode)

Apply Strunk's constructive rules while drafting. Full detail in `references/elements-of-style.md`; the load-bearing ones:

- Use the active voice.
- Put statements in positive form (assert; avoid "not un-").
- Use definite, specific, concrete language.
- Omit needless words.
- Keep related words together; put the emphatic word at the end of the sentence.
- One topic per paragraph, led by a topic sentence.

For the **technical** voice (default for docs): explain mechanics, show how it works, name the tradeoff, reduce the reader's uncertainty. Calm and specific beats punchy and vague.

---

## Layer 2 — Detect, score, report (review mode)

### Step A — Detect content type, then ask the stance

Classify as one of: **docs** (README, runbook, ADR, PR/commit, API reference, technical explanation), **blog**, **youtube-script** (spoken explainer/tutorial narration), **linkedin**, **email**, **slack**. Detection cues and per-channel rules live in `references/channels.md`. State the detected type at the top of the report. If ambiguous, default to **docs** for technical input and **blog** otherwise, and say so.

**If the audience or format is unclear, ask one question: who is this for, and where will it be published?** That is a different question from the stance one below and they are complementary — audience decides what can be assumed, stance decides who is speaking.

Channel is not the whole story: a personal account and a product write-up can be the same channel and want opposite stances. Ask which one this is, or take it from `WRITING_CONTEXT.md` — never infer it, because a stiff impersonal draft and a correct impersonal draft look identical on person density. See the Stance section of `references/channels.md`. Person is context; stiffness is what you flag.

### Step B — Scan for AI patterns

Apply the universal pattern list in `references/ai-patterns.md` to all content, then the channel-specific markers from `references/channels.md`. Flag every instance with the exact quote and a concrete fix. Don't paraphrase the flag — quote what's actually there.

Optionally run `scripts/register_report.py <draft>` to get measured rates for the stiffness features instead of judging them by eye — it prints the citation behind each one and no verdict. Useful when a draft reads as formal but you can't say which feature is doing it.

### Step C — Score (1–10, four dimensions)

AI-Likeness is always present (lower is better, target 1–3). The other three vary by channel:

| Channel | Dim 2 | Dim 3 | Dim 4 |
|---|---|---|---|
| docs | Clarity | Accuracy / Verifiability | Actionability |
| youtube-script | Clarity | Accuracy / Verifiability | Authenticity |
| blog / linkedin | Authenticity | Reader Value | Domain Credibility |
| email | Authenticity | Clarity | Appropriate Tone |
| slack | Naturalness | Clarity | Brevity |

Targets for dims 2–4 are 7–10 (8–10 for short formats). One-line justification per score. If AI-Likeness is low but Dim 3/4 is also low, call it out: clean but hollow.

### Step D — Report

```
## [Content Type] Review
**Detected as:** [type]

### Overall
[2–3 sentences: biggest strength, biggest issue]

### Scores
| Dimension | Score | Note |
|---|---|---|
| AI-Likeness | X/10 | ... |
| [Dim 2] | X/10 | ... |
| [Dim 3] | X/10 | ... |
| [Dim 4] | X/10 | ... |

### Flags
[Each flagged phrase/structure: exact quote → suggested fix]

### Top 3 changes
1. ...
2. ...
3. ...
```

---

## Layer 3 — Rewrite and restore (rewrite mode)

1. Replace every flagged pattern with natural language (see `references/ai-patterns.md` for before/after).
2. Vary sentence rhythm — short lines mixed with longer ones. Uneven length reads as human; treat it as one signal among several, not a ranking (see `references/ai-patterns.md`, which records that the "loudest tell" claim had no source).
3. Use simple constructions (is/are/has) instead of "serves as / stands as / boasts".
4. Cut decorative emoji, mechanical boldface, and title-case headings. **Em-dashes and curly quotes are not on this list** — they are author-relative and model-specific, and `references/ai-patterns.md` holds the current rule with its evidence. Follow the reference, not a blanket cut. A graded eval caught this file and that one giving opposite instructions, and the reference was the better-reasoned of the two.
5. **Add voice, carefully.** Opinions, mild uncertainty, first person where it fits, the occasional aside. In `technical` mode keep this conservative — a runbook doesn't need a personality, it needs to be right and unambiguous.
6. **Restore contractions the draft expanded — but only where the author's own rate says there is something to restore.** "Restore" presumes a prior state. In the measured corpus above the author's median is **2.9 per 1000 words, band 0.0–5.6, with one published piece at exactly 0.0**; running this step on her produces contractions that were never there and makes her less like herself. With `scripts/register_report.py --baseline <dir>` the question is checkable instead of assumed. Without a baseline, ask before expanding the rate rather than treating expansion as the default. See the expanded-contractions entry in `references/ai-patterns.md`.
7. Apply the channel rewrite rules from `references/channels.md`.
8. Honor the no-invention rule: if texture requires a fact you don't have, leave a placeholder.

### Self-audit (the blader pass — run before presenting the final rewrite)

1. Ask yourself: "What still makes this read as AI-generated?" Answer in 2–4 honest bullets (rhythm too even? placeholder-ish specifics? slogan-y closer?).
2. Then revise once more to fix exactly those tells. **A revised version must follow the audit.** If the audit names nothing worth fixing, say that explicitly — but an audit that ends the output is not a self-audit, it is a postscript.
3. Run `scripts/fidelity_check.py <original> <rewrite>`. It reports any number, quote, URL or code span that appeared, vanished or changed. A number present in the rewrite but not the original is a fabrication.
4. Read the **CLAIM WORDS** section of that report before presenting anything. It lists the ranking, scope, comparison and requirement words the rewrite dropped or added — the loss that looks like style. A superlative that ranked its subject against everything else in the document, a "simultaneously" that said three things hold at once rather than in turn, a "must" softened to "should": each leaves with the shape it was carried in. **The script does not judge these; you have to.** For every row, go to the sentence it quotes and decide whether the claim survives without the word. If it doesn't, put the word back. Say which rows you checked and what you concluded — a row you did not open is a row you did not check.
5. **Run `scripts/register_report.py <rewrite> --against <original>`** and read the REGISTER DRIFT section. `fidelity_check.py` catches a rewrite that invented a **fact**; this catches one that invented a **register**, which nothing else here does. Movement is not a defect — the rewrite was supposed to change the text. What you are looking for is movement you did not intend, and with `--baseline` a row marked **AWAY** means the rewrite ended up further from the author's own rate than the original was. Report what it says; it sets no threshold and returns no verdict.
6. **Answer `references/self-check.md` item by item, by number.** Twenty-four pass/fail questions grouped as fidelity, voice, patterns and substance. It is deliberately more mechanical than the prose audit in step 1: a paragraph asking you to reflect is easy to narrate past, and the graded set shows that happening — six of ten outputs narrated running `fidelity_check.py` and one pasted its output. **The checklist is judgement and the script is measurement; neither substitutes for the other.**
7. Present the final version. Optionally list the changes made.

**Never certify what you did not check.** This is the rule the eval caught being broken, and it is the most damaging failure in the set because the reader trusts this line specifically. Two constraints:

- **Do not claim to have run a script unless you ran it and are pasting its real output.** Six of ten graded outputs narrated running `fidelity_check.py`; one pasted anything. A narrated check is worse than no check, because it reads as verification.
- **Do not assert that nothing was invented.** Say what you checked and how. "No number in the rewrite is absent from the original — fidelity_check reports 0 appeared" is a claim you can stand behind. "Nothing was invented" is not, and one output made exactly that claim in the same breath as inventing a metric about the user's CI pipeline.

`fidelity_check.py` will tell you when it cannot help: on text with no numbers, quotes, URLs or code spans it prints **NOTHING TO CHECK** rather than a clean result, because a pass over an empty set is not evidence. When you see that, the claims have to be verified by reading, and the audit must say so. The same warning appears as a footer under a report built only from claim words — those catch the claim that ranks or scopes something, and nothing at all about the claim that doesn't.

---

## After a review or rewrite: candidate patterns (optional, off by default)

Do **not** edit this skill's own files. If you noticed a recurring AI tell that isn't in `references/ai-patterns.md`, surface it to the user as a suggestion with a concrete example, and let them decide whether to add it. This replaces the self-rewriting loop from the original the-humanizer skill, which bloated the file and broke on read-only installs.

## Closing note to give the user

The rewrite is a starting point. Their own edits on top of it are usually the best version — the goal is to get fast at recognizing their own voice, so review becomes a quick confirmation rather than a rescue.

---

## Deliberately excluded

Deliberately excluded, and it matters that they are: any AI-detector score (Liang et al.,
*Patterns* 4(7):100779, measured a 61.22% false-positive rate against non-native English
writers across seven detectors), burstiness (no grounding found; GPTZero dropped it in
autumn 2023), and readability indices (validated on schoolchildren and Navy trainees, not on
whether prose sounds like a person). This skill is not a detector and not a grammar checker.
