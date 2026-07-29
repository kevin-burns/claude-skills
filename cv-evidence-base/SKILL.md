---
name: cv-evidence-base
description: >
  Interrogates a CV or resume to recover the evidence that never made it onto the page,
  and works out which roles the person is genuinely credible for. Grades their background
  against role archetypes derived from what they actually did rather than from their job
  titles - including archetypes they are NOT credible for - asks the oblique questions that
  dislodge buried achievements, names where the page would get binned in a seven-second
  scan, and maintains an evidence base plus an action ledger across sessions. Use this
  whenever the user has NO target role in mind and is asking an open question about
  themselves: what roles they could realistically go for, whether they are pitching
  themselves right, whether they are pigeonholed, why they get no callbacks or interviews,
  what they are missing, or what their CV says about them. Use it when they hand over a CV
  with no clear instruction - "does this look OK", "be honest with me", "am I positioned
  right". ALSO use for a career change, a step up, going freelance or contracting, or
  restarting a job search after a long gap. Do NOT use when the user names something to be
  DONE to the document - tailor it to this job description, ATS-proof it, keyword/gap
  analysis, check it parses, de-slop it, or anything about a LinkedIn profile's headline,
  About section or recruiter-search keywords. That is cv-and-human, which is the right next
  step once this skill has established what is true and worth claiming.
---

# CV evidence base

## What this is for

Most CVs are not weak because the wording is bad. They are weak because the
person's best evidence never made it onto the page. They omit the things they
found easy, because they assume everyone finds them easy. They describe
responsibilities they held rather than outcomes they caused. They file their
whole career under a job title the market has quietly moved past.

None of that is fixable by rewriting sentences. It is fixable by asking
questions until the missing material comes out, and then deciding what deserves
space.

So this skill does not polish prose. It interrogates a person, produces a
durable record of what is true about their career, and tells them what to change
and why. The rewriting happens elsewhere.

## The two readers

Everything here follows from a fact about how CVs are actually consumed. There
are two readers, and they want opposite things.

**Reader one** spends roughly seven seconds deciding whether to bin it. For this
reader, only the top third of page one exists. Their job is elimination, and
they are looking for reasons to stop reading.

**Reader two** has already decided the candidate is interesting and is now
hunting for reasons to be confident. This reader wants *more*. Shortening the
document actively hurts here.

This is why "how long should it be" is the wrong question. The right question is
whether the top third earns reader two's attention, and whether the rest rewards
it. Keep both readers in mind when judging any change.

## The two artifacts

Every session maintains two files. Keeping them separate matters, because facts
and recommendations have different lifespans.

**`evidence-base.md`** — durable, archetype-neutral, append-mostly. "I cut CI
build times from 40 minutes to 9 across 30 repos" is true regardless of what job
they are chasing. This file grows across sessions and is never wholesale
rewritten. It is the most valuable thing produced here and it is longer and
richer than any CV could be. It never gets sent to an employer.

**`action-ledger.md`** — derived, archetype-specific, perishable. "Lead with the
build-time figure, move certifications to the bottom" is only valid for one
target and expires when the target changes or the change is applied. Regenerate
this freely.

Templates for both are in `assets/`. Read them before writing either file for
the first time. If the user supplies existing versions at the start of a
session, read those instead and continue from them — do not start over.

## Session flow

A full pass takes more than one sitting. Aim to leave every session with both
files updated and one concrete improvement made, even if the session is cut
short. A session that ends with nothing written down is a session wasted.

### 1. Orient

Read the CV. If prior artifacts were supplied, read those too and check the
coverage table — whatever it says has been mined, do not re-mine. Opening a
session by re-asking questions already answered is the fastest way to get this
tool abandoned.

Open by reflecting back what the CV currently transmits, in two or three
sentences, before doing anything else. Not what the person is worth — what the
page says about them to someone who has never met them. This is often the first
useful shock, and it costs nothing.

### 2. Grade the archetypes

Propose the role archetypes this person is plausibly aiming at, derived from
their evidence rather than their job titles. Do not use a fixed taxonomy — read
what they have actually done and name the market categories that fit. See
`references/archetypes.md` for worked examples of how to derive these, spanning
both technical and non-technical careers.

This is often the most valuable output of the whole exercise, because people get
pigeonholed by their own job title. Someone who has called themselves "DevOps"
for six years may have an evidence base that reads far more like platform
engineering. Someone titled "office manager" may have been running procurement
and vendor negotiation. Naming that gap is worth more than any amount of bullet
polishing.

Grade each archetype into one of three buckets:

- **Credible now** — the evidence exists, it is just badly framed or buried
- **One or two artifacts away** — they would be credible if they could evidence
  one specific thing; say precisely what that thing is, and where in their
  history to go looking for it
- **Not credible** — and say so

That third bucket is the discipline that makes the first two mean anything. The
natural failure mode here is telling someone they are a plausible fit for
everything, which makes the whole exercise worthless — a grading with no
exclusions is flattery wearing a lab coat. Always name at least one archetype
they are not currently credible for, and say what is missing.

If the user declares a target up front, still do this grading. Their declared
target may be the thing that is holding them back.

Then agree one archetype to work against for this session. Everything downstream
is aimed at it.

### 3. Elicit — the curious colleague

Now change register completely. This phase is warm, curious and
non-judgemental, because hostile questioning is bad at elicitation: people get
defensive, they under-report, and they start justifying instead of remembering.

The mechanics matter more than the tone. Direct questions produce nothing —
"what were your key achievements?" reliably returns the same tired bullets
already on the page, because it asks the person to self-assess, and they already
did that when they wrote the CV. Oblique questions bypass that. Ask about
difficulty, causation, counterfactuals and other people's perceptions:

- What was the hardest part of that, and why was it hard?
- Why were *you* the person asked to do it?
- What would have happened if you hadn't been there?
- What would your team lead say you were relied on for?
- What went wrong, and what did you change afterwards?
- What's the thing you're quietly proud of that isn't on here?

`references/question-bank.md` has the full set, organised by what each question
is trying to dislodge, plus follow-up probes for scale, baseline and durability.
Read it before the first elicitation round.

Practical constraints that keep this usable:

- **Batch questions, three to five at a time.** One-at-a-time interrogation is
  exhausting and makes people give shorter answers as it goes.
- **Two or three batches per session, then stop.** A forty-question grilling
  gets abandoned at question nine, and everything after that point is lost work.
- **Prioritise by rejection risk.** Aim questions at the gaps most likely to get
  the CV binned for the chosen archetype, not at whatever is most interesting.
- **Follow the energy.** When an answer opens something up, probe it rather than
  marching on through the list.

Record answers close to how they were said. When someone hedges — "maybe 30%?",
"I think it was about a year" — the hedge is data. Preserve it as
`approximate` or `unverified` in the evidence base rather than smoothing it into
confident prose. This is the single biggest fabrication risk in the whole
process: questioning generates fresh claims under social pressure, and confident
phrasing can quietly promote a guess into a fact the person then has to defend
in an interview.

### 4. Screen — the direct pass

Now go cold. Same analysis a sceptical recruiter would run, but delivered as
diagnosis rather than verdict. Not "this is weak" but "a recruiter scanning this
for six seconds sees X, and the thing you just told me about Y isn't visible
anywhere."

Score harshly, phrase plainly. The judgement should be blunt and the framing
should be clinical — you are describing what the page transmits, not what the
person is worth.

Ground every observation in a named, checkable failure rather than a vibe:

| Failure | What it looks like |
|---|---|
| Unscaled claim | An achievement with no size attached — how many, how big, how long, how much |
| Baseline-free outcome | "Improved performance by 40%" with no starting point, so the number means nothing |
| Orphan keyword | A tool or skill in the skills list that appears in zero roles |
| Stack as identity | A dense list of technologies with no account of what was built, why those tools were chosen, or what was learned — the reader cannot tell a senior engineer from someone who attended the training |
| Scope/verb mismatch | "Led" and "owned" implying a seniority the described scope doesn't support |
| Responsibility without outcome | What they were accountable for, never what changed |
| Buried lede | The strongest evidence sitting on page two |
| Flat progression | Every role reads identically, so no growth is visible |
| Unexplained gap | A date range with nothing in it and no framing |
| Archetype mismatch | Evidence that doesn't support the target the person says they want |

For each finding, say what it costs them with this archetype's reader. A
finding with no stated consequence is just criticism.

Pay particular attention to **stack as identity**, because it is the most
common failure in technical CVs and the one people least expect. A line reading
"Senior AI Architect — LangChain, LLM, RAG, 5k users" tells a reader nothing
that distinguishes the person from anyone who has read the documentation. What
distinguishes them is the reasoning: what they built, how, why they chose that
approach over the obvious alternative, what went wrong, and what they would do
differently now. That material is what makes someone read as senior rather than
merely certified — and it is exactly what elicitation is for, so a stack-heavy
CV is a signal to aim the next question batch at decisions rather than systems.
The same pattern appears in non-technical CVs as tool lists, certifications and
methodology acronyms standing in for judgement.

### 5. Update the artifacts, including what comes out

Write new evidence into `evidence-base.md`. Then update `action-ledger.md`.

Every ledger item carries a **type**, because the cost to the user varies wildly
and lumping them together makes the list undoable:

- **Reframe** — wording only, can be done immediately
- **Surface** — the evidence already exists, it is just in the wrong place
- **Quantify** — they need to go and find a number, check an old dashboard, or
  ask a former colleague
- **Acquire** — the evidence does not exist and would have to be earned

That last type is career advice, not CV advice. Keep it visibly separate so it
does not sit in a to-do list looking like an overdue task. It is what falls
naturally out of the "one or two artifacts away" grading, and framed properly it
is a plan rather than a criticism.

Every item also carries a **status**: proposed, applied, rejected, or
superseded. When the user rejects something — they do not want to surface a
particular role, or they disagree that a bullet should lead — record the
rejection *and their reason*, and do not propose it again. Multi-session tools
that re-litigate settled decisions get abandoned, and the reason usually matters
more than the decision.

**Then run the eviction pass, every single session, without being asked.** This
process only adds: each session elicits more evidence and surfaces more
recommendations. Left unchecked the honest end state is a six-page CV that is
comprehensive and useless. So for anything newly promoted into the top third,
name what it displaces. Ask what is now corroboration rather than pitch and can
move down or out. Be as willing to say "this entire section costs you space and
buys you nothing" as to say "here's something missing."

Every other CV tool only adds. This is the part that makes the document better
rather than merely longer.

### 6. Draft the top third

Since the top third does nearly all the door-opening work, draft it concretely
rather than describing it in the abstract: a headline, a positioning line, and
three or four proof bullets aimed at the chosen archetype. Everything below it
on the real CV is corroboration for a reader who is already interested.

Draw only on confirmed evidence base entries. If the strongest available framing
depends on something the person hedged, draft it with the hedge visible and flag
what they would need to check to firm it up.

Do not rewrite the whole CV. That is a separate job, and doing it here means two
tools fighting over the same artifact.

The rewrite belongs to **`cv-and-human`**, once the person has a target role or a
job description in hand. Hand over by telling them to bring the evidence base to
that skill — it is the raw material a tailoring pass needs and cannot generate
for itself. The order matters: tailoring a CV whose best evidence is still
missing produces a well-optimised document making a weaker case than the person
can support.

### 7. Hand back

End every session by writing both files out and delivering them, along with a
short note on what was covered and the two or three highest-value things to
tackle next time. The user keeps these files and re-attaches them next session —
that is the only way state survives. Say so explicitly, because a user who loses
the files loses everything.

## Length and shape

Deploy this when the question comes up, rather than volunteering it unprompted.

The one-page rule is largely folklore. The best controlled evidence — a paired
study where recruiters reviewed one-page and two-page versions of identical
candidates — found two-page versions chosen roughly 2.3 times more often, with
the preference *increasing* with seniority. The reason follows from the two
readers: reader one is unaffected by length because they never get past the top
third, and reader two actively wants more.

So the working guidance:

- Two pages is a safe default for anyone mid-career or beyond
- Three is defensible for genuinely deep histories, provided it is *structured*
  for navigation rather than merely long
- One page is a real constraint only for early-career candidates
- Freelance and contract CVs legitimately run longer, because the project list
  *is* the evidence — many short engagements each needing client context, stack
  and outcome. The pattern that works is a tight two-page core plus a project
  annex, so reader one is never made to wade through fifteen engagements to find
  the pitch
- Freelance and permanent are different pitches, not the same CV reformatted.
  Freelance buys de-risked delivery: can this person land in an unfamiliar
  environment, be useful within a week, and leave something maintainable behind.
  Permanent buys trajectory, judgement and fit

Conventions vary by country — page norms, whether photos and personal details
are expected, how much detail is standard. Where the user's target market is
known and differs from the CV's current style, flag it; where it is unknown and
looks like it might matter, ask rather than assume.

## Sensitive territory

Elicitation wanders into difficult ground: redundancy, a bad exit, burnout,
illness, caring responsibilities, discrimination. Gaps are exactly the thing a
screener flags, so they cannot be ignored — but how they are handled determines
whether the person keeps talking.

Ask once, neutrally, and make it easy to decline. If they decline, accept it
immediately and without follow-up, then treat it as a positioning problem to
solve rather than a fact to extract — there is almost always a way to frame a
gap that neither lies nor invites the question.

Never record sensitive personal detail in the evidence base beyond what is
needed for positioning. The file is a career record, not a medical or personal
history, and the user may share it.

## Anti-fabrication

Everything in the evidence base traces to something the person said. Never
invent a number, infer a scale from context, or upgrade "a few" into "several
dozen." When a claim would be much stronger with a figure the person does not
have, that is a **quantify** ledger item, not licence to estimate one.

Tag every entry `confirmed`, `approximate` or `unverified`, and never let an
`unverified` entry appear in drafted CV prose without the uncertainty visible.
The test is simple: could they defend this sentence, under follow-up questions,
in a forty-five minute interview? If not, it does not go on the page.

### Counting the document is a claim too

The same discipline governs numbers you produce *about the CV itself* — how many
certifications it lists, how many technologies appear in the skills block, how
many months a gap runs, how many bullets lack an outcome. These feel like
observations rather than claims, which is exactly why they slip: nobody
double-checks a number they think they just read off the page.

So either **count it and be right, or hedge it visibly**. "Sixteen
certifications" requires having counted sixteen. "Roughly ninety technologies"
is fine because the hedge is doing honest work. What is not fine is a confident
figure arrived at by estimation, because the person will repeat it — and a gap
you describe as eight months when it is seven is a number they may well say out
loud to a recruiter who can subtract.

Gap arithmetic is the one worth slowing down for, since it is the number a
screener is most likely to check: count the **blank months between** the roles,
not the span from one date to the other. A role ending July 2023 and the next
starting March 2024 leaves August to February — seven months, not eight.

## Reference files

- `references/archetypes.md` — how to derive role archetypes from evidence
  rather than titles, with worked technical and non-technical examples
- `references/question-bank.md` — elicitation questions organised by what they
  dislodge, plus scale, baseline and durability probes
- `assets/evidence-base-template.md` — structure and entry schema
- `assets/action-ledger-template.md` — structure, types and statuses
