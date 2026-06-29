---
name: cv-and-human
description: >
  Tailor and polish a CV/resume to maximise its score in applicant tracking systems
  (ATS), covering both keyword/JD-matching screeners and modern LLM-rubric scorers
  (which often take no job description at all). Use this whenever the user wants to
  optimise, tailor, rewrite, or "ATS-proof" a CV or resume, asks why their resume
  isn't getting through screening, wants a keyword/gap analysis against a job
  description, wants to remove AI-generated texture from a CV, or wants to check
  whether a CV parses cleanly. Trigger even if the user only supplies a CV (with or
  without a job description), or asks to "make my resume match this job" or "pass
  the ATS". Do NOT use for writing a CV from a blank page with no material to work
  from, or for generic career advice unrelated to a document.
---

# CV and Human

Polish a CV so it clears automated screening while staying truthful. The strategy
is grounded in the **source code** of a real LLM screener (read directly, not from
commentary): ATS scoring splits into a **knowable, controllable surface** —
parseability, literal keyword coverage, project links, real open-source framing,
the explicit bonus triggers — and a **noisy LLM-judgment layer** you can't pin
down (whether your projects are "worth" 18 vs 24 points swings run to run). Lock
down the controllable surface; feed the noisy layer the strongest *true* material;
never promise a score. Note that some screeners take **no job description at all**
and grade against a fixed rubric — so this skill handles both JD-matching and
JD-less tools. See `references/ats-mechanics.md`.

## Core principles (read before editing anything)

1. **Never fabricate.** Do not invent skills, titles, dates, employers, metrics,
   or open-source work. If a JD requirement is genuinely absent from the
   candidate's background, surface it as a gap for them to address — do not paper
   over it. Tailoring means truthful reframing and surfacing, not lying. This is
   both an integrity line and a practical one: fabrications get caught at
   interview and burn the candidate.
2. **Win the deterministic surface first.** Exact skill/keyword coverage and clean
   parseability are checklist logic — they score consistently. This is where
   effort reliably moves the needle.
3. **Strengthen, don't promise, the noisy surface.** Project/experience judgment
   scores swing run-to-run. Give those sections quantified, JD-aligned, truthful
   detail and then stop optimising — chasing a target number there is chasing
   noise.
4. **Match the candidate's real language to the JD's language.** If they did the
   thing the JD asks for but called it something else, use the JD's term (only
   when it's genuinely the same thing).
5. **Stay in the candidate's voice and seniority.** Don't inflate a mid-level CV
   into principal-level claims.

## Workflow

### Step 1 — Gather inputs and identify the ATS family

Get the **CV** and, if one exists, the **target job description**. There are two
ATS families (see `references/ats-mechanics.md`), and which one you're optimising
for changes the work:

- **Family A — keyword / JD-matching ATS** (Workday, Taleo, Greenhouse). Needs the
  JD; the job is literal keyword coverage + clean parsing.
- **Family B — LLM-rubric scorer** (e.g. HackerRank's `hiring-agent`). Takes **no
  JD at all** — it scores against a fixed internal rubric. Here you optimise the
  rubric levers, which are JD-independent.

So: if there's a JD, do the JD-matching work (Steps 3–4). If there's no JD, **don't
refuse** — skip to the Family-B rubric levers in Step 5. If you don't know which
family the employer uses, optimise both; they don't conflict.

Always ask for the candidate's **GitHub, portfolio, and blog links**: Family-B
tools scrape GitHub, weight open source at 35%, and award explicit bonus points for
a portfolio URL, LinkedIn, and a technical blog. Relevant public work is worth
surfacing prominently.

### Step 2 — Read the CV

Read the CV file using the appropriate tool:
- **.docx** → use the `docx` skill to extract content.
- **.pdf** → use the `pdf` / `pdf-reading` skill to extract text.
- **.txt / .md / pasted text** → read directly.

**Boundary — extraction is the orchestrator's job, not the skill's.** Turning a
PDF/DOCX into malleable text happens **here, upstream, with a deterministic tool**
(the agent reading it, pymupdf, markitdown) **before** any reasoning step runs. The
skill and its sub-agents (tailor, de-slop, red-team) assume text *in* — they must
never run an LLM-based PDF/DOCX extractor internally. Keeping conversion upstream
and deterministic makes it cheap, repeatable, and inspectable; burying a
non-deterministic extractor inside the skill would make every downstream result vary
on parsing noise. (The optional measured-ATS lens is the one place an *external*
scorer like `hiring-agent` does its own internal parsing — but that engine is the
thing under test, not this skill; see `references/red-team.md`.)

While reading, run the **parseability check** in
`references/parseability-checklist.md`. Parsing happens upstream of all scoring —
a multi-column layout, text-in-images, or tables that scramble on extraction can
sink a strong candidate before grading even starts. Note every parseability risk.

**Auto-detect the CV's regional format here** — don't ask the candidate. If the
document is a German/DACH Lebenslauf (heading "Lebenslauf", German section
headings, a personal-data block with Geburtsdatum/Nationalität, a top-right photo
or signature line, MM.YYYY dates), load `references/regional-formats.md` and apply
its overrides. This is important: the Anglo defaults would strip the photo, date of
birth, nationality, and signature a German recruiter expects. Detect first, then
apply the right layer; when no regional format is detected, the Anglo defaults
stand.

### Step 3 — Analyse the job description

Extract and list, in this order:
- **Hard requirements** (must-haves: named technologies, years, certifications,
  degrees, clearances).
- **Preferred/nice-to-haves.**
- **Exact keyword phrases** as written in the JD (tools, methodologies, role
  nouns). Capture the JD's *exact* surface forms — "CI/CD", "Kubernetes",
  "Terraform", "SRE" — because checklist matching is literal.
- **Implied themes** (e.g. "owns reliability" → on-call, SLOs, incident response).

### Step 4 — Gap analysis

Produce the gap table (template below). For every JD requirement and keyword,
classify against the CV as:
- **Present & strong** — clearly evidenced.
- **Present but weak/buried** — there, but underexposed or in non-JD language →
  reframe/surface.
- **Absent** — not in the CV. If the candidate actually has it, add it truthfully;
  if they don't, flag it as a real gap (and, where reasonable, suggest how they
  might close or bridge it). Never invent it.

### Step 5 — Rewrite

Apply, in priority order:
1. **Fix parseability** — convert to a single-column, standard-heading,
   text-based layout. This is non-negotiable; nothing else matters if the parser
   chokes.
2. **Skills / technical section** — ensure every JD hard-requirement skill the
   candidate genuinely has appears verbatim in JD surface form. This is the
   highest-consistency scoring area; make coverage complete.
3. **Experience bullets** — reframe in JD language; lead with quantified outcomes
   (what changed, by how much); mirror the JD's themes. Keep them true.
   **Align job titles** to the JD's title language where it's truthfully the same
   role — both ATS and recruiters filter on title, so "Platform Engineer" beats a
   creative title like "Cloud Ninja." Never inflate the level, only normalise the
   wording.
4. **Projects / open source** — surface relevant public work, link it, describe
   architecture and real-world deployment in concrete terms. This is heavily
   weighted in LLM screeners but also the noisiest — give it strong true material
   and move on.
5. **Standard sections & headings** — use conventional headings the parser
   expects (`Experience`, `Education`, `Skills`, `Projects`) — see checklist.

**Family-B rubric levers** (apply whenever a Family-B / LLM-rubric tool is in play,
or when the ATS family is unknown — all JD-independent, all truthful-only; full
detail and point values in `references/ats-mechanics.md`):
- **Put a working link on every project**, lead with live demos. Linkless projects
  are explicitly penalised; live demos are explicitly rewarded.
- **Don't mislabel solo repos as "open source."** Surface genuine contributions to
  others'/multi-contributor projects; solo repos are capped low and deducted.
- **Drop or recharacterise tutorial-grade projects** (todo/calculator/CRUD/weather
  apps etc. are named for zero scores and deductions, including generic names).
- **Claim the real bonus points:** portfolio URL, LinkedIn, technical blog, GSoC,
  founder/early-stage roles — include the links and surface the experience.
- **Foreground rewarded complexity signals where true:** auth+databases, real-time,
  ML/AI, microservices, mobile-native, advanced algorithms, real user adoption.

**The summary/profile line** — borrow `hook-and-human`'s one applicable principle:
lead with a real specific, not a generic opener. "Cloud engineer who cut a fintech's
AWS spend 38% and owns their Terraform monorepo" beats "Results-driven professional
with a proven track record." Apply this *only* to the summary line, with a real
number; do not import hooks, CTAs, or persuasion framing into the body.

### Step 5.5 — De-slop (remove AI-generated texture)

After rewriting, strip AI-written texture from the prose — both human reviewers and
LLM screeners increasingly down-rank it, and an AI-textured CV reads as
undifferentiated. Follow `references/deslop-cv.md`, which is **self-contained**: it
carries its own CV-tuned AI-pattern list, so no other skill is required. If
`clear-and-human` happens to be installed you may use its fuller pattern list as an
optional extension, but never depend on it.

The one rule that makes this safe: **the keyword guard.** The AI-vocabulary cut-list
(leverage, optimise, scalable, robust, agile, etc.) overlaps with real JD keywords
and real technology names. Keep a flagged word when it is *referential* — a JD
keyword, or the accurate name of a tech/method/metric the candidate used — and cut
it only when it is *empty* booster or connective tissue. Do not strip the keywords
the rewrite deliberately added. After de-slopping, re-confirm skills coverage.

Note also that a CV is its own channel: do **not** apply clear-and-human's
blog/linkedin habit of adding first person, contractions, or "voice". Keep
fragment, action-verb-led bullets. Details in the reference.

### Step 6 — Deliver

Produce three things:
1. **The tailored CV** as a clean file. Default to the same format the candidate
   supplied (use the `docx` skill for Word output). If they gave plain text,
   return Markdown unless they ask otherwise.
2. **The gap report** (template below) — what you changed, what's still a real
   gap, and what the candidate must decide on.
3. **The honesty note** — a short, plain statement that ATS scores (especially
   LLM-based ones) are partly non-deterministic, so this maximises their odds on
   the parts that are controllable rather than guaranteeing a pass.

See `references/worked-example.md` for a full before/after (fake data) showing the
de-slop, the keyword guard, the metric-placeholder discipline, and filled gap-report
and red-team fragments. Imitate its pattern.

## Beyond the CV: flag what it can't fix

The CV is not the only gate. Many enterprise ATS (e.g. Workday, Greenhouse) hard-
filter on **application-form knockout questions** — work authorisation, years of
experience, willingness to relocate, salary expectations, a required degree — that
are scored separately from the CV and can auto-reject regardless of how good it is.
This skill can't change those, but it should **flag** them so the candidate isn't
blindsided perfecting a CV that a form answer already eliminated. Name the likely
knockouts for the role and tell the candidate to answer them deliberately.

## Red-team pass (optional)

If the user wants their CV stress-tested, run the **CV Red-Team pass** in
`references/red-team.md`. It follows the council pattern (evaluator–optimizer, same
idiom as `council-skills`): the red team arrives last, after a working tailored CV
exists; it **pushes back, it doesn't reject**; and it **finds weaknesses without
rewriting** — every finding is a flag the candidate acts on. Lenses: ATS (the
machine), Recruiter (the human scan), Slop (AI texture), and Truth (the
fabrication-floor enforcer, with veto over fixes that would require inventing
anything). The split resolves the fabrication tension cleanly: the red team finds
gaps, the tailor fixes only the truthful ones, and the rest become candidate
decisions. If a real scorer is available, the ATS lens can be quantitative — but
only against a distribution (N≥5 runs), via `scripts/ats_adversarial_loop.py`. Off
unless asked for.

## Gap report template

ALWAYS use this structure for the report:

```
# ATS Tailoring Report — [Role] @ [Company]

## Parseability
[Pass/risks found and fixed]

## Coverage against job description
| JD requirement / keyword | Status | Action taken |
|---|---|---|
| <requirement> | Present & strong / Weak / Absent | <reframed / surfaced / added (truthful) / flagged as gap> |

## Real gaps (candidate decision needed)
- <requirement not in background> — [how to bridge, or leave as-is]

## What I changed
- <bullet list of edits>

## Honesty note
[Short statement on determinism limits — see references/ats-mechanics.md]
```

## What this skill will NOT do

- Invent qualifications, employers, dates, or metrics (including *soft*
  fabrications: derived numbers, aggregate-time claims, vague-outcome boosters).
- Keyword-stuff with skills the candidate doesn't have (modern parsers and humans
  both catch it, and white-text/hidden-keyword tricks get CVs binned).
- Promise a specific ATS score or a guaranteed pass.
- Refuse when there's no job description — JD-less LLM-rubric tools are supported
  via the Family-B rubric levers.

## Reference files

- `references/ats-mechanics.md` — How keyword and LLM-rubric ATS pipelines actually
  work (grounded in `hiring-agent` source), the two ATS families, what scores
  consistently vs what's noise, and the verified rubric levers. Read when the user
  asks *why* a change helps or which family they're facing.
- `references/parseability-checklist.md` — Formatting rules for a cleanly-parseable
  CV. Read during Step 2 and apply during Step 5.
- `references/regional-formats.md` — Auto-detection and overrides for non-Anglo CV
  formats (German/DACH Lebenslauf and others), so the skill keeps the photo, DOB,
  nationality, and signature those markets expect instead of Anglicising them. Read
  during Step 2 whenever a regional format is detected.
- `references/deslop-cv.md` — Self-contained CV de-slop engine: the embedded
  AI-pattern list, the keyword guard, the CV-channel rewrite rules, and the
  soft-fabrication floor. Read during Step 5.5.
- `references/red-team.md` — Optional council-style red-team pass (ATS / Recruiter /
  Slop / Truth lenses) that pushes back without rejecting and finds weaknesses
  without rewriting. Read only for the red-team pass.
- `references/measured-scorer.md` — Optional external-tool runbook for the *measured*
  ATS lens: wiring `scripts/ats_adversarial_loop.py` to a real `hiring-agent`, the
  model backends (Ollama / OpenAI-compatible: gpt-5-mini, Haiku), and the
  markdown-first extraction path. Read only if you actually run the measured loop.
- `references/worked-example.md` — A full before/after on fake data demonstrating
  the de-slop, keyword guard, metric-placeholder discipline, and filled report/
  red-team fragments. Read when you need a concrete pattern to imitate.
- `scripts/ats_adversarial_loop.py` — Scoring/stats harness for the red-team's
  measured ATS lens (`selftest` runs without a model backend).
