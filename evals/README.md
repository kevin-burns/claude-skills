# Routing evals

Eight cases that ask one question: **when the 21 skills are installed as a plugin and their
names are prefixed `claude-skills:`, does a request still reach the right one?**

Twelve of the 21 name a sibling by **bare name** inside their own description —
`cv-and-human` points at `cv-evidence-base`, `report-builder` at `c7search`, `dev-fleet` at
`source-snapshot`. Nobody has measured whether those cross-references survive namespacing.
Tracked as `claude-skills-0kt`.

## First real run, 2026-10-02 (claude-skills-b9nk.5)

`claude plugin eval` is now generally available, and the suite has run. **The case layout the
section below guessed was wrong**: every prompt.md and grader needs YAML front matter (prompt:
`max_turns`, `allowed_tools`; grader: `type`, `weight`). Without it the loader rejects the case
with `graders: Required`. Both are fixed, and each case now also carries a `fired.md`
`tool_used: Skill` grader, because the first run showed the no-plugin arm passing the `llm`
routing grader too. That grader alone could not say whether the skill fired.

Three runs per arm, per model. "Fired" = how many of the 3 with-plugin runs invoked the right
skill (for `negative-no-skill`, how many invoked none):

| case | Haiku fired | Sonnet fired | Opus fired |
|---|---|---|---|
| cv-fork-evidence | 0/3 | 3/3 | 3/3 |
| cv-fork-tailor | 0/3 | 3/3 | 3/3 |
| docs-fork-convert | 0/3 | 3/3 | 3/3 |
| docs-fork-library (`c7search`) | 0/3 | **0/3** | **0/3** |
| iac-fork-registry | 3/3 | 3/3 | 3/3 |
| negative-no-skill (none should fire) | 3/3 | 3/3 | 3/3 |
| writing-fork-neutral | 0/3 | 3/3 | 3/3 |
| writing-fork-persuasive | 0/3 | 3/3 | 3/3 |

What it says:

- **On Haiku the skills almost never fire** (1 of 7 positive cases). Anthropic's per-model
  question for Haiku is "does the Skill provide enough guidance?", and for routing the answer
  here is no.
- **On Sonnet and Opus routing is right on 6 of 7**, and no false positives.
  **`c7search` never fires on any model**: its description loses to answering from memory.
- **The `llm` routing scores are not yet trustworthy.** Some cases fire 3/3 and still score 0,
  for example iac-fork-registry on Sonnet and Opus. `allowed_tools` was set to
  `[Read, Glob, Grep, Skill]`, so a skill that needs Bash to run its CLI fires and then cannot
  do its job. The tool set per case is the next fix, before reading Δ.
- Cost of the three-model run as the tool reports it: Haiku $1.38, Sonnet $3.12, Opus $6.91.

Run with the logged-in credential: `env -u ANTHROPIC_API_KEY claude plugin eval . --model <m>`.
A stale `ANTHROPIC_API_KEY` in the environment makes every run fail with a 401.

### Second pass, same day: scoring routing rather than execution

Three fixes:
- **The sandbox blocks the CLI skills.** Eval runs can't read the home directory, so
  `~/go/bin/c7search`, `uv` and `markitdown` are unreachable, and network is off unless
  granted. The three CLI cases' rubrics now pass a response that follows the skill's method
  and reports the tool unavailable.
- `negative-no-skill`'s fired check is `arm: both`, as the docs recommend for a must-not-fire
  check.
- **`cv-fork-evidence` said "here is my CV" and attached none**, so the skill rightly asked for
  one and the rubric failed it. It now carries a short fictional CV.

| | first run | second run |
|---|---|---|
| Sonnet overall score / mean Δ | 0.62 / +0.17 | 0.73 / +0.27 |
| Haiku overall score / mean Δ | 0.50 / +0.17 | 0.44 / −0.02 |

On Sonnet the CLI cases now show the skill's value: docs-fork-convert and iac-fork-registry
moved to Δ +1.00. On Haiku the skills still do not fire, so Δ is noise. cv-fork-evidence with
the fixture: fires 3/3 and passes 3/3 on Sonnet, but the no-plugin arm also passes 3/3, so
this rubric cannot yet tell the skill's method from a competent generic answer.

## Running them, when access lands

```bash
claude plugin eval claude-skills --ablation with-without
```

The `--ablation with-without` arm is the point. It runs each case **with the plugin and
without it** and reports the delta. A routing suite without that arm cannot tell "the skill
fired and helped" from "the model would have answered well anyway" — and the second is the
null hypothesis this whole exercise exists to reject.

Useful flags: `--case <glob>` to run one, `--runs <n>` (default 3), `--judge-model` (default
haiku), `--verbose` to stream the trace, `--max-cost-usd` for a hard ceiling.

## The cases

| case | should route to | the trap |
|---|---|---|
| `cv-fork-tailor` | `cv-and-human` | a target role exists, so this is tailoring, not discovery |
| `cv-fork-evidence` | `cv-evidence-base` | **no** target role, which is the whole signal |
| `writing-fork-neutral` | `clear-and-human` | reference prose, not persuasion |
| `writing-fork-persuasive` | `hook-and-human` | `clear-and-human`'s description also lists "LinkedIn post" |
| `docs-fork-library` | `c7search` | one API question, not a fact worth pinning |
| `docs-fork-convert` | `markdown-converter` | local files, not a web source to snapshot |
| `iac-fork-registry` | `terraform-registry` | "not writing config yet" rules out `terragrunt-skill` |
| `negative-no-skill` | **nothing** | see below |

**`writing-fork-persuasive` is the sharpest case in the set** and was written to be
adversarial. `clear-and-human`'s description names "LinkedIn post" among the things it
handles, while `hook-and-human` owns persuasive copy. If any routing breaks under
namespacing, expect it here first.

**`negative-no-skill` is not padding.** A suite made only of positive cases measures
eagerness rather than accuracy — a plugin whose skills fire on everything would score
perfectly. A false positive is not free either: 21 descriptions are already loaded on every
request, so a skill firing on a concurrency question spends context and misleads the reader
about what the collection is for.

## What these do not test

- **Whether the skills are any good.** That is the per-skill `evals.json` sets, which are a
  different harness. See `clear-and-human/evals/README.md`, the only one documented so far.
- **The Codex side.** Codex namespaces `plugin:skill` identically — verified by installing
  and enumerating — but `codex` has no equivalent eval runner, so the same question is open
  there and has no instrument.
- **Anything about the eight skills with no routing fork.** These cases cover the pairs that
  can plausibly be confused, not the whole collection.
