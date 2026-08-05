# Deriving role archetypes

## Why not a fixed list

A hardcoded taxonomy of job titles ages badly and only ever covers one industry.
More importantly, it recreates the exact problem this skill exists to solve:
people are pigeonholed by titles, and handing them another list of titles just
moves them from one box to another.

So derive archetypes from evidence. Read what the person has actually done —
the artifacts they produced, the decisions they owned, the people and systems
they moved — and name the market categories that fit that shape. The examples
below are patterns to reason from, not a menu to pick from.

## The method

1. **Strip the titles.** Ignore what each role was called. List what the person
   demonstrably did, owned and changed.
2. **Cluster by the shape of the work**, not the domain. "Made a messy thing
   legible to other people" is a shape. "Worked in insurance" is not.
3. **Ask what market currently buys that shape**, including categories that
   didn't exist when they started. This is where pigeonholing breaks — a role
   description from 2018 may map onto a category that only got a name in 2023.
4. **Grade honestly**, including exclusions.

## Strip the labels from the prose, not just from the titles

Step 1 says strip the titles. The harder half is stripping the title-adjacent
phrases *inside the bullets*, and skipping it produced the worst failure this
skill has had in the field.

Running on a real CV (2026-07-29) it graded **solution architect** as NOT
CREDIBLE on the strength of a single line — "Engaged as the senior engineer on
complex builds, partnering with senior architects on the overall solution
design" — reasoning that this put the person next to the architect rather than
in the chair. The same document contained six bullets across four roles
demonstrating design ownership: *Architected and built* a multi-cluster cost and
usage reporting solution; *Designed* unified CI/CD pipeline automation;
*Designed* cloud security-hardening reporting; *produced an architecture
blueprint* for operational monitoring; *Redesigned* the backup and DR strategy;
*Led the design and implementation of* a serverless data pipeline. One of the
job titles read, literally, "AWS Architect". The candidate had to push back with
evidence that was already on the page.

The mechanism is worth naming, because it will recur: **a hedging phrase that
NAMES the archetype is lexically closer to it than a bullet that DEMONSTRATES it
without naming it.** Retrieval by surface similarity beats retrieval by
evidence. Worse, the constructions that produce those phrases — *Support
framing* and *Downgrade by modesty*, both listed below as patterns to correct —
are exactly what gets mistaken for a negative finding. Grading on them commits
the pigeonholing this skill exists to undo, and does it in the skill's own
confident register, which makes the error look principled.

So the rule, and it cuts both ways:

**A phrase that names an archetype is not evidence about that archetype, in either direction.**
"Partnering with senior architects" is not evidence against design ownership,
exactly as "Solution Architect" in a title is not evidence for it.
Both are labels. Grade on what was built, owned, decided or changed.

### Enumerate before you assign a bucket

Before writing any grading, list the demonstrated work for that archetype across
the *whole* document — every bullet showing the shape, wherever it sits. Assign
the bucket from that list.

This makes the failure structurally hard rather than merely discouraged, and it
gives a usable self-check: **if a not-credible grading rests on one line, it is
wrong.** Evidence for or against an archetype is a pattern across roles, not a
sentence. A defensible exclusion reads "nothing in this document shows X" — not
"this line suggests otherwise."

The asymmetry is deliberate. A wrongly generous grading gets corrected at
interview, uncomfortably but recoverably. A wrongly harsh one tells someone
their real experience does not count, and they may believe it — so where the
enumeration is genuinely mixed, that is *one or two artifacts away*, and you say
which artifact. It is not *not credible*.

## The three buckets

**Credible now** — the evidence exists and would survive an interview. The
problem is framing, ordering or visibility, not substance. Say which specific
evidence supports it and where it currently sits on the page.

**One or two artifacts away** — a reader would want one specific thing they
cannot currently see. Name that thing exactly, and say where to go looking: an
old project, a colleague who would remember, a system still running somewhere.
Often the artifact does exist and the person forgot it counted.

**Not credible** — the evidence isn't there and no amount of reframing creates
it. Name at least one of these every time. A grading with no exclusions tells
the person nothing, because if everything is possible then nothing is
information. Say what specifically is missing, so it reads as a map rather than
a door closing.

## Worked example — technical

A candidate with eight years of titles reading "Systems Administrator" then
"DevOps Engineer". Stripped of titles, the evidence shows: built an internal
deployment tool other teams adopted; wrote the onboarding runbook; ran the
migration off a legacy platform; is the person people ask before shipping.

- **Platform engineering — credible now.** Building tools other teams consume is
  the defining shape, and they have done it twice. It is currently invisible
  because the CV describes the tool as "automation scripts" under a maintenance
  role.
- **SRE / reliability — one or two artifacts away.** They have operated systems
  under pressure but nothing evidences reliability *as an owned outcome*. Worth
  checking whether they held an error budget, ran postmortems, or carried a
  pager against a target. If any of that exists, this bucket moves up.
- **MLOps — not credible.** No model lifecycle work, no experiment tracking, no
  serving infrastructure. The adjacency is real, the evidence is not. Closing
  this means one substantive project, not a rewrite.

Note the reasoning: the candidate's own label ("DevOps") is the least
informative thing in the file, and their strongest category is one they never
claimed.

## Worked example — non-technical

A candidate whose titles read "Office Manager" then "Operations Coordinator" at
a mid-sized firm. Stripped of titles: renegotiated three supplier contracts;
built the induction process still in use; is the person who fixed a failing
system rollout when the vendor stalled.

- **Procurement / vendor management — credible now.** Three renegotiations with
  recorded savings is direct evidence. It sits in a bullet list of
  administrative duties where no reader will find it.
- **Operations / business process — one or two artifacts away.** The induction
  process is real evidence of process design; what's missing is scale and
  outcome. Did adoption stick, how many people went through it, did anything
  measurable change.
- **People / HR management — not credible.** Adjacent, frequently assumed, but
  there is no evidence of managing people, performance or employment matters.

The same method, no domain knowledge required beyond knowing what the market
buys. If the market categories for a field are genuinely unfamiliar, say so and
ask the person what roles they see advertised — they usually know their own
market better than they realise, and it is a better source than guessing.

## Common pigeonholing patterns

Worth actively checking for, because they recur:

- **Title lag.** The person's title reflects the job they were hired into years
  ago, not the job they grew into.
- **Category drift.** The work has stayed the same while the market renamed and
  re-valued it around them.
- **Support framing.** They describe themselves as supporting or assisting work
  they substantially did.
- **The invisible specialism.** The thing colleagues always come to them for
  appears nowhere, because it never had a title attached.
- **Downgrade by modesty.** They describe a thing they led as a thing they
  "helped with", especially where the work was collaborative.
