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

None yet.
