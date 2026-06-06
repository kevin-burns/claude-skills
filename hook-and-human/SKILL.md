---
name: hook-and-human
description: >
  Write, punch up, and review marketing copy that stops the scroll and converts, while still sounding like a real person. Use this skill whenever the user wants to: write a LinkedIn post, X/Twitter post, Bluesky post, cold or marketing email, ad, landing-page section, headline, hook, lead magnet, or YouTube packaging (video title, thumbnail text, description hook, end-screen/CTA, community post); "punch up" or "make this convert" or "make this land"; sharpen a CTA; or review copy for stopping power and conversion. Also trigger on "hook", "scroll-stopper", "make it punchy", "marketing copy", "sales copy", "cold email", "ad copy", "landing page copy", "lead magnet", "bluesky", "youtube title", "video title", "thumbnail", "make this convert". Deploys persuasion patterns (hooks, frameworks, one strong CTA) on purpose, reads WRITING_CONTEXT.md for voice and approved facts, and never fabricates specifics. For neutral, credibility-first writing (docs, README, plain explanation, or a teaching/explainer video script) use clear-and-human instead.
license: MIT
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion
---

# Hook and Human

The persuasion sibling of `clear-and-human`. That skill strips engagement patterns to protect credibility; this one **deploys them on purpose** to win attention and conversions — without crossing into slop. Marketing copy that reads like a person, hooks in the first line, and asks for exactly one thing.

Use this for social, ads, sales, and landing copy. Use `clear-and-human` for docs, runbooks, and anything where authority beats reach.

## Modes

- **Write** — generate copy from a brief ("write a LinkedIn post about X"). Pick a framework, lead with a hook, close with one CTA.
- **Punch-up** — the user has flat copy that's accurate but doesn't land. Add a hook, tighten rhythm, sharpen the CTA. Don't change the claims.
- **Review** — score the copy for stopping power and conversion (see scoring). Offer a punch-up.

Default to **Write** for a brief, **Punch-up** for pasted flat copy, **Review** if they ask "is this any good?".

## The floor (non-negotiable — this is what keeps it human)

These carry over from `clear-and-human` unchanged. Persuasion is not a license to break them:

1. **Never fabricate specifics — including the soft ones.** No invented stats, testimonials, customer names, results, or credentials. Use only what's in the brief or `WRITING_CONTEXT.md`. The trap in marketing copy is the *soft* fabrication, because it doesn't look like a lie: a **derived** number (rounding an approved "40→6 min" into "saves 30 minutes"), an **aggregate-time** claim ("get your afternoon back" — you don't know how often they deploy), or a **soft outcome** ("fixes ship the same hour they're reported") are all fabrications too. The reader can't tell invented color from a measured result, so each one spends trust you haven't earned. Stick to the approved fact and let it carry the weight; if you want another proof point, leave `[ADD PROOF]` and say so. A made-up *implication* damages credibility as fast as a made-up number.
2. **Cut generic AI filler.** Hooks are fine; *filler* is not. Still banned: delve, leverage, synergy, robust, seamless, transformative, tapestry, "in today's landscape", "unlock your potential". These don't persuade — they signal a machine.
3. **No hollow vulnerability or fake humility.** "Can I be real for a second?", "I'm no expert, but…" — these backfire; readers smell the performance. If a personal story is real, tell it plainly. If it isn't, don't.
4. **One CTA, specific.** Not three asks, not "thoughts?". One clear next action.
5. **Vary rhythm and match voice.** Short line, then a longer one. Pull voice from `WRITING_CONTEXT.md`. Uniform cadence reads as generated even when the words are punchy.

## Context

Read `WRITING_CONTEXT.md` (or `FOUNDER_CONTEXT.md`) from the project root first — same file `clear-and-human` uses. Pull brand voice, audience/ICP, the offer, approved proof points, and banned phrases. If it's missing and the brief is thin, ask up to 3 questions (offer, audience, the one action you want) before writing.

## What to deploy (the part clear-and-human suppresses)

Full detail in `references/frameworks.md`. The essentials:

- **Lead with a hook.** First line earns the second. Specific > clever. Open a curiosity gap you actually close.
- **Pick a framework** to structure the body: AIDA, PAS, or BAB (see reference). Don't show the seams.
- **One CTA**, concrete and low-friction ("Reply 'guide' and I'll send it", not "Let me know if interested").
- **Format for the channel** — line breaks, length, hashtag/emoji norms in `references/channels-marketing.md`.

The difference from slop: a hook backed by a real specific is persuasion; a hook backed by nothing is bait. Earn the emphasis with the actual number or story, never with ALL-CAPS or "Read that again."

## Review scoring (1–10)

| Dimension | Measures | Target |
|---|---|---|
| Scroll-stop | Does the first line stop the reader? | 8–10 |
| Offer clarity | Is the value/offer unmistakable? | 8–10 |
| Conversion | One clear, specific, low-friction CTA? | 8–10 |
| Authenticity | Sounds like this person/brand, not generic AI? | 7–10 |

If Scroll-stop is high but Authenticity is low, flag it: attention-grabbing but hollow, won't build trust or repeat.

## Self-audit (run before presenting Write or Punch-up output)

1. Would the first line actually stop me mid-scroll, or is it a template hook with no payoff?
2. Is there exactly one CTA, and is it specific?
3. Did I invent any number, name, or result — including a *derived* number, an *aggregate-time* claim ("hours back", "your afternoon back"), or a *soft outcome* the approved facts don't actually support? If yes, cut it or replace with a placeholder.
4. Does it sound like the brand in `WRITING_CONTEXT.md`, or like generic marketing AI?

Fix what fails, then present.

## Relationship to clear-and-human

Siblings, not a pipeline. Pick by intent: reach/conversion → here; credibility/clarity → `clear-and-human`. They share `WRITING_CONTEXT.md` and the no-fabrication floor, so a piece can move between them without contradiction. Don't run both on the same draft in sequence — they optimize for different things and will fight.

## Provenance

Adapted (MIT / public domain): persuasion frameworks and hook/CTA patterns synthesized from common copywriting practice and `ognjengt/founder-skills` (MIT); the no-fabrication floor and voice/rhythm rules inherited from its sibling `clear-and-human`.