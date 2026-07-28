# The LinkedIn profile mode (job-seeker lens)

This mode optimises a LinkedIn profile for the job-seeker use case: findable in
Recruiter search, credible to the human who opens it, never inventing anything.
It does not cover the founder/consultant use case (demand generation, not
screening) — that lens is out of scope for this mode entirely.

## 1. Why a profile is not a CV

A CV is tailored 1:1 to one job description. A profile is one artifact read by
many people — recruiters searching for a dozen different roles, hiring managers,
former colleagues, connection requests. You cannot keyword-tailor a single page
to twelve roles at once without producing soup: a headline and About that try to
say everything end up saying nothing to anyone. That's why positioning comes
before keywords here (Section 3) — pick the story first, then decide where
keywords for a *specific* target role are allowed to land (Section 4).

LinkedIn Recruiter search is still automated screening over a career document,
even though it doesn't look like an ATS. The host skill's split holds unchanged:
lock down the knowable, controllable surface (character limits, keyword
placement, consistency with the CV); feed the noisy judgment layer — the human
who actually reads the profile — strong, true material; never promise a
ranking. Nobody, including LinkedIn, can tell you where Recruiter search will
place you. This mode maximises what you control and is honest about the rest.

## 2. Getting the profile in

Assume ragged pasted text. "Save to PDF" from LinkedIn's own export is a
five-click detour most users skip, so this mode has to degrade gracefully on a
partial, messy paste — missing sections, broken line wraps, stray UI chrome
copied along with the text — rather than demanding a clean export before it
will start. Work with whatever comes in; ask only for what's missing and needed
(e.g. "what's your current headline?" if it wasn't in the paste).

A PDF export is fine when the user has one. But extraction stays **upstream and
deterministic** — the agent reading the file, pymupdf, markitdown — never an
LLM extractor running inside this skill. This is the same boundary the CV
workflow draws in its own Step 2: turning a file into text is a deterministic,
inspectable step that happens before any reasoning step runs, so downstream
results don't vary on parsing noise.

If there's no profile at all yet, cold-start from the CV: the CV already has
the roles, dates, and outcomes a profile needs, and the positioning pass
(Section 3) works the same way whether the source is a pasted profile or a CV.

## 3. The positioning pass — one question, not an interrogation

Ask one question: **who do you help, what changes for those people, and what
proves it?** Then produce a candidate headline from the answer immediately —
don't wait for a fuller profile draft before giving something back.

The reason for asking exactly one question, not a form: nobody sits down and
rewrites a whole LinkedIn profile in one pass. Real users fix the headline and
stop. A positioning step that never gets to output because it's still asking
follow-up questions is not differentiation — it's just prose nobody reads. A
user who wants only a headline should get a good one from a single exchange; a
user who wants more should get coherence across headline, About, and skills
because the answer to that one question anchors all three.

If the answer is only a job title — "I'm a Senior Software Engineer," the
common case when someone hasn't thought about positioning before — don't ask
the question again. Give one concrete example of what a fuller answer looks
like ("something like: I help fintech teams cut deploy risk — led three
zero-downtime migrations, most recently moving a 40-service platform off a
monolith") to show the shape of a good answer, then let them react to that
rather than stalling on a repeated open question.

Anything the user claims in this pass that they can't back up — a metric they
don't actually have, an outcome they're not sure was theirs alone — becomes a
`[VALIDATE]` placeholder in the draft, not a quietly asserted fact. The user
resolves it before it goes live.

## 4. The keyword placement rule

Target-role keywords are the right input for **coverage** — the specific nouns
a recruiter's search needs to find you — and the wrong input for **voice**.
They may land in **skills, experience, and the tail of About**. They may
**not** drive the **headline** or the **first ~200 characters of About**.

The reason this is a hard boundary and not a style preference: the headline
and the pre-fold opening of About are the only parts of a profile most humans
ever read. Everything past the "see more" fold is read by search indexes and
by the minority of people who click through, not by the recruiter skimming a
results list. If keywords are allowed to drive those first ~200 characters,
the profile reads like a keyword bag to every human who sees it — the exact
"soup" problem from Section 1, concentrated into the one place it does the
most damage. The headline and the opening of About should come from the
positioning line (Section 3) and the user's own specifics; keywords earn their
place further down, where they help search without costing the human read.

State this rule explicitly every time you write to a profile, because no
script can enforce it — `li_profile_check.py` checks lengths and coverage
(Section 7), not where a term sits relative to the fold or whether it reads
naturally. A placement rule with no stated reason is the first thing that gets
dropped under pressure to "just add the keyword"; keep the reason attached to
the rule.

## 5. Per-field rules

**Headline** (220 characters). Front-load the specific — the thing that makes
this person different, not a role-title restatement. A recruiter scanning
search results reads the first handful of words before moving on, so the most
distinctive fact belongs at the front, not the end.

*When you don't have enough to go on, still hand back headlines.* A user who says
"just fix my headline" and gives you almost nothing puts two rules in tension: you
cannot invent a specialty or a metric, but a template plus homework is not the
thing they asked for — and an eval of exactly this case showed the mode retreating
to a fill-in-the-blank structure while an unaided model cheerfully produced four
polished headlines built on skills the user never claimed. Neither is right.

Resolve it by writing **two or three complete candidate headlines with the unknowns
marked as slots**, not by withholding the deliverable:

    IT Support Lead | [your top 2 tools, e.g. ServiceNow, Intune] | cut [X]% off ticket backlog
    [Sysadmin / Cloud Ops / Security — pick the true one] supporting [N] users across [Windows/Linux]

A bracketed slot is visibly not a claim, so this fabricates nothing — the user reads
it as a blank to fill, never as something you asserted about them. They leave with
something shaped they can finish in thirty seconds, which is what they came for.
Give each candidate its character count, and say which slot matters most to fill.
Branching on a plausible specialty is fine *as a labelled branch* ("if you're
actually in security, this one"); stating the specialty as fact is not.

**About** (2,600 characters). The fold at ~200 characters is the real
constraint, not the 2,600 limit — almost nobody expands "see more," so
everything that has to land, lands before the fold. Unlike a CV, first person
is correct here: "I help..." not "Helped..." — a profile is a personal
statement read in a personal-network context, and third-person CV register
reads as stiff in this channel. Keyword-bearing material, if any, belongs in
the tail, after the specifics that earned the read.

**Skills** (80 characters each). Order matters — LinkedIn shows only the top
few skills prominently, and recruiters filtering by skill see the list in the
order given, so lead with what the target role actually searches for. Only
list skills the candidate genuinely holds; this mode never adds a skill to
close a coverage gap it can't back up (Section 7 explains why the checker
doesn't push toward that either).

**Experience descriptions** (2,000 characters per role). Same register as
About — first person, not the CV's third-person fragment convention. In v1
this mode does not do full bullet-by-bullet rewrite depth here: apply the
positioning line and de-slop pass lightly if asked, but treat a
role-by-role rewrite as future scope. If the user specifically asks for a
full experience-bullet rewrite, tell them plainly that this mode currently
rewrites headline, About, and skills, and offer the lighter pass instead of
silently doing partial work.

## 5.5 De-slopping a profile

Strip AI-written texture from a profile the same way Step 5.5 of the host skill
does for a CV — but only part of `references/deslop-cv.md` applies here, because
that file also encodes CV-specific register rules that are wrong for a profile.

**Shared (channel-neutral) — apply as-is:**
- The AI/slop pattern list (empty vocabulary, weak verbs, significance inflation,
  superficial `-ing` tails, rule of three, vague quantification, mechanics) — these
  are about hollow prose, not register, so they hold for a profile too.
- **The keyword guard** — keep a flagged word when it's referential (a target-role
  keyword or the real name of a tech/metric the candidate used), cut it only when
  it's empty booster.
- **The soft-fabrication floor** — no derived numbers, aggregate-time claims, or
  soft outcomes with no measured basis; use `[VALIDATE]` per Section 3, not
  `[ADD REAL METRIC]` (this mode's own placeholder convention).

**CV-only — do NOT apply to a profile:**
- The **"CV-channel rewrite rules" block** (no first person, no contractions, keep
  fragment action-verb bullets). A profile's About is a first-person personal
  statement (Section 5) — applying the CV's third-person fragment convention here
  would silently undo the register this mode deliberately sets.

## 6. The limits block

LinkedIn does not publish a consolidated limits table. These numbers are
third-party-reported, cross-checked across two independent sources
([Letter Counter](https://lettercounter.org/blog/linkedin-character-limit-guide/),
[LinkedHelper](https://www.linkedhelper.com/blog/linkedin-character-limit/)) —
treat them as liable to drift if LinkedIn changes its UI.

| Field | Limit | Note |
|---|---|---|
| Headline | 220 | ~240 reported on mobile; this mode targets the stricter 220 |
| About | 2,600 | ~200 chars visible before the "see more" fold |
| Experience description | 2,000 | per role |
| Position title | 100 | |
| Company name | 100 | |
| Skill (each) | 80 | length per skill; a cap on skill *count* is unconfirmed |

`scripts/li_profile_check.py` is the enforcement — it holds all six numbers in
one `LIMITS` block so a drift is a one-line fix in that file rather than a
hunt through this prose. In v1 this mode rewrites headline, About, and skills
at full depth, with a lighter pass on experience descriptions (Section 5), so
the checker's input schema currently checks headline, About, and skills
against their limits; position title, company name, and experience-description
limits are in the table above for reference if you're eyeballing those fields
by hand.

## 7. Running the checker

Run it from inside the `cv-and-human` directory:

```bash
uv run scripts/li_profile_check.py profile.json
# or pipe JSON on stdin:
cat profile.json | uv run scripts/li_profile_check.py
# machine-readable output:
uv run scripts/li_profile_check.py profile.json --json
```

Exit code is `0` when everything checked is within limits, `1` otherwise — use
that in a loop if you're iterating on a draft.

**Input shape** — a JSON object:

```json
{
  "headline": "...",
  "about": "...",
  "skills": ["...", "..."],
  "keywords": ["...", "..."],
  "must_contain": ["...", "..."]
}
```

- `headline` — the draft headline string.
- `about` — the draft About string.
- `skills` — list of skill strings; each is checked against the 80-character
  skill limit.
- `keywords` — target-role keywords to check for coverage (Section 4's
  placement targets). Advisory, see below.
- `must_contain` — the user's own specifics that must appear **above the
  fold** (the first ~200 characters of About) — e.g. the metric from the
  positioning line, a named system they own, a distinctive fact. Not a
  target-role keyword — Section 4's placement rule keeps those out of the
  pre-fold text, so requiring one here would fight the rule this checker is
  supposed to protect. Drives the front-load check.

**What each part of the output means:**

- **`fields`** — headline and About against their character limits, counted in
  UTF-16 code units to match LinkedIn's own browser-side counter (a Python
  `len()` count would under-count anything containing an emoji or other
  character outside the Basic Multilingual Plane, and reporting a count the
  real field then rejects is worse than reporting nothing). An entry with
  `ok: false` reports `over_by` — trim exactly that many characters.
- **`front_load`** — which `must_contain` terms are missing from the visible
  text above the fold. A missing term means a specific that matters isn't
  landing where it will actually be read; move it up.
- **`skills`** — each skill's own length check. An over-limit skill needs
  shortening, not dropping — order and content are the user's call.
- **`coverage`** — for each keyword, which fields carry it, and whether it
  appears anywhere at all.

**Read `coverage` carefully — it has two properties that are easy to
misread:**

1. **It's a plain, case-insensitive substring match**, not a whole-word match.
   A short keyword like "Go" will register as covered if the text contains
   "Google" or "Django" — the checker isn't doing anything smarter than
   `needle in haystack.lower()`. Treat a "covered" result as a hint to verify,
   not proof the keyword is genuinely present in a useful sense, especially
   for short keywords. **The same substring logic drives `front_load`'s check
   on `must_contain`** — and unlike coverage, `front_load` *does* gate `ok`
   and the exit code, so a short `must_contain` term can false-pass and turn
   a genuinely buried specific green. Prefer a distinctive phrase (a metric,
   a named system) over a short token in `must_contain`.
2. **Coverage does not affect `ok` or the exit code.** A profile can be fully
   `ok` — every length within limits, everything required above the fold —
   while several target keywords show `covered: false`. This is deliberate,
   not a gap: an uncovered keyword usually means the candidate genuinely
   doesn't have that skill yet, not that the draft forgot to mention it. If
   coverage gated `ok`, the only way to turn a result green would be adding a
   keyword the candidate can't back up — which this skill forbids outright
   (Section 3, the `[VALIDATE]` discipline). So coverage is reported as
   information for the user to act on, not as a target the checker pushes
   toward closing. Uncovered keywords belong in the delivery report's "Real
   gaps" section (Section 9) — the user's decision, not an automatic edit.

## 8. CV ↔ profile consistency

When both a CV and a profile exist, compare job titles and employment dates
between them. A recruiter who likes a candidate frequently opens both
documents, and a title or date that disagrees between the two reads as a red
flag — inconsistent, possibly embellished, worth a harder look — even when
both versions are individually true (e.g. a title that was informally used
day-to-day but never made official).

Report every disagreement found. Never silently reconcile one to match the
other: only the user knows which version is accurate, or whether both are
correct for different reasons (a promotion that hit the CV but not yet the
profile, for instance). Silently picking one would risk introducing an error
into whichever document was right. Surface it in the delivery report
(Section 9) and let the user resolve it.

## 9. The delivery template

For a single-field request ("just fix my headline"), deliver only that
field's block plus its character count and the honesty note — not the full
template. The full structure below applies once more than one field has been
rewritten in the session.

```
# LinkedIn Profile Report — [target role]

Lens: job-seeker

## Positioning
[one line: who you help, what changes, what proves it]

## Headline  (214/220)
[copy-paste block]

## About  (1,840/2,600 · fold at ~200 shown)
[copy-paste block, with the fold position marked inline]

## Skills
[list, each within 80 chars]

## Keyword coverage
| Target keyword | Field carrying it | Status |

## CV ↔ profile consistency
[title/date disagreements, or "consistent"]

## Real gaps (your decision)
- [thing not in the background — never invented]

## Honesty note
[Recruiter ranking is not public and partly non-deterministic; this maximises the
controllable surface rather than guaranteeing visibility.]
```

The `Lens: job-seeker` line is not decoration — a request like "help with my
LinkedIn" carries no signal about which lens is in play, so naming it in the
output makes a wrong assumption visible and correctable in one line rather
than silently baked into every field.

## 10. What this mode will not do

This is a line, not a gap — these are excluded on purpose, not left for a
later version:

- **Engagement automation of any kind** — connecting, posting, commenting,
  messaging, following, or applying on the user's behalf. This crosses into
  LinkedIn ToS territory and real account-suspension risk; this mode only ever
  produces text for the user to paste in themselves.
- **Scraping or fetching linkedin.com.** This mode works from text the user
  pastes or exports, never from a live fetch of the site.
- **Inventing roles, metrics, skills, or endorsements.** Every fact in a
  profile draft traces back to something the user supplied; anything unproven
  becomes a `[VALIDATE]` placeholder (Section 3) or a named gap (Section 9),
  never a quiet addition.
- **Promising search ranking.** Recruiter search placement is not public and
  not fully deterministic. This mode maximises the controllable surface
  (Sections 4–7) and says so plainly in every report's honesty note — it never
  claims a rewrite will move someone up a results list.
- **Writing LinkedIn posts.** A post is persuasive or informational content
  for a feed, a different job entirely from profile optimisation. Route
  persuasive post-writing to `hook-and-human` and neutral/informational
  post-writing to `clear-and-human`.
