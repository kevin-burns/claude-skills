---
name: dev-fleet
description: Orchestration playbook for driving the development agent fleet (code-builder, fact-verifier, coherence-checker, code-reviewer) through a build → verify → cohere → review → commit pipeline with explicit, deterministic hand-offs. Use when implementing a non-trivial change where correctness and fact-accuracy matter and you want the steps to actually run in order rather than hoping the orchestrator delegates. Also use when deciding which fleet agent to dispatch for a task, or when wiring a new agent into the pipeline. Covers how to pass context between agents, the fact-gate and coherence-gate before commit, the loop-back semantics on each gate, and handing off to commit-pr.
license: MIT
---

# Dev Fleet Orchestrator

This skill tells the **main session** (the orchestrator — you) how to drive the
development agents as a pipeline. The agents live in `agents/`; the main session dispatches
each by name via the Agent tool, reads its JSON, and gates on the result.

**Two ways to run the pipeline — pick by how much determinism you need:**
- **This skill (in-the-loop).** You follow these steps and invoke each agent explicitly. A
  skill is *instructions you follow*, not a mechanical orchestrator — so it's only as
  reliable as your adherence. Don't lean on auto-delegation for a stage you care about;
  name the agent. (A human driving Claude Code can force a stage with an `@agent-…` mention.)
- **The `dev-story` Workflow (hands-off, deterministic).** For a guaranteed
  plan→build→verify→cohere→review→full-suite run, dispatch it via the Workflow tool with the
  **absolute** `scriptPath` `~/.claude/skills/dev-fleet/dev-story.workflow.js` (a relative path
  won't resolve from your repo). It moves orchestration into code and hands back a ready-to-merge
  branch; it mirrors the two-point fact discipline and gates coherence on change size
  automatically (`coherence: auto|always|never`). See *Running for scale*.

See `docs/agent-fleet-architecture.md` for the why.

## The pipeline

```
plan & scope ─▶ verify load-bearing facts ─▶ code-builder ─▶ fact-verifier (gate) ─▶ coherence-check (gate, if complex) ─▶ code-reviewer ─▶ full-suite gate ─▶ [you decide] ─▶ commit-pr
 (explore · calibrate)        (up front)                       (did it hold up?)
```

Each agent returns JSON (see its definition). You read that JSON and decide whether to
proceed, loop, or stop. You stay in the loop between stages — this is a skill, not an
unattended workflow.

**Facts get verified at two points** — load-bearing facts *before* the build (stage 1, so the
builder writes against evidence) and the finished change's claims *after* (stage 3, to catch
drift/assumption/hallucination). Same `fact-verifier` agent, two jobs (detailed in those stages).

### Loop-back semantics (what a failing gate does)
Every gate loops back to a **fresh-context** `code-builder` dispatch carrying the *specific*
problem — never a vague "try again". Re-run the gate after the fix (bound the loop to ~2 rounds,
then hand the residue to a human). Do the fix work **on the builder's branch** and merge once —
see *Patterns: reconcile in the worktree*.

| Gate result | Loop back to builder with |
|---|---|
| `fact-verifier` REFUTED | the correct value to use |
| `coherence` fail | the specific structural mismatch (+ its `loop_back_target`) |
| `code-reviewer` blocking | the specific bug + suggested fix |
| full-suite RED | the failing test name(s) |

### 0. Plan & scope — explore, calibrate, surface the facts
For anything beyond a trivial edit, agree the approach before dispatching a builder — but scoping
is more than writing a brief. It's where you **explore** the real code/data, **calibrate** any
rule the change depends on, and **surface the facts** it will rest on. A builder with a fuzzy
brief produces fuzzy code.
- **Calibrate a detector/gate against real data before you freeze the builder brief.** A gate's
  predicate ("X is a violation") is a domain claim, and the domain usually has exceptions the plan
  doesn't know yet. Hand the builder a naive rule and the exceptions surface as false positives
  *after* merge — expensive to unwind. Run the naive rule against real data first (a throwaway
  script or one inline pass), triage hits into real-vs-benign, and hand the builder a predicate
  that already encodes the exclusions. (Real example: a naive "catalog var absent from pinned
  module = error" gate threw 6 hits, 5 benign — calibration moved that discovery to the front.)
- **Surface the load-bearing facts** the change will depend on — an API/module input surface, a
  version's behaviour, a resource/schema shape. These feed stage 1.
- **Flag combinatorial features for pairwise design.** If behaviour turns on ≥3 interacting
  parameters, say so — the builder designs the case matrix with pairwise/PICT, not ad-hoc cases
  (TDD by default; see code-builder's test-first guidance).
- **Capture out-of-scope / deferred** work (what you're leaving to a companion change) and forward
  it to the coherence and review stages — otherwise they'll treat a deliberate deferral as a bug.

### 1. Verify load-bearing facts — up front, before building
When the change's correctness *rests on* external facts you don't already hold, gather and verify
them **before** the builder starts; it should write against verified facts, not offline guesses it
can't check. Dispatch `fact-verifier` on the load-bearing facts from stage 0, using its sources —
MS Learn / official docs, `source-snapshot`, `c7search`/Context7, schema dumps.
- Front-loading surfaces real findings early — "this pinned version dropped that input" shows up
  now, not in reconcile after the build.
- The verified facts (and any corrected values) become the builder's **oracle** — pass them as
  data into stage 2.
- Skip only when the change rests on nothing external (e.g. a pure refactor with green tests).

### 2. code-builder — implement
Dispatch with: the agreed plan, the target files/area, the **verified facts** from stage 1, and a
**calibrated predicate** if a gate is involved. Tell it to work in a worktree/branch.
- If it returns `missing_facts`, do **not** push it to guess. Resolve them with the stage-1 tools,
  then re-dispatch with the facts filled in.
- If it returns `open_questions` that change scope, decide before continuing.
- If the change needs a network-dependent artifact the offline builder can't produce, split the
  work — see *Patterns: network-dependent artifact*.

### 3. fact-verifier — gate (did the build hold up?)
Now verify the claims the *finished* change asserts or depends on — the drift check: did the
builder assume, invent, or hallucinate a value/API/behaviour along the way? Run it on config
values, "library X supports Y", resource IDs, version constraints, "the spec says Z".
- **Gate rule:** if any verdict is `REFUTED`, fix the code/claim (loop back to builder) before
  proceeding. If `UNVERIFIABLE`, run the returned `lookup_command` (or have the caller run it) and
  re-verify — never commit on an unresolved fact.
- Skip only when the finished change asserts no external facts (pure refactor with green tests).

### 4. coherence-checker — structural gate (non-trivial changes)
Runs **after** fact-verifier (so refuted assumptions are known) and **before** code-reviewer (a
cheaper structural pass than line-level review). It checks whether the implementation that exists
structurally matches the **plan, the spec it cites, and the verified facts** — a different lens
from the reviewer's line-level correctness. Its five checks:
1. **Spec-to-code traceability** — every cited spec section / MUST has code + a test.
2. **Inverse-pair fidelity** — every `(encode,decode)`/`(write,read)`/`(export,import)` pair has a
   `decode(encode(x)) == x` test with **no normalization tricks** (`.rstrip()`/`.lower()`/`set()`/
   `sorted()` that paper over the real delta).
3. **Plan-to-commit traceability** — every plan task has a change; skips are explicit, not silent.
4. **Cross-implementation parity** — when >1 impl of an interface changed, a test drives the same
   input through each and asserts equivalent observable behaviour (not just "all have the method").
5. **Contract-docstring fidelity** — docstrings/schemas match what the code actually does.

Dispatch with the **plan** (incl. `out_of_scope`), the **fact verdicts** (so it can confirm the
code used corrected values, not refuted ones), and the **branch/diff**.
- **When to run:** non-trivial changes only — `files_changed > 5`, `commits > 3`, or a multi-part
  plan. A one-file, one-commit change doesn't earn the stage; skip it. (The `dev-story` workflow
  gates this automatically with a `coherence: auto|always|never` arg.)
- **Gate rule:** `verdict: fail` → loop back to code-builder with the structural mismatch, then
  re-run. Advisory like the reviewer — you weigh it; a deliberate `out_of_scope` deferral is never
  a coherence failure.
- **Boundary:** keep it on structure/traceability/parity. If its only finding is a line-level bug,
  that's the reviewer's lane — don't double-report.

### 5. code-reviewer — review
Dispatch on the builder's branch/diff. Read the findings:
- `blocking` / `needs-rework` → loop back to code-builder with the specific findings.
- `ship-with-fixes` → apply the minor fixes (small enough to do inline, or another
  builder pass) then continue.
- It is **advisory**. You weigh it and decide (disagree-and-commit); don't treat the
  verdict as a veto, but don't ignore a well-evidenced `blocking` finding either.

### 6. Full-suite gate — the orchestrator's job
code-builder **bounds** its own test runs (targeted + the relevant module once) to avoid
minutes-long full-suite runs that risk a dropped session, and reports
`tests.full_suite_command`. Running the whole suite once is **your** job, not the builder's —
run it before landing and require green. (The `dev-story` workflow does this as an explicit
phase.) Never merge on an unrun or red suite.

### 7. Commit & land
When green and reviewed, hand to **commit-pr** for the commit/PR message (it reads the
`commit-style` playbook). Landing (push/merge/PR open) is a human decision — confirm
before pushing, per the global git rules. Never auto-push from the pipeline.

## Choosing an agent (quick routing)
| Need | Agent |
|---|---|
| Write/modify code or tests | `code-builder` |
| "Is this fact/version/ID/claim true?" | `fact-verifier` |
| "Does the impl structurally match the plan/spec/verified facts?" | `coherence-checker` |
| "Is this change correct / safe to land?" | `code-reviewer` |
| Commit or PR/MR message | `commit-pr` |
| Security-focused pass | `/security-review` |
| Design/architecture trade-offs | architecture agent (e.g. `azure-architect`) |

## Passing context between agents
Agents run in isolated context windows — they see only the prompt you pass. So:
- Forward the **relevant prior output** explicitly (the builder's branch name and
  `files_changed` into the reviewer; a verifier's `correct_value` into the builder).
- Pass facts as data, not "as discussed" — the agent has no memory of the conversation.
- Tell each agent where to read project conventions; don't assume it knows them.

## Principles
- **Explicit over auto.** Dispatch by name; gate on results. Determinism beats luck.
- **Fact-gate at both ends.** Load-bearing facts before the build, the change's claims before
  commit — nothing lands on an unresolved or refuted fact.
- **Advisory, not adversarial.** The reviewer and any red-team inform your decision;
  they don't make it.
- **Least privilege.** Verifier/coherence-checker/reviewer are read-only; only the builder
  writes; only a human pushes/merges.

## Generating infrastructure-as-code (extra governance)

Infrastructure changes are high-blast-radius and often irreversible, so when the fleet
*generates* IaC (Terraform/OpenTofu/Terragrunt) the bar is higher than for app code. The
pattern the field has converged on — "**through IaC, not instead of it**" — is that the agent
produces *reviewable IaC*, never direct cloud changes. (Hard-won dogfooding a graph→IaC
generator: the model is the contract; the gates are the moat.)

- **Generate code, never touch the cloud.** No agent runs `apply`/`destroy` or calls cloud
  APIs directly against real environments. It emits IaC + a plan for a human/pipeline to apply.
- **Plan → review → apply, always.** State-changing infra routes through a `plan` a human or
  the pipeline reviews; the pipeline is the only path to prod. (The same rule terragrunt-skill
  states for human authors binds *doubly* for agents.)
- **Query state before acting.** Read existing state/graph first; never assume the cache is
  current. Acting blind breaks idempotency and creates drift.
- **The data model is the contract.** When generation is driven by a typed model/graph,
  validate intent against the model *before any code exists*, and check generated output
  *against the model* (conformance) — don't trust emitted HCL until a `plan` shows no
  unintended changes (no create/destroy/replace, no state-key churn).
- **Verification cost rises as generation gets cheap.** The faster agents emit IaC, the more
  the gates (fact-verify, conformance tests, plan-no-change, policy-as-code) are the moat —
  invest there, not in trusting the generator.

## Patterns for specific task shapes
Depth beyond the core stages, from real runs.

### Network-dependent artifact: split builder (offline) from orchestrator (online)
When the change needs an artifact the offline builder can't produce (a fetched snapshot, a
registry baseline, anything needing network/creds): the **builder** writes the code + a small
committed **fixture** + an integration test guarded by `skipif(not REAL_ARTIFACT.exists())` and
verifies against the fixture; the **orchestrator** generates the real artifact online (which
activates the guarded test), then runs the gate + full suite. Make the generator **fail loudly**
(non-zero exit) on partial output so a half-built oracle can't be committed silently.

### Reconcile in the worktree; merge once
If the reviewer's findings (or a calibration pass) mean more work, do it **on the builder's
branch** (re-dispatch via `SendMessage`, or edit in the worktree) and merge only when clean —
one branch, one merge, one history.

## Running for scale
For a batch (backlog, migration), don't use this interactive pipeline — use a Workflow. The
`dev-story` workflow is the **per-item building block**: run it solo, or from a fan-out that
respects task dependencies, gates risky items, and sequences shared-file tasks (they can't run
in parallel worktrees). This skill is the in-the-loop, one-change path.
