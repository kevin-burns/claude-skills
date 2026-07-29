# cv-evidence-base

> Interrogates a CV to recover the evidence that never made it onto the page, and grades which roles you are genuinely credible for — including the ones you are not. Part of [claude-skills](../README.md).

## What it does

Most CVs are not weak because the wording is bad. They are weak because the person's best
evidence never made it onto the page — they omit what they found easy, describe
responsibilities rather than outcomes, and file a whole career under a job title the market
has quietly moved past. None of that is fixable by rewriting sentences.

So this skill does not polish prose. It runs a session that:

**Reflects back what the page transmits** — what a reader who has never met you concludes
from the CV as it stands, in two or three sentences, before anything else. This is usually
the first useful shock and it costs nothing.

**Grades role archetypes derived from evidence, not titles.** Three buckets: *credible
now* (the evidence exists, it's just buried), *one or two artifacts away* (naming the
specific missing thing and where to go looking for it), and *not credible* — with at least
one exclusion named every time. That third bucket is the discipline that makes the other
two mean anything; a grading with no exclusions is flattery wearing a lab coat.

**Elicits through oblique questions.** Direct questions ("what were your key
achievements?") return the bullets already on the page, because they ask you to
self-assess and you already did that when you wrote it. Asking about difficulty,
causation, counterfactuals and other people's perceptions bypasses the modesty filter that
suppressed the material in the first place. Questions come in batches of three to five,
two or three batches per session, because a forty-question grilling gets abandoned at
question nine.

**Screens cold**, against a named failure table — unscaled claims, baseline-free outcomes,
orphan keywords, stack-as-identity, scope/verb mismatch, buried lede, flat progression —
with what each one costs you, because a finding with no stated consequence is just
criticism.

**Runs an eviction pass every session, unasked.** This process only ever adds; without
eviction the honest end state is a six-page CV that is comprehensive and useless. For
anything newly promoted into the top third, it names what that displaces.

### The two artifacts

Every session maintains two files, kept separate because facts and recommendations have
different lifespans:

- **`evidence-base.md`** — durable, archetype-neutral, append-mostly. "I cut CI build
  times from 40 to 9 minutes across 30 repos" is true regardless of what job you're
  chasing. Grows across sessions, richer than any CV could be, never sent to an employer.
- **`action-ledger.md`** — derived, archetype-specific, perishable. "Lead with the
  build-time figure, move certifications to the bottom" expires when the target changes.
  Regenerate freely. Ends with a drafted top third — headline, positioning line, proof
  bullets — which is the material a rewrite starts from.

You keep both files and re-attach them next session. That is the only way state survives.

## How to use it well

- **Come without a target role.** This skill is for when you don't know what you're aiming
  at, or suspect you're aiming at the wrong thing. If you already have a job description,
  you want `cv-and-human`.
- **Answer the oblique questions properly** — they're the engine. The Kiro-style question
  ("which tooling, who used it, what did they do before it existed?") is where the buried
  material actually comes from.
- **Hedge out loud.** "Maybe 30%?" is more useful than a confident guess: hedges are
  preserved as `approximate` or `unverified` rather than smoothed into prose you'd then
  have to defend in an interview.
- **Expect to be told what you're not credible for.** If you push back on the exclusion
  and get it withdrawn, you've lost the most valuable thing in the session.
- **Keep the two files.** Lose them and the next session starts from zero.
- **Then go to `cv-and-human`** once you have a target role, bringing the evidence base
  with you.

## What it does NOT do

- **Does not rewrite or reformat your CV.** It drafts the top third and stops. Full
  rewriting, ATS keyword tailoring, parseability fixes and de-slopping belong to
  `cv-and-human` — two tools fighting over one artifact serves nobody.
- **Never invents a number, a scale, or an achievement.** Everything in the evidence base
  traces to something you said. When a claim would be much stronger with a figure you
  don't have, that becomes a **quantify** action — go find it — not licence to estimate
  one. Every entry is tagged `confirmed`, `approximate` or `unverified`, and unverified
  material never reaches drafted prose with the uncertainty hidden.
- **Does not promise callbacks or interviews.** It improves what the page transmits; it
  cannot control who reads it.
- **Does not record sensitive personal detail** beyond what positioning requires. Gaps,
  health, caring responsibilities and exits are asked about once, neutrally, with an easy
  decline that is accepted without follow-up — the evidence base is a career record, not a
  medical history, and you may share it.
- **Does not do LinkedIn profiles, posts, or cover letters.** Profiles are `cv-and-human`;
  posts are `hook-and-human` (persuasive) or `clear-and-human` (neutral).

## How it pairs with `cv-and-human`

They are sequential tools driven by you, not an automated pipeline — nothing moves the
evidence base between them except you attaching it.

| | `cv-evidence-base` | `cv-and-human` |
|---|---|---|
| **Use when** | no target role; open question about yourself | a job description or named target role |
| **Asks you questions** | yes — that's the engine | only for links and facts |
| **Output** | evidence base + action ledger + drafted top third | tailored CV / LinkedIn profile + gap report |
| **Failure it prevents** | tailoring a document whose best evidence is missing | a truthful CV the parser mangles |

The order matters. Tailoring thin material doesn't make it less thin — it produces a
well-optimised document arguing a weaker case than you can actually support.

## Measured effect

Against the three bundled evals (`evals/`), run once each with and without the skill:

| eval | with skill | without skill |
|---|---|---|
| technical CV, cold open | 100% (10/10) | 40% |
| non-technical CV, cold open | 100% | 36% |
| continuation session with prior state | 100% | 90% |

Mean pass-rate delta **+0.45**. Two caveats on reading that: each cell ran **once**, so
there is no variance data and "stddev 0" in the benchmark reflects spread across evals
rather than across repetitions; and token capture failed on four of six runs, so the token
figures in that benchmark are unusable.

The instructive result is what the *baseline* did. Asked "am I positioned right, what am I
missing?", it went straight to restructuring the CV — and in doing so invented a
certification count and produced an umbrella date range that silently absorbed a
seven-month gap into a continuous engagement. Nobody invented an achievement; the
reformatting itself manufactured a claim the source document could not support. That is
the failure mode this skill exists upstream of.

## Maintenance note

`cv-evidence-base` and `cv-and-human` are routed apart by a deliberate fork: **a named
document operation** (tailor, ATS-proof, parse-check, de-slop, a LinkedIn field) goes to
`cv-and-human`; **an open positioning question** with no target role goes here. Their two
descriptions are measured artifacts. If either changes, re-run the routing harness — the
surface language overlaps enough that an edit to one can silently steal triggers from the
other, and from `clear-and-human` and `hook-and-human` besides:

```bash
uv run --no-project python docs/superpowers/specs/linkedin-router-harness/v3_check.py
```

`tests/test_skill_contract.py` guards the same invariants in under a second at zero API
cost — run that first. The harness directory is gitignored and local-only.

## Requirements

No tooling. PDF/DOCX extraction happens upstream via the `pdf`/`pdf-reading` and `docx`
skills, never inside this skill.
