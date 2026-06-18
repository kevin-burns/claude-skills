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
- **The `dev-story` Workflow (hands-off, deterministic).** For a guaranteed run of
  plan→build→verify→review→full-suite, dispatch it via the Workflow tool with the **absolute**
  `scriptPath` `~/.claude/skills/dev-fleet/dev-story.workflow.js` (this skill's base directory,
  announced on load) — a relative `dev-fleet/…` won't resolve from the repo you're working in.
  It moves the orchestration into code and hands a ready-to-merge branch back to you. Use it when
  you want the steps to run in order without depending on the model *choosing* to.

See `docs/agent-fleet-architecture.md` for the why.

## The pipeline

```
plan ─▶ code-builder ─▶ fact-verifier (gate) ─▶ coherence-check (gate, if complex) ─▶ code-reviewer ─▶ full-suite gate ─▶ [you decide] ─▶ commit-pr
```

Each agent returns JSON (see its definition). You read that JSON and decide whether to
proceed, loop, or stop. You stay in the loop between stages — this is a skill, not an
unattended workflow.

### Loop-back semantics (what a failing gate does)
Every gate loops back to a **fresh-context** `code-builder` dispatch carrying the *specific*
problem — never a vague "try again". Re-run the gate after the fix (bound the loop to ~2 rounds,
then hand the residue to a human).

| Gate result | Loop back to builder with |
|---|---|
| `fact-verifier` REFUTED | the correct value to use |
| `coherence` fail | the specific structural mismatch (+ its `loop_back_target`) |
| `code-reviewer` blocking | the specific bug + suggested fix |
| full-suite RED | the failing test name(s) |

### 0. Plan first
For anything beyond a trivial edit, agree the approach before dispatching a builder.
Brainstorm/plan in the main session (or with the `Plan` agent). A builder with a fuzzy
brief produces fuzzy code. Capture an explicit **out-of-scope / deferred** list as part of the
plan (what you're intentionally leaving to a companion change) and forward it to the coherence
and review stages — otherwise they'll treat a deliberate deferral as a bug and blocking-flag it.

### 1. code-builder — implement
Dispatch with: the agreed plan, the target files/area, and **every fact it needs**
(IDs, versions, endpoints). Tell it to work in a worktree/branch.
- If it returns `missing_facts`, do **not** push it to guess. Go to step 2 to resolve
  them, then re-dispatch with the facts filled in.
- If it returns `open_questions` that change scope, decide before continuing.

### 2. fact-verifier — gate (run when facts are in play)
Run the verifier on any factual claims the change asserts or depends on — config values,
"library X supports Y", resource IDs, version constraints, "the spec says Z". Also use it
to resolve a builder's `missing_facts`.
- **Gate rule:** if any verdict is `REFUTED`, fix the code/claim (loop back to builder)
  before proceeding. If `UNVERIFIABLE`, run the returned `lookup_command` (or have the
  caller run it) and re-verify — never commit on an unresolved fact.
- Skip only when the change asserts no external facts (pure refactor with green tests).

### 2c. coherence-checker — structural gate (non-trivial changes)
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

### 3. code-reviewer — review
Dispatch on the builder's branch/diff. Read the findings:
- `blocking` / `needs-rework` → loop back to code-builder with the specific findings.
- `ship-with-fixes` → apply the minor fixes (small enough to do inline, or another
  builder pass) then continue.
- It is **advisory**. You weigh it and decide (disagree-and-commit); don't treat the
  verdict as a veto, but don't ignore a well-evidenced `blocking` finding either.

### 3b. Full-suite gate — the orchestrator's job
code-builder **bounds** its own test runs (targeted + the relevant module once) to avoid
minutes-long full-suite runs that risk a dropped session, and reports
`tests.full_suite_command`. Running the whole suite once is **your** job, not the builder's —
run it before landing and require green. (The `dev-story` workflow does this as an explicit
phase.) Never merge on an unrun or red suite.

### 4. Commit & land
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
- **Fact-gate before commit.** Nothing lands on an unresolved or refuted fact.
- **Advisory, not adversarial.** The reviewer and any red-team inform your decision;
  they don't make it.
- **Least privilege.** Verifier/coherence-checker/reviewer are read-only; only the builder
  writes; only a human pushes/merges.

## Refinements learned in practice

These sharpen the pipeline for specific task shapes. They came out of building gates
and registry-backed validators where the naive plan looked clean but the real data
disagreed.

### Calibrate a detector/gate against real data BEFORE freezing the builder brief
A gate's predicate ("X is a violation") is a domain claim, and the domain usually has
exceptions the plan doesn't know yet. If you hand the builder the naive rule, it ships
it, and the exceptions surface as false positives *after* review/merge — expensive to
unwind. Instead, **run the naive detector against production data first** (a throwaway
script or one inline pass), triage the hits into real-vs-benign, and hand the builder a
predicate that already encodes the exclusions. Symptom you skipped this: you're editing
the just-merged rule to special-case cases the gate itself surfaced. Real example: a
"catalog var absent from the pinned module = apply error" gate threw 6 hits, 5 benign —
the rule didn't know about hand-authored wrappers or a template's `parent_id` transform.
A 5-minute calibration pass would have moved that discovery to the front.

### Fact-gate the load-bearing facts UP FRONT, not just before commit
The standard order is build→verify, but when a change's correctness *rests on* external
facts (an API/module input surface, a version's behaviour, a resource shape), gather and
verify those facts **before** the builder starts — the builder should write against
verified facts, not assumptions it can't check offline. Moving fact-verification (or the
fact-gathering step that produces the builder's oracle) ahead of the build also tends to
surface real findings early (e.g. "this pinned version dropped that input") instead of in
reconcile.

### Network-dependent artifact: split builder (offline) from orchestrator (online)
When the change needs an artifact the offline builder can't produce (a fetched snapshot,
a registry baseline, anything requiring network/credentials), split the work cleanly:
- **builder** writes the code + a small committed **fixture** of the artifact + the
  integration test **guarded** by `skipif(not REAL_ARTIFACT.exists())`, and verifies
  against the fixture;
- **orchestrator** generates the real artifact in primary (online), which **activates**
  the guarded test, then runs the gate + full suite.
This keeps the builder hermetic and green in its worktree while the real-data gate lands
intact. Make the artifact generator fail loudly (non-zero exit) on partial output so a
half-built oracle can't be committed silently.

### Reconcile in the worktree; merge once
If the reviewer's findings (or a calibration pass) mean more work, do it **on the
builder's branch** — re-dispatch via `SendMessage` to the same builder, or edit in the
worktree — and merge only when clean. Merging first and then layering fixes + generated
artifacts in primary works, but it splits the change across two workspaces and leaves the
worktree behind. One branch, one merge, one history.

## Running for scale
For a batch of changes (a backlog, a migration), this interactive pipeline is the wrong
tool — use a Workflow. The `dev-story` workflow is the **per-item building block**: run it
solo for one story, or call it from a fan-out that respects task dependencies and gates
risky items for human review. Mind that dependent tasks touching shared files can't run in
parallel worktrees — sequence them. This skill is for the in-the-loop, one-change path.
