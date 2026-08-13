# Routing evals

Eight cases that ask one question: **when the 21 skills are installed as a plugin and their
names are prefixed `claude-skills:`, does a request still reach the right one?**

Twelve of the 21 name a sibling by **bare name** inside their own description —
`cv-and-human` points at `cv-evidence-base`, `report-builder` at `c7search`, `dev-fleet` at
`source-snapshot`. Nobody has measured whether those cross-references survive namespacing.
Tracked as `claude-skills-0kt`.

## Read this before trusting anything here

**These have never been run.** `claude plugin eval` is in early access and is not available
on this account — `claude plugin eval init` returns *"`plugin eval` is currently in early
access"* and refuses to scaffold. So the case layout below follows what
`claude plugin eval --help` documents, and **the layout itself is unverified**.

That matters more than usual in this repo. Three manifest schemas were guessed and shipped
this week; two of them failed **silently** — the Claude `agents` field accepted valid file
paths and loaded zero agents, and a `marketplace.json` with the wrong `source` shape
registered successfully and listed no plugins. Neither raised an error. Assume the same is
possible here until a run proves otherwise.

`prompt.md` + `graders/*.md` was chosen over `case.yaml` deliberately: it is the form with
the fewest fields to get wrong.

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
