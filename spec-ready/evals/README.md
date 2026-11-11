# spec-ready evals

| what | where | graded by |
|---|---|---|
| gate scripts | `../tests/` | pytest, every run |
| behaviour scenarios S1-S8 | `evals.json` (turns, the item each turn states, expectations) | fresh Opus graders with quoted evidence |
| routing: fires when asked "is this ready to spec", silent on near misses | `routing.json`, generated into the root `evals/` | `claude plugin eval` |

## Run

1. `python3 spec-ready/evals/make_routing_cases.py` regenerates the routing cases.
2. `spec-ready/evals/run_cases.sh spec-ready/evals/runs/<date>` runs every scenario. Session
   scenarios replay their turns into a real session (`claude -p`, then `--resume` per turn) in three
   arms: with spec-ready, without it (the user's own configuration), and with Matt Pocock's
   `to-spec` fetched from github.com/mattpocock/skills (MIT) as a project skill. S6 is gate-only:
   the gate runs with no readable transcript.
3. Grade each run directory against the case's expectations, quoting evidence from
   `session.jsonl`, `written.txt` and the written files. Save `grades.json` in the run directory
   (git-ignored).

Results are reported per arm and per case, never pooled.

## Results

### 2026-11-11, routing (`claude plugin eval`, Sonnet, 10 runs per case, commit 3e1145f)

180/180: every should-fire case fired 10/10, and every near miss stayed silent 10/10, including
two that describe a plan without asking for a spec. Cost 13.27 USD as the tool reports it. Caveat:
the eval sandbox loads this plugin only, so routing against a full personal skill set is not
measured here; the early firing seen in the core runs (S2 turn 5, S4 turn 0) happened mid-
conversation with spec-ready installed as a project skill, a context single-prompt cases do not
reproduce.

### 2026-11-11, core cases (S1, S2, S8), commit c92bbbe + runner fix 4423f08

Claude Code with Sonnet as the session model, one run per case and arm, about 12.74 USD
API-equivalent for all six runs. Both arms load the same user-level configuration (CLAUDE.md,
superpowers, software-design-rules), so "without" is that configuration alone, not a bare model.
Graded by a fresh Opus subagent with quoted evidence (`grades.json` in the run directory,
git-ignored). Expectations passed, excluding ones that cannot apply to the arm:

| case | with spec-ready | without |
|---|---|---|
| S1 anti-goal never stated | 3/3: gate open on anti_goal, nothing written | 1/2: asked twice, then wrote a PRD with the anti-goal "[open, asked twice, not yet answered]" |
| S2 bare "Sounds fine." / "Sure." | 2/2: never cited them, asked both items | 1/2: did not treat them as settled, but wrote the PRD with the anti-goal open |
| S8 answer the round, then pass | 3/3: first gate open on exactly anti_goal and success_check, then exit 0; PRD cites the answer turn, check_sources clean | 2/3: wrote the PRD before the answer, turning a risk into the anti-goal |

Invented content: none in figures with the skill; its S8 spec added one user story and one
out-of-scope line nobody stated. Without it, S2 invented a 1 s latency target, clip counts, a
30-minute spike, and presented the eval host's macOS version as the person's machine.

Known limits of this run:

- In session mode every open item was "not proposed": the agent left it out rather than the
  verifier rejecting a weak proposal. The verifier's own rejection was checked separately on
  2026-11-11 with the S2 fixture proposals (non_goals and anti_goal left open, gate exit 1).
- `written.txt` matched only prd.md/spec.md/readiness.json, so it was empty for the without arm,
  which wrote PRD.md and *-prd.md / *-spec.md files; the grader read the repositories directly.
- The scripted person never answers the agent's own clarifying questions, so both arms re-ask.
- n = 1 per case and arm.
