---
name: clear-and-human
description: >
  Construct, review, score, and rewrite written content so it reads like a specific human wrote it, not an AI. Use this skill whenever the user wants to: write or draft prose for humans (docs, README, runbook, ADR, PR/commit message, blog post, LinkedIn post, email, Slack message, or a spoken explainer/tutorial video script); humanize or de-slop AI-generated text; check whether writing "sounds like AI"; review a draft for AI texture; rewrite content in their own voice; score a draft for authenticity or clarity; or tighten and sharpen prose. Also trigger on "humanize", "make it sound human", "sounds like AI", "does this sound like AI", "voice check", "review my draft", "rewrite in my voice", "tighten this up", "edit for clarity", "video script", "explainer script". Auto-detects content type and applies channel-specific rules. Defaults to a neutral, factual voice and never invents specifics to add texture. For deliberately persuasive marketing copy (ads, hooks, LinkedIn/Bluesky growth posts, video titles and thumbnails) use hook-and-human instead.
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
2. **Preserve meaning.** Change delivery, not substance. Never add or drop an argument during a rewrite.
3. **Match the intended voice**, not a generic "good writing" voice. Use the user's sample if provided (see Voice calibration). Absent a sample, default to neutral-factual, not marketing-operator.
4. **Clean is not enough.** Text with zero AI tells but no opinion, no specifics, and uniform rhythm is still slop. Flag "clean but hollow" explicitly.

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

### Step A — Detect content type

Classify as one of: **docs** (README, runbook, ADR, PR/commit, API reference, technical explanation), **blog**, **youtube-script** (spoken explainer/tutorial narration), **linkedin**, **email**, **slack**. Detection cues and per-channel rules live in `references/channels.md`. State the detected type at the top of the report. If ambiguous, default to **docs** for technical input and **blog** otherwise, and say so.

### Step B — Scan for AI patterns

Apply the universal pattern list in `references/ai-patterns.md` to all content, then the channel-specific markers from `references/channels.md`. Flag every instance with the exact quote and a concrete fix. Don't paraphrase the flag — quote what's actually there.

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
2. Vary sentence rhythm — short lines mixed with longer ones. Uniform length is the loudest AI tell.
3. Use simple constructions (is/are/has) instead of "serves as / stands as / boasts".
4. Cut em-dashes, decorative emoji, mechanical boldface, curly quotes, title-case headings.
5. **Add voice, carefully.** Opinions, mild uncertainty, first person where it fits, the occasional aside. In `technical` mode keep this conservative — a runbook doesn't need a personality, it needs to be right and unambiguous.
6. Apply the channel rewrite rules from `references/channels.md`.
7. Honor the no-invention rule: if texture requires a fact you don't have, leave a placeholder.

### Self-audit (the blader pass — run before presenting the final rewrite)

1. Ask yourself: "What still makes this read as AI-generated?" Answer in 2–4 honest bullets (rhythm too even? placeholder-ish specifics? slogan-y closer?).
2. Then revise once more to fix exactly those tells.
3. Present the final version. Optionally list the changes made.

---

## After a review or rewrite: candidate patterns (optional, off by default)

Do **not** edit this skill's own files. If you noticed a recurring AI tell that isn't in `references/ai-patterns.md`, surface it to the user as a suggestion with a concrete example, and let them decide whether to add it. This replaces the self-rewriting loop from the original the-humanizer skill, which bloated the file and broke on read-only installs.

## Closing note to give the user

The rewrite is a starting point. Their own edits on top of it are usually the best version — the goal is to get fast at recognizing their own voice, so review becomes a quick confirmation rather than a rescue.

---

## Provenance

Merged and adapted (all MIT / public domain):
- `the-humanizer.md` — channel detection, scoring rubric, structured report (user-supplied from reddit).
- `blader/humanizer` (MIT) — soul/voice section and the self-audit loop.
- `softaworks/agent-toolkit/writing-clearly-and-concisely` (MIT; orig. @joshuadavidthomas) — Strunk layer.
- *The Elements of Style*, Strunk 1918 (public domain).
- `ognjengt/founder-skills` (MIT) — the shared-context-file pattern (`FOUNDER_CONTEXT.md`), adopted here as `WRITING_CONTEXT.md`.