# Channels — detection and rewrite rules

Detect the type, then apply these on top of the universal patterns in `ai-patterns.md`.

## Stance — declare it, don't infer it

Every channel below can be written in either stance, and both are correct: a product write-up in third person and a personal account in first person are not different qualities of prose, they're different jobs. PERSON (first- and second-person density) is a stance the author chooses per piece. Report it as context, never as a flag or a score deduction.

STIFFNESS (contractions, nominalization, analytic negation, demonstratives, word length, lexical diversity) is the axis that gets flagged, and none of it requires first person. A piece written entirely in the third person can still use "doesn't" instead of "does not". Flag stiffness features exactly as usual, regardless of the declared stance.

These features say a draft reads as formal. They do not say who or what wrote it, and lexical diversity in particular is a register indicator only — never treat it as evidence of AI origin.

**Why person is reported and not flagged**, since the reason matters more than the rule. Not because it is statistically unrelated to the stiffness features — most of them sit on the same dimension in Biber (1988), and establishing independence would need roughly a hundred same-channel documents by one author, which nobody has. The reason is that first-person density is a rhetorical choice rather than a defect: Thonney (2013, *Across the Disciplines*) reports experts using first person to project confidence and authority, at around four times the rate of students, and its prevalence varying by discipline, within disciplines, and within genres. A tool that treats low first person as a fault pushes every document toward chatty and takes away the writer's ability to be impersonal on purpose. Flag stiffness; report person.

Before scoring or rewriting, ask which stance this piece needs, or use the stance already declared in `WRITING_CONTEXT.md` or the brief. Do not infer it from the draft: a stiff impersonal draft and a correctly impersonal draft read identically on person density, so guessing from the text alone throws away the one thing that tells them apart.

## docs (technical) — DEFAULT for technical input

**Detect if:** code fences, file paths, CLI commands, headings like Prerequisites/Setup/Usage/Rollback, API/endpoint references, commit/PR phrasing, or it's clearly a README/runbook/ADR/design doc.

**Markers to flag:** marketing adjectives in reference material (robust, powerful, seamless, blazing-fast); "simply"/"just"/"easily" papering over real difficulty; passive voice that hides who does what ("the config is applied" → who applies it, when); vague steps that aren't reproducible; significance inflation about the tooling.

**Rewrite rules:**
- Imperative, second person for instructions ("Run X", "Set Y"), present tense for behavior.
- Every step reproducible: exact command, expected output, what to do on failure.
- State preconditions and the failure/rollback path; name the actual error, not "if something goes wrong".
- Keep voice conservative — accuracy and unambiguity over personality. No invented version numbers, flags, or outputs.
- Commit/PR: subject in imperative under ~72 chars, body explains *why* and the tradeoff, not a feature-list of *what*.

**Scoring dims:** Clarity, Accuracy/Verifiability, Actionability.

## blog

**Detect if:** headings/subheadings, >3,000 chars of structured prose, developed argument, "In this article", SEO structure.

**Rewrite rules:** keep heading structure but fix generic heading copy; vary paragraph length; replace "In this article/Let's dive in" meta-commentary with a real opening; open with a specific hook (story, datapoint, contrarian claim), close with a challenge/principle/open question rather than a recap.

**Scoring dims:** Authenticity, Reader Value, Domain Credibility.

## youtube-script (spoken long-form / educational)

**Detect if:** the user asks for a video script, explainer, tutorial narration, or voiceover — content meant to be *spoken*, not the title/description (those are marketing packaging and belong in hook-and-human).

**Markers to flag:** written-prose tells that don't survive being read aloud (long subordinate clauses, nested parentheticals); signposting ("In this video we'll dive into…"); restating a heading out loud; uniform sentence length (deadly when spoken); filler intros before the first real point.

**Rewrite rules:**
- Write for the ear: short sentences, direct address ("you"), contractions. Read it aloud mentally — if you run out of breath, cut.
- Open with the actual payoff or a concrete question, not "Hey guys, welcome back, in today's video…".
- Vary rhythm deliberately; spoken monotone is worse than written monotone.
- Keep it accurate and credible — this is the teaching, so no invented specifics, and name real tradeoffs. A soft CTA at the end is fine; don't sprinkle sales hooks through the body.
- Mark visual/B-roll or [PAUSE] cues in brackets if useful; keep them out of the spoken lines.

**Scoring dims:** Clarity, Accuracy / Verifiability, Authenticity.

**Detect if:** one-sentence-per-line formatting, hashtags, end-CTA ("Thoughts?"), @mentions, <3,000 chars no headings, emoji as section breaks, vulnerability/credential-stack hooks.

**Markers to flag:** pivot transitions ("But here's the thing", "Here's what most people miss"); engagement-bait closers ("Agree? Drop a comment 👇" — also penalized as spam); vulnerability performance ("Can I be real for a second?"); fake humility ("I'm no expert, but…"); tag-and-thank lists; arrow chains (→); ALL-CAPS single-word emphasis; "What if I told you…", "Here's what nobody tells you…", "Read that again.", "Let that sink in.", "And honestly?".

**Rewrite rules:** ≤1,300 chars short-form / ≤3,000 long-form; weave 1–3 hashtags or drop them; remove engagement bait; arrows → sentences; one-line paragraphs → 2–4 sentence paragraphs; emoji only if it carries meaning.

**Scoring dims:** Authenticity, Reader Value, Domain Credibility.

## email

**Detect if:** subject/To/From/CC, greeting formula, formal sign-off, "I wanted to reach out", "Following up on", ask + sign-off structure.

**Rewrite rules:** lead with the ask/purpose, not context; cut to minimum length (most AI emails are 2–3x too long); one ask per email; specific CTA ("Free Tuesday at 2?" not "Let's chat sometime"); skip "I hope this finds you well"; one sign-off, not a stack; subject specific to the content; match formality to the relationship.

**Scoring dims:** Authenticity, Clarity, Appropriate Tone.

## slack

**Detect if:** #channel refs, @here/@channel/@user, short thread messages, very casual, <500 chars, inline emoji shortcodes.

**Rewrite rules:** ≤4–5 sentences (if longer, suggest moving to a doc/email); lead with the ask/action; no formal greeting or sign-off; match the channel's casual tone; if sharing a link, one sentence of context, not a summary.

**Scoring dims:** Naturalness, Clarity, Brevity.
