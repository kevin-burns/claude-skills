# ATS mechanics: how screening actually works

This file is grounded in the **source code** of a real LLM-based screener
(HackerRank's open-source `interviewstreet/hiring-agent`), read directly — not in
secondary commentary about it. Where it generalises beyond that one tool, it says
so. The point is to optimise against how these systems actually behave, with the
honest caveat that tools differ and any single tool's output is noisy.

## Two different games — detect which one you're playing

**Family A — classic keyword / JD-matching ATS** (Workday, Taleo, Greenhouse-style
parsing). Parses the CV to text and matches it against a specific job posting's
keywords, titles, years, and filters. Deterministic. Here, **tailoring to the JD**
is the whole game: literal keyword coverage in the JD's surface forms, plus clean
parsing. This is the JD-driven path in SKILL.md.

**Family B — LLM-rubric scorer** (e.g. `hiring-agent`). Parses the CV, makes
several LLM calls to extract structured sections, scrapes a linked GitHub and
optionally a blog, then makes **one LLM call** to grade against a *fixed internal
rubric*. Verified fact: this tool's `evaluate_resume()` takes only the résumé text
— **there is no job description input at all.** So for Family B, "tailor to the JD"
does not apply; you optimise the rubric, which is JD-independent. The levers are
below.

When you don't know which family a given employer uses, optimise both surfaces:
JD-keyword coverage AND the Family-B rubric levers. They don't conflict.

## Determinism: knowable rules, noisy application

Don't call these tools black boxes. In `hiring-agent` the final score is computed
deterministically (`score.py`: sum the four category scores + bonus − deductions,
cap at 120). The *only* non-deterministic part is the single LLM call that emits
the category numbers. So:
- The **rubric is fully knowable** — every rule, weight, and deduction is in the
  prompt templates, reproduced below.
- The **noise** comes from an LLM applying ~30 overlapping numeric rules in one
  pass; it won't do that identically twice (one documented run produced
  27/34/32/34/34/30 on the same input at temperature 0). Lowering temperature does
  not remove it.

Practical reading: optimise the rules you can see; do not chase a target number on
the categories that require fine-grained LLM judgment, because that's the noisy
part.

## The verified rubric (Family B) — weights

- Open Source: 0–35
- Self Projects: 0–30
- Production (work/experience): 0–25
- Technical Skills: 0–10
- Bonus: up to +20 ; Deductions: subtracted ; hard cap 120.

Open source + projects = 65% of the base. Default model gemma3:4b @ temp 0.1.

## The verified levers (Family B) — these are the actionable wins

These are explicit, named rules in the criteria template. They are the highest-
value, most concrete tailoring targets and they're JD-independent. Apply only
where **truthful**.

1. **Put a working link on every project. Live demos especially.**
   - No link: −3 to −5 points *per project*, and 30–50% lower project score.
   - GitHub link but no live demo: −2 to −3 per project.
   - Broken/inactive link: −1 to −2 per project.
   - Working live demo: +10–20% on the project.
   Action: ensure each listed project has a live, working URL or repo link; lead
   with the live demo where one exists.

2. **Do not mislabel personal repos as "open source".** True open source = contributing
   to *other people's* / multi-contributor projects. If all GitHub projects are
   single-contributor (`self_project`), open_source is capped at ≤10 *and* takes a
   3–5 point deduction. Action: surface genuine contributions to others' projects
   (PRs merged, multi-contributor repos, GSoC); don't pad the open-source framing
   with your own solo repos.

3. **Cut or recharacterise tutorial-grade projects.** Named in the rubric for low/zero
   scores and deductions: todo apps, calculators, basic CRUD ("give NO POINTS"),
   weather apps, note/recipe apps, NLTK/scikit sentiment analysis, social-media
   clones. Generic names ("Calculator", "Todo App") cost −1 each. Action: drop toy
   projects, or if a project is genuinely more than it sounds, name it specifically
   and foreground the complex part.

4. **Claim the bonus points that exist** (only if true): portfolio website URL +2,
   LinkedIn +1, technical blog +1–3, GSoC +5, founder/co-founder +3–5, early-stage
   engineer +2–3. Action: include portfolio + LinkedIn + blog links in the header;
   surface any of these real experiences.

5. **Foreground the complexity signals the rubric rewards** where real: auth +
   databases, real-time systems, ML/AI, microservices, mobile-native features,
   advanced algorithms/data structures, and genuine user adoption.

## Determinism caveats and limits (use in every report's honesty note)

- Family B output is partly non-deterministic; the same CV can clear or miss a
  cutoff on consecutive runs purely on variance.
- These levers are read from one open tool. Other employers' tools differ — some do
  JD-matching, some weight differently. Optimise the controllable, verifiable
  surfaces (parsing, links, real OSS, bonus URLs, JD-keyword coverage) and don't
  promise a score.
- Some strong engineers' best work was never public; Family-B tools structurally
  underrate them. That's a limitation of the tool, not the candidate — name it
  rather than fabricating public work to compensate.
