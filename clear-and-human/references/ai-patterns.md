# AI patterns (universal) — detect and fix

The deduped master list, merged from Wikipedia's "Signs of AI writing", blader/humanizer, and the-humanizer. Apply to every content type; add channel markers from `channels.md` on top. Flag with the exact quote and a concrete fix.

## How to read this list

The source these patterns mostly descend from states its own status plainly, and the
distinction did not survive into the versions this file was built from. Wikipedia's
"Signs of AI writing": *"this list is descriptive, not prescriptive; it consists of
observations, not rules"*, and *"The patterns listed here are also only potential signs
of a problem, not the problem itself."*

So a match here is **a reason to look, not a verdict**. Three consequences that change
how you use it:

- **Quote the hit, then decide.** A human writer can use any item on this list correctly.
  Flag it, say why it reads as a tell in this draft, and let the writer overrule you.
- **A single match proves nothing.** These are weak signals that mean something in
  combination and very little alone. Never build a conclusion on one.
- **The patterns decay.** They track what particular models did at a particular time, and
  models change. "Delve" was overused by ChatGPT in 2023 and early 2024 and dropped off
  sharply in 2025. Treat an unmatched pattern as uninformative rather than as evidence of
  a human, and treat the list as perishable stock rather than a fixed asset.

**Last reviewed against the upstream source: 2026-08-13.** That page is edited almost
daily, so this file drifts from it continuously. Items below that were checked against it
on that date are noted; the rest are inherited and unverified.

## Phrase-level

**AI vocabulary (cut or replace with the specific thing):**
delve, leverage (verb), harness, navigate (figurative), utilize, foster, cultivate, facilitate, streamline, optimize, unlock, empower, elevate, enhance, garner, showcase, underscore (verb), highlight (verb), align with, transformative, groundbreaking, seamless, robust, holistic, dynamic, agile, synergy, scalable, disruptive, paradigm, landscape (abstract), realm, tapestry (abstract), multifaceted, nuanced, comprehensive, intricate, crucial, vital, pivotal, essential, key (adj), enduring, vibrant, testament, interplay, showcasing, intricacies, meticulous, meticulously, unparalleled, albeit, whilst, essentially, certainly, absolutely (opener), overall (filler), typically, various (vague pluralizer), actually, additionally.

> **Which of these have evidence, and which are inherited.** Checked 2026-08-13 against
> Kobak, D., González-Márquez, R., Horvát, E-Á., & Lause, J. (2025), "Delving into
> LLM-assisted writing in biomedical publications through excess vocabulary",
> *Science Advances* 11(27), eadt3813, DOI 10.1126/sciadv.adt3813. Their method is
> excess-frequency: extrapolate a word's 2021–22 trend, measure the gap, over 15
> million-plus PubMed abstracts. The resulting 900 words, annotated `style` vs `content`,
> are published at **github.com/berenslab/llm-excess-vocab** (`results/excess_words.csv`,
> MIT). 407 are style words, 268 of them verbs.
>
> **32 of the 61 words above appear in that style set:** delve, leverage, harness, utilize, foster, facilitate, streamline, unlock, empower, elevate, enhance, garner, showcase, underscore, highlight, align with, transformative, groundbreaking, seamless, realm, multifaceted, nuanced, comprehensive, intricate, crucial, pivotal, essential, enduring, interplay, typically, various, additionally.
>
> **29 do not:** navigate, cultivate, optimize, robust, holistic, dynamic, agile, synergy, scalable, disruptive, paradigm, landscape, tapestry, vital, key, vibrant, testament, showcasing, intricacies, meticulous, meticulously, unparalleled, albeit, whilst, essentially, certainly, absolutely, overall, actually. That is not proof they are wrong — the
> corpus is biomedical abstracts, so tech-register words like *synergy*, *scalable*, *agile*
> and *paradigm* would not surface there whatever their LLM overuse. It is the honest
> partition: two-thirds sourced, one-third inherited from intermediaries with nothing behind
> it. Weight a hit accordingly. The five added 2026-08-16 — *showcasing, intricacies,
> meticulous, meticulously, unparalleled* — are in the unsourced group by construction: they
> were taken from `delete-ai-words` only because each is a morphological sibling of a word
> that IS in the Kobak set (*showcase, intricate*), which is a weaker warrant than the study
> itself and is not the same thing as evidence.
>
> **We deliberately do not import the other 407.** They describe excess vocabulary in
> academic abstracts, and pulling them in wholesale would drag that register into blog and
> product writing. Cite the dataset when a word needs backing; do not mirror it. It is
> maintained upstream — the repo carries a July 2025 recompute at monthly resolution — and a
> copy here goes stale.

**Filler openers / hedges:** "In today's [noun]", "In the ever-evolving landscape", "When it comes to", "At the end of the day", "It's worth noting that", "It's important to note that", "One might argue", "It goes without saying", "The truth is", "Here's a breakdown", "Below is/Below:" before a list. Cut and start with the substance.

> **Two of these are dated.** Checked 2026-08-13: Wikipedia now files "It's important to
> note that" and its didactic-disclaimer relatives under **Historical indicators
> (November 2022–2024)** — *"common in text generated by older AI models, but much less
> frequent in newer models"*. Still worth cutting as filler; much weaker as evidence of
> machine origin than the rest of this line.

**Significance inflation:** "stands/serves as", "is a testament to", "marks a pivotal/crucial moment", "underscores its importance", "reflects a broader", "setting the stage for", "a key turning point". State what actually happened instead.
- Before: "Established in 1989, marking a pivotal moment in the evolution of regional statistics."
- After: "Established in 1989 to publish regional statistics independently of the national office."

**Vague attributions / weasel words:** "Industry observers note", "Experts argue", "Studies show", "Some critics say" with no named source. Name the source or drop the claim.

**Copula avoidance:** "serves as / functions as / stands as / boasts / features a". Use is/are/has.
- Before: "Gallery 825 serves as the exhibition space and boasts 3,000 sq ft."
- After: "Gallery 825 is the exhibition space and has 3,000 sq ft."

**Superficial "-ing" tails:** "...ensuring reliability", "...highlighting its significance", "...reflecting the community's connection". These bolt fake depth onto a sentence. Cut or turn into a real clause.

**Persuasive-authority tropes:** "The real question is", "At its core", "What really matters", "Fundamentally", "The deeper issue". Usually precede an ordinary point dressed up. Just make the point.

**Wordy hedging — a tightening edit, NOT an AI tell.** "could potentially possibly" → "may affect"; "might have some effect" → say which effect. Also: "arguably", "to some extent", "broadly speaking", "generally speaking". Either commit to the claim or name the actual limit.

> **The evidence runs the other way, so do not count these toward AI-likeness.** Corrected 2026-08-13. Three independent sources put hedges on the HUMAN side. Jiang & Hyland (2025, *English for Specific Purposes* 79) found ChatGPT essays show *"a significantly lower frequency of interactional metadiscourse, such as hedges, boosters, and attitude markers, leading to a more impersonal and expository tone"*. Mizumoto, Yasuda & Tamura (2024, *Applied Corpus Linguistics* 4(3)) found *"human-written essays exhibited higher usage of modals, epistemic markers, and discourse markers"*. Wikipedia's "Signs of AI writing" lists simple hedges (*very, perhaps, tends to*) under signs of human writing.
>
> Against that: one vendor blog — Grammarly's common-AI-words page, from a company selling both an AI Detector and an AI Humanizer — which is where the four phrases above came from, and which appears to have the direction wrong. They are kept because they are still wordy, and because "omit needless words" needs no evidence about machines. Belongs with the filler-to-tight rewrites below, for the same reason.

**Filler-to-tight rewrites:** "in order to" → "to"; "due to the fact that" → "because"; "at this point in time" → "now"; "has the ability to" → "can"; "in the event that" → "if".

> **Tighten these as a Strunk edit, not as an AI tell.** Checked 2026-08-13: Wikipedia's "Signs of AI writing" lists *"as a result of, in order to, all of the, a part of, or the fact that"* under signs of **human** writing, reporting them as *"empirically observed, over 25 years of Wikipedia writing, to be more common in Wikipedia articles written by humans than in AI-generated text"*. So the direction of evidence is against reading these as machine output. They are still wordy, and "omit needless words" stands on its own authority (`elements-of-style.md`) — but do not cite them as evidence a draft was AI-written, and do not count them toward an AI-likeness score. The same source lists simple hedges (*very, perhaps, tends to*) as human tells too, which sits awkwardly beside the excessive-hedging entry below.

## Structural

- **Generic opening** instead of a specific story, datapoint, or claim.
- **Uniform paragraph/sentence length.** Vary it. Note the demotion: this was
  previously called "the loudest tell", and that ranking had no source. Checked
  2026-08-13 — Wikipedia's guide does not discuss sentence-length uniformity or
  burstiness anywhere ("burst", "uniform", "monoton", "sentence length",
  "paragraph length" all return zero hits across the full page), so it backs the
  claim neither way. The related idea of scoring burstiness is separately
  rejected in `SKILL.md`; no grounding was found for it and GPTZero dropped it in
  autumn 2023. Reading unevenness as a good sign is fine. Ranking it above every
  other item here was not.
- **Intro → 3-point list → summary** template; the **rule of three** forced everywhere ("innovation, inspiration, insight").
- **Stacked fragment cadence** as punchlines: "X. Y. Z." → write a real sentence.
- **Negative parallelism / the reframe.** Rejecting one frame and replacing it with another to
  manufacture depth. Expanded 2026-08-16 from a single line naming two shapes; the taxonomy is
  inherited and unverified, like the analogy section below, but the pattern is easy to check
  by eye and the one-liner caught only the most obvious form.

  A passage fails if it (1) dismisses, minimises or questions X, then (2) upgrades to Y —
  **even when the word "not" never appears.**

  *Shapes:* "This isn't X, it's Y" · "Not X. Y." · "Forget X, focus on Y" · "Less X, more Y" ·
  "Not only X but also Y" · "X? No. Y." · "Stop thinking X, start thinking Y" · "X is dead,
  Y is the future" · "The question isn't X, it's Y" · "You don't need X, you need Y" ·
  "It was never about X, it was always about Y".

  *Softened forms doing the same work:* "While X may seem…", "Although X appears…",
  "At first glance…", "On the surface…", "Most people think X…", "Conventional wisdom says X…".
  Watch the pivot: *but, yet, actually, really, instead, rather, ultimately, in reality, the
  truth is, what matters is, the real, the deeper, the hidden, the overlooked.*

  **It crosses sentence boundaries**, which the old one-liner missed entirely:
  - Before: "Most teams think they have a hiring problem. They have a standards problem."
  - After: "The team's standards are unclear."

  Headings too — "Not a tool. A system." / "The real problem" → name the thing directly.

  **Fix:** delete the rejected half, then write the positive claim as a plain sentence.
  "It's not about the prompt, it's about the context." → "Context controls the output."

  **Allowed, and this exception is what makes the rule usable:** contrast that corrects a
  specific factual, legal, technical, date, number, name or scope error. "The meeting is on
  Tuesday, not Thursday." Never contrast for drama or manufactured insight.
- **Tailing negation:** "...no guessing", "...no wasted motion" tacked on. → real clause.
- **False ranges:** "from the Big Bang to dark matter, from birth to death of stars" where endpoints aren't a real scale. → name the actual items.
- **Elegant variation** (synonym cycling): protagonist → main character → central figure → hero, all for one subject. Pick one.
- **Summary closing** that restates the piece; **generic upbeat conclusion** ("the future looks bright"). → end on a concrete next step, a real claim, or an open question. *Dated:* Wikipedia files "In summary" / "In conclusion" closings under Historical indicators (Nov 2022–2024), tied to older long-form generation. Cut them as flab; stop treating them as a tell.
- **Fake-profound kicker:** the final "deep" line that turns the point into a cute metaphor,
  an aphorism or a mic-drop. **This is a different failure from Summary closing above, and
  covering one does not cover the other** — a recap restates what the reader just read; a
  kicker adds a *new*, empty, quotable sentence that was never argued for.

  **The instruction matters more than the label, because it forbids the obvious wrong fix.**
  Do not rewrite it into a better metaphor. Do not preserve the rhythm. Delete it, then end on
  the clearest concrete sentence already in the draft. If the ending genuinely needs closure,
  add a plain takeaway or a next action. Added 2026-09-03 from `no-ai-slop` (MIT, petergyang).
- **Fragmented header:** a heading followed by a one-line restatement of the heading. Delete the restatement.
- **Colon reveals:** a noun phrase, a colon, then a lowercase dramatic reveal. "The detail that
  makes it work: a separate agent grades it." / "The best part: it learns." The colon is doing
  the job of a drum roll, and the sentence after it is usually ordinary. Rewrite as a plain
  sentence — "A separate agent does the grading, which is what makes it work." Reserve colons
  for lists, labels and quotes. Prefer sentence case after one unless grammar, a proper noun,
  a title or code requires otherwise.

  Distinct from **Fragmented header** above and **Signposting** below, which is why it was
  missed: a fragmented header restates a heading, signposting announces what is coming, and
  this stages a reveal in a single sentence. Added 2026-09-03 from `no-ai-slop` (MIT,
  petergyang), which names it and which we had no equivalent for.
- **Signposting:** "Let's dive in", "Here's what you need to know", "Now let's look at". Do the thing instead of announcing it.
- **Evidence-rating asides:** "which is the part I didn't expect", "and that's the interesting bit", "works better than you'd expect", "which is where it gets strange". Signposting facing backwards — instead of announcing what is coming, these rate what just arrived, telling the reader how to feel about evidence rather than presenting it. Cut the aside and let the fact land; if it does not land without the label, the label is not what is missing. Two notes on how to fix them: the hedged-comparative form ("works better than you'd expect on X") usually also splits the verb from its complement, so the repair is word order rather than vocabulary — a thesaurus will not help. And check the author's own corpus before flagging: a writer who genuinely uses these is not doing anything wrong, which is the standing rule for everything on this page.
- **Reading-complexity creep:** 3+ three-syllable words or 2+ nested clauses in one sentence. Shorten.
- **Expanded contractions:** spelling out "do not / is not / cannot" through an otherwise casual draft is a surface formalizing move, not a change of register. The rest of the sentence can stay just as warm. Contractions carry the highest loading (.90) of any single feature on Biber's (1988) involved/informational dimension, ahead of second-person pronouns and negation. Pavlick & Tetreault (2016) found contraction expansion in 16% of the edits annotators made when asked to sound more formal.

  A long draft with short words and casual asides but zero contractions is **worth asking about** — not a finding on its own. Two qualifiers, because without them the observation is falsifiable by ordinary human writing:

  **Length carries the whole signal.** Contraction opportunities scale with the draft, so zero means nothing in a short one. At 11 per 1,000 words — the low end of one author's eight-document sample — a 300-word post expects about three and a 1,800-word post expects twenty. Roughly **800 words is the floor** below which this is too weak to raise at all.

  **Compare against the author's rate for that channel, not a global range.** Fifteen documents from one author's 2008–2012 product blog average **3.7** contractions per 1,000 words against **11–29** for the same author's technical blog — and **6 of the 15 sit at exactly zero**, every one written a decade before any LLM existed. Same person, same measure, one fifth the rate, because it is a different job. `scripts/register_report.py --baseline <dir>` makes that comparison against the author's own corpus.
- Before: "It is not something we would recommend, and we cannot support it in production."
- After: "It's not something we'd recommend, and we can't support it in production."

## Analogy and metaphor

> **Inherited and unverified**, and flagged as such because the rest of this file partitions
> its claims. Adapted 2026-08-16 from a widely circulated anti-AI-writing skill
> (`delete-ai-words`) that cites nothing. Nothing below is sourced to a study; it is one
> writer's taste, and the frequency budget in particular is a number somebody chose. It earns
> a place because reaching for a metaphor to explain an ordinary idea is a recognisable habit
> and this file previously said nothing about it at all — not under-specified, absent. Treat
> every item as a reason to look, per the rules at the top.

**The default is no analogy.** Do not explain an ordinary idea through metaphor, and do not
decorate a clear point with imagery.

**Permission test — an analogy is allowed only if all five pass.** The subject is genuinely
unfamiliar, abstract or technical; the analogy makes it *easier*; it is **shorter** than the
literal version; it is exact enough not to mislead; and it reads normally aloud. If any fail,
write it literally. The "shorter" test does most of the work: an analogy that costs more words
than the plain statement is decoration.

**Rough budget:** none under 800 words, at most one per 800–1,500, and never stacked. Held
loosely — it is a smell test for over-reaching, not a quota to fill.

**Banned setups:** "Think of it as", "Imagine", "Picture", "It's like", "As if", "The X of Y",
"Works like", "Acts like", "A bridge between", "A lens for", "A roadmap for", "The engine of",
"The backbone of", "The DNA of".

**Tired families for abstract work:** journey, battlefield, ecosystem, engine/fuel,
map/compass, signal/noise (unless literal), iceberg, north star, flywheel, scaffolding,
plumbing, gardening, chess, sports, puzzle.

**Metaphor verbs applied to ideas, strategy or products:** sanded down, bolted on, stripped
back, stitched together, woven, layered, carved out, baked in, distilled, unpacked,
crystallized, sharpened, surfaced, amplified, anchored, cemented, bridged. Use the literal
verb: cut, added, removed, changed, joined, caused, showed, reduced, clarified, fixed, named,
compared, chose, rejected.

- Before: "Your onboarding is a leaky bucket."
- After: "42% of users leave on step 2, where the form asks for billing details before showing
  the product."

The fix is usually not a better metaphor. It is the specific fact the metaphor was standing in
for — which is why this belongs next to the vague-attribution and puffery entries above.

## Formatting / mechanics

- **Em-dash rate out of step with the author** (—). Checked 2026-08-13, and this
  is no longer a model-agnostic rule. Wikipedia's guide cites *"A July 2026 study
  [finding] that of contemporary models only Claude used em dashes more than
  professional writers, and ChatGPT used them less"*, and notes GPT-5.1 was changed
  to suppress them — so vendors are actively training the signal away. It also warns
  the sign *"is most useful when taken in combination with other indicators, not by
  itself"*. Compare against the author's own rate rather than against zero; a blanket
  cut is backwards for at least one major model family. Where the rate really is high
  for this writer, most become commas, periods, or parentheses.
- **Mechanical boldface** on key terms; **inline-header lists** ("**Performance:** …"). Prefer prose.
- **Title Case In Headings** → sentence case.
- **Decorative emoji** as section markers → remove.
- **Curly quotes** ("…") → straight quotes ("…") — *only where the surrounding file
  uses straight ones.* Checked 2026-08-13: this fires on ordinary human output, since
  macOS and iOS substitute smart quotes system-wide, Word does the same, the Chicago
  Manual of Style prefers them, and citation tools echo a source's own curly title.
  Wikipedia also notes *"Gemini and Claude models typically do not use curly quotes"*,
  so it misses two current model families outright. Treat as a consistency check
  within one document, not as evidence of origin.

## Do not "fix" these by merging another list over them

Three entries in this file **contradict** the popular anti-AI-writing lists, on purpose and
with sources. A future merge that quietly restored the common version would be a regression,
so the disagreements are named here rather than left to be rediscovered.

- **Em dashes.** The circulating rule is a blanket ban. This file compares against the
  author's own rate instead, because a July 2026 study found that of contemporary models only
  Claude used em dashes *more* than professional writers and ChatGPT used them *less*, and
  GPT-5.1 was changed to suppress them. A blanket cut is backwards for at least one model
  family.
- **Hedges** (*arguably, to some extent, broadly speaking*). Commonly listed as AI tells.
  Three independent sources put them on the **human** side -- Jiang & Hyland (2025), Mizumoto
  et al. (2024), and Wikipedia's own guide. Tighten them as wordiness; never score them as
  machine origin.
- **"In order to", "due to the fact that", "as a result of".** Same story: Wikipedia reports
  these as *more* common in human writing across 25 years of editing. Strunk edits, not tells.

The general rule this file follows: **a bigger banned list is not a better one.** The
`delete-ai-words` list compared against on 2026-08-16 carries 82 words to this file's 61, but
the extra ones are largely B2B marketing vocabulary -- *cutting-edge, state-of-the-art,
turnkey, plug-and-play, mission-critical, future-proof* -- which predates LLMs by decades and
is written by humans daily. Importing it would conflate puffery with machine origin and fire
on ordinary product writing. Only five words were taken from it, each a morphological sibling
of a word already sourced to Kobak et al. (2025).

## Chatbot artifacts (delete on sight in pasted content)

- "Great question!", "Certainly!", "You're absolutely right!", "I hope this helps", "Let me know if you'd like…"
- Knowledge-cutoff disclaimers: "As of my last update", "While specific details are limited…".
- Sycophantic/servile tone and over-politeness stacking.
