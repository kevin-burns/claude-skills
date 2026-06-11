---
name: dev-fleet
description: Orchestration playbook for driving the development agent fleet (code-builder, fact-verifier, code-reviewer) through a build → verify → review → commit pipeline with explicit, deterministic hand-offs. Use when implementing a non-trivial change where correctness and fact-accuracy matter and you want the steps to actually run in order rather than hoping the orchestrator delegates. Also use when deciding which fleet agent to dispatch for a task, or when wiring a new agent into the pipeline. Covers how to pass context between agents, the fact-gate before commit, and handing off to commit-pr.
license: MIT
---

# Dev Fleet Orchestrator

This skill tells the **main session** (the orchestrator — you) how to drive the
development agents as a deterministic pipeline. The agents live in `agents/` and are
dispatched via the Task tool by name. Don't rely on auto-delegation for a pipeline you
care about: **invoke each stage explicitly, in order, and gate on its result.** See
`docs/agent-fleet-architecture.md` for the why.

## The pipeline

```
plan ─▶ code-builder ─▶ fact-verifier (gate) ─▶ code-reviewer ─▶ [you decide] ─▶ commit-pr
```

Each agent returns JSON (see its definition). You read that JSON and decide whether to
proceed, loop, or stop. You stay in the loop between stages — this is a skill, not an
unattended workflow.

### 0. Plan first
For anything beyond a trivial edit, agree the approach before dispatching a builder.
Brainstorm/plan in the main session (or with the `Plan` agent). A builder with a fuzzy
brief produces fuzzy code.

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

### 3. code-reviewer — review
Dispatch on the builder's branch/diff. Read the findings:
- `blocking` / `needs-rework` → loop back to code-builder with the specific findings.
- `ship-with-fixes` → apply the minor fixes (small enough to do inline, or another
  builder pass) then continue.
- It is **advisory**. You weigh it and decide (disagree-and-commit); don't treat the
  verdict as a veto, but don't ignore a well-evidenced `blocking` finding either.

### 4. Commit & land
When green and reviewed, hand to **commit-pr** for the commit/PR message (it reads the
`commit-style` playbook). Landing (push/merge/PR open) is a human decision — confirm
before pushing, per the global git rules. Never auto-push from the pipeline.

## Choosing an agent (quick routing)
| Need | Agent |
|---|---|
| Write/modify code or tests | `code-builder` |
| "Is this fact/version/ID/claim true?" | `fact-verifier` |
| "Is this change correct / safe to land?" | `code-reviewer` |
| Commit or PR/MR message | `commit-pr` |
| Security-focused pass | `/security-review` |
| Design/architecture trade-offs | architecture agent (e.g. `azure-landing-zone-architect`) |

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
- **Least privilege.** Verifier/reviewer are read-only; only the builder writes; only a
  human pushes/merges.

## Running for scale
For a batch of independent changes (many files, a migration), this interactive pipeline
is the wrong tool — use a Workflow to fan out builder→verify→review per item with
worktree isolation. This skill is for the in-the-loop, one-change-at-a-time path.
