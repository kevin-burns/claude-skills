# cv-and-human

> Tailor a CV/resume — or a LinkedIn profile — to clear automated screening while staying truthful and in your own voice: ATS keyword/JD matching, LLM-rubric scorers, and LinkedIn Recruiter search. Part of [claude-skills](../README.md).

## What it does

**CV / resume tailoring** (the original capability). Given a CV and, optionally, a job
description, it identifies which ATS family you're up against — keyword/JD-matching
(Workday, Taleo, Greenhouse) or an LLM-rubric scorer that takes no JD at all — and
optimises for the one in play (or both, if you don't know). It checks parseability
(single-column, standard headings, no table/image traps), runs a gap analysis against
the JD, rewrites skills and experience bullets in JD language with quantified outcomes,
surfaces open-source/portfolio work the way LLM screeners weight it, strips AI-written
texture (`references/deslop-cv.md`), and auto-detects and applies non-Anglo formats
(e.g. a German/DACH Lebenslauf) instead of stripping fields those markets expect. It
delivers the tailored CV, a gap report, and an honesty note that ATS scoring — especially
the LLM-based kind — is partly non-deterministic. An optional red-team pass (ATS /
Recruiter / Slop / Truth lenses) pushes back on a finished draft without rewriting it,
and an optional measured-ATS harness (`scripts/ats_adversarial_loop.py`) scores a draft
against a real LLM screener across repeated runs to get a distribution rather than one
noisy number.

**LinkedIn profile mode** (new). The same "lock down the controllable surface, never
promise the noisy layer" strategy applied to a LinkedIn profile instead of a CV. This
mode is **job-seeker-focused only** — there is no founder/consultant lens; it does not
cover personal-brand demand generation. It runs a one-question positioning pass (who do
you help, what changes for them, what proves it), then rewrites headline, About, and
skills within LinkedIn's field limits, applying a keyword-placement rule: target-role
keywords may land in skills, experience, and the tail of About, but never drive the
headline or the first ~200 characters of About (the part almost everyone actually
reads). It cross-checks title and date consistency against your CV when both exist, and
flags disagreements rather than silently reconciling them. `scripts/li_profile_check.py`
enforces the character limits and front-load/coverage checks deterministically, counting
UTF-16 code units to match LinkedIn's own field counter.

## How to use it well

- **Supply the job description when you have one** — it drives the keyword-matching
  work. Without one, the skill doesn't refuse; it switches to the JD-independent
  LLM-rubric levers instead.
- **Hand over GitHub, portfolio, and blog links** — LLM screeners weight open source and
  award explicit bonus points for these, so they're worth surfacing even if you don't
  think to mention them.
- **For LinkedIn: give a target role and paste whatever profile text you have**, however
  ragged — a partial paste with broken line wraps and stray UI chrome is the normal
  case, not a blocker. If you don't have a profile yet, hand over your CV instead; it
  cold-starts from that.
- **Answer the one positioning question with a specific, not a job title.** "I help
  fintech teams cut deploy risk — led three zero-downtime migrations" produces a much
  better headline than "Senior Software Engineer." If you only have a title, it'll show
  you the shape of a better answer rather than asking again.
- **If both a CV and a profile exist, supply both** so the consistency check can catch a
  title or date that quietly disagrees between them.
- **Ask for the red-team pass or the measured ATS loop** if you want pushback or a
  quantified score distribution; both are off by default.

## What it does NOT do

The boundary is the point — this is what makes the output trustworthy rather than just
optimistic:

- **Never invents qualifications, metrics, skills, or endorsements.** Everything in a
  draft traces back to something you supplied. Anything you claim but can't back up
  becomes a `[VALIDATE]` placeholder for you to resolve, or a named gap — never a quiet
  addition.
- **Never keyword-stuffs.** No hidden text, no skills you don't have, no white-text
  tricks — modern parsers and humans both catch it, and it gets CVs and profiles binned.
- **Never promises an ATS score or a LinkedIn Recruiter search ranking.** Both are
  partly non-deterministic and, for Recruiter search, not public at all. This maximises
  the controllable surface and says so in every report — it does not guarantee a pass or
  a ranking.
- **No LinkedIn engagement automation of any kind** — it will not connect, post, comment,
  message, follow, or apply on your behalf. It only ever produces text for you to paste
  in yourself.
- **No scraping or fetching linkedin.com.** The LinkedIn mode works only from text you
  paste or export, never from a live fetch of the site.
- **Does not write LinkedIn posts.** A post is persuasive or informational feed content,
  a different job from optimising a career document. Route persuasive post copy to
  `hook-and-human` and neutral/informational post copy to `clear-and-human`.

**A note on the LinkedIn field limits:** LinkedIn publishes no consolidated limits
table. The numbers this mode targets (headline 220 chars, About 2,600, skills 80 chars
each, etc.) are third-party-sourced and cross-checked across two independent sources,
and may drift if LinkedIn changes its UI. `scripts/li_profile_check.py` is the actual
enforcement point — a drift is a one-line fix in that script's `LIMITS` block, not a
hunt through prose.

## Maintenance note

If the `description` frontmatter of `cv-and-human`, `clear-and-human`, or
`hook-and-human` ever changes, re-run the routing harness before merging — job-seeker
LinkedIn requests, neutral writing, and persuasive writing overlap enough in surface
language that a description edit to any one of the three can silently steal or lose
triggers from the others:

```bash
cd docs/superpowers/specs/linkedin-router-harness && uv run --no-project python v2_check.py 3
```

Must score 54/54. This note lives here, next to the skill it gates, rather than only in
the harness's own spec, because a spec document nobody reads is not a control. The
harness directory itself is gitignored and local-only — it is not shipped as tracked
content in this repo.

## Requirements

**CV tailoring** — no tooling for the core workflow (review, tailoring, de-slop). PDF/DOCX
extraction happens upstream via the `pdf`/`pdf-reading` and `docx` skills, never inside
this skill. The optional red-team's measured ATS lens uses `scripts/ats_adversarial_loop.py`
— `uv`/Python 3 (`selftest` runs without a model backend).

**LinkedIn profile mode** — `uv` to run the checker, from inside the `cv-and-human`
directory:

```bash
uv run scripts/li_profile_check.py profile.json
```
