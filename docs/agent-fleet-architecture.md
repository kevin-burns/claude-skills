# Agent Fleet Architecture (ADR)

**Status:** Draft for review · **Date:** 2026-06-11 · **Owner:** Kevin Burns

A reusable collection of specialist subagents for software- and product-development
work, coordinated by deterministic orchestrators. Think "design council, but the
roles are persistent, isolated workers" — with a fact-discipline rule running through
all of them so the fleet can *build, test, and review code against a fact*.

---

## 1. Context & problem

We want a standing team of agents that covers the bulk of SWE + product tasks:
build, test, verify-against-a-fact, review, and the design-time roles (architect,
product, red-team). Two questions drive the design:

1. **What's the right unit** — a skill, or a subagent?
2. **Who triggers whom**, and how do we know an agent fires when we want it to (and
   *doesn't* when we don't)?

This ADR fixes the shape before we write any agent files.

## 2. Decision summary

- **Unit:** a thin **skill = playbook** (the "how") + **subagent = worker** (the "who",
  with isolated context, scoped tools, own model). They compose; agents read skills.
  We already do this: `commit-pr` (worker) reads `commit-style` (playbook).
- **Orchestration:** prefer **explicit, deterministic invocation** (a coordinating
  skill or a Workflow calls agents by name) for any pipeline we care about. Treat
  auto-delegation (orchestrator picks from descriptions) as convenience, not a
  guarantee.
- **Fact-discipline is mandatory in every agent:** never invent a fact (GUID, ID, API
  shape, version, pricing). If a fact is missing, STOP and return the exact lookup
  command(s) the caller should run. (Pattern proven in a project-specific
  infra-builder agent, after a fabricated-ID incident.)
- **Red-team is advisory, never a gate.** Its mandate is *find what breaks this and
  propose the fix* — verdict + remediation, not veto. The orchestrator does
  disagree-and-commit.

## 3. Skill vs. subagent (when to use which)

| | Skill (playbook) | Subagent (worker) |
|---|---|---|
| Carries | "How to do X" + scripts/refs | Does the work in its own context window |
| Context | Loads into the caller | Isolated — sees only the prompt passed to it |
| Tools / model | Inherits caller's | Scopes its own `tools:` and `model:` |
| Best for | Knowledge, conventions, deterministic scripts | Role separation, parallelism, isolation, guardrails |
| Triggered by | Description (in-context) | Description (auto-delegation) **or** `Task`/`agent()` (explicit) |

Rule of thumb: if it needs **isolation, its own toolset, or to run in parallel** →
subagent. If it's **shared know-how** several agents reuse → skill.

## 4. Fleet layout

Lanes mirror an engineering org. **Bold = exists today.**

### Build lane
- `code-builder` — implements in an isolated worktree, TDD, commits on a feature
  branch; never merges/pushes/applies. (Generalize `iac-builder`.)
- `test-author` — writes/expands tests (can start folded into `code-builder`).

### Verify lane — the "against a fact" keystone
- `fact-verifier` — checks code/claims against an authoritative source
  (`c7search`/Context7, official docs, repo specs, Ogham). Mandate: **cite or
  refute**; never assert from memory.
- **`coherence-checker`** — structural fit of the implementation against the plan, the spec it
  cites, and the verified facts: spec/plan traceability, inverse-pair round-trip fidelity (no
  normalization tricks), cross-implementation parity, contract-docstring fidelity. Read-only and
  advisory; sits between `fact-verifier` and `code-reviewer`, gated on change complexity. (Added
  from a battle-test retro: a `.rstrip()` round-trip test masked a real serialization delta.)
- `code-reviewer` — correctness/bugs on the diff (pairs with `/code-review`).
- security review — covered by built-in `/security-review`.

### Design lane
- **`azure-architect`** — enterprise Azure / CAF design (exists).
- `architect` — general system design & trade-offs.
- `product-strategist` / `delivery-pm` — the product-development roles.
- `red-team` — constructive adversary (see §6).

### Docs & delivery lane
- **`docs-reviewer`** — reviews docs for completeness/clarity (exists).
- **`commit-pr`** — writes commit + PR/MR messages (exists; haiku; `Bash, Read, Grep`).
- **`commit-style`** — commit/PR style playbook that `commit-pr` reads (exists).

### Synthesis
- **Orchestrator** — a skill or Workflow that routes work, runs the pipeline, and
  reconciles outputs (the council's "preserve dissent, don't average" behavior).

**Phase 1 target (high-leverage):** `code-builder → fact-verifier → code-reviewer`,
handing off to `commit-pr`, wired by a thin `dev-fleet` orchestrator skill. Everything
else is additive.

## 5. Cross-cutting agent conventions

Every agent definition follows the `iac-builder` template:

1. **Description = trigger.** Lead with *when to use*; be slightly pushy (orchestrators
   under-delegate). State negative scope ("never merges/pushes/applies").
2. **Least-privilege `tools:`** — reviewers/verifiers get read-only sets
   (`Read, Grep, Glob, Bash`, `WebFetch` for the verifier); only builders get
   `Edit, Write`. Tool scope *is* the guardrail.
3. **Model tier per role** — pin `model:` in the agent frontmatter. Accepts
   `sonnet`, `opus`, `haiku`, `fable`, a full ID (`claude-opus-4-8`), or `inherit`.
   haiku/sonnet for mechanical work, opus/fable for architecture/synthesis. (Matches
   the global "cheapest model that fits".) See §5.1 for how this drives the
   cheap/capable split.
4. **Return-as-data** — the final message is structured input for the orchestrator,
   not prose. Each agent declares an explicit return schema.
5. **Fact-discipline** — the §2 rule, in every agent.
6. **Git rules** — never add Co-Authored-By / AI attribution; never auto-push or merge
   (caller's job). Defer to `AGENTS.md` + `commit-style`.

### 5.1 Model selection — the routing lever is the agent, not CLAUDE.md

The mechanism that picks a model per task is **subagent delegation**, not CLAUDE.md.
CLAUDE.md is a context/memory file loaded into the prompt — it documents heuristics
("use the architect for X") but does not mechanically route. What Claude actually
decides is *which agent to hand off to*; the model **rides along** with that agent,
fixed by its `model:` frontmatter and run in its own context window.

- **The main session runs one model** (set via `/model` or plan default) and does not
  silently swap mid-turn. Keep the top-level thread sensible and push the
  fable-vs-sonnet-vs-haiku decision **down into the agents**. This is the whole reason
  the cheap/capable split lives in the fleet.
- **Resolution order** when `model:` is set in more than one place:
  `CLAUDE_CODE_SUBAGENT_MODEL` env var → per-invocation `model` parameter →
  subagent `model:` frontmatter → main conversation's model.
- **Built-in precedent:** the `Explore` agent runs on **haiku**; `Plan` **inherits**
  the main model. The cheap-exploration / capable-planning split is already baked in —
  our fleet just extends the same pattern (e.g. `fact-verifier`/`code-reviewer` on
  sonnet, `architect`/`red-team` on opus or fable, mechanical builders on haiku).
- A sharp **`description:`** is what makes auto-routing land on the right agent — so
  for any agent we *do* leave auto-delegated, the description is doing the model
  selection by proxy. (Reinforces §6's precision point.)

## 6. Orchestration & the trigger question

Two delegation modes — do not conflate them:

- **(a) Auto-delegation:** the main loop reads descriptions and decides to hand off.
  Probabilistic, and **under-fires for tasks the model thinks it can just do** (the
  same effect we measured optimizing `markdown-converter`: recall stayed 0% across
  every description rewrite because the work looked "simple"). Good descriptions raise
  the odds; they never guarantee.
- **(b) Explicit invocation:** a skill/Workflow calls the agent by name. Deterministic.

**Decision:** encode any pipeline we depend on as (b). Don't hope the orchestrator
summons the verifier before commit — make the orchestrator *always* call it. Reserve
(a) for convenience routing.

> For a fleet, **precision matters more than recall**: a mis-fired builder or red-team
> is worse than one that didn't fire. Tune descriptions to avoid *false* delegation
> first.

## 7. Testing strategy

Two separate concerns, both reusing the `skill-creator` harness:

1. **Triggering test** (only for auto-delegated agents): a 20-query
   should-trigger / should-not-trigger set run through the orchestrator; measure
   precision/recall with the description optimizer. Accept that simple prompts won't
   delegate regardless of wording.
2. **Behavioral test** (the important one): real input fixtures → run the agent →
   assert on its return schema and side-effects. Examples:
   - `code-builder`: committed on a branch? refused to push/apply? tests pass?
   - `fact-verifier`: **plant a known-false fact → assert it is REJECTED**; supply a
     true fact → assert it is cited with a source. This is the regression test for the
     whole "against a fact" premise.
   - `red-team`: returns verdict + remediation, not a veto.

## 8. Phasing

1. **This ADR** ← you are here.
2. `fact-verifier` end-to-end (definition + behavioral eval). Keystone first.
3. `code-builder` + `code-reviewer`; wire the `dev-fleet` orchestrator skill →
   `commit-pr`.
4. Design lane (`architect`, `product-strategist`, `red-team`) + a council-style
   orchestrator that preserves dissent.
5. Triggering evals for any agent we want auto-delegated.

## 9. Decisions & open questions

**Resolved:**
- **Home & sharing:** the fleet lives in the public `claude-skills` repo under
  `agents/`, with each agent file symlinked into `~/.claude/agents/` so Claude Code
  loads it (same pattern as the skills). **Hard constraint:** no PII or IPR in committed
  files — no client/project names, internal incident IDs, secrets, subscription/tenant
  IDs, or absolute user paths. Project-scoped agents that must reference proprietary
  context stay out of this repo.
- **Fact sources of record:** precedence for `fact-verifier` is repo specs > official
  docs/Context7 > memory store (Ogham) > model memory (never). Implemented in
  `agents/fact-verifier.md`.

**Open:**
- **Project vs. user scope:** which agents are global vs. per-project (agents that must
  reference proprietary context stay in their private project repo, not here).
- **Orchestrator form:** coordinating *skill* (you stay in the loop each turn) vs.
  *Workflow* (deterministic fan-out, runs to completion)? Likely both — skill for
  interactive, Workflow for batch.
