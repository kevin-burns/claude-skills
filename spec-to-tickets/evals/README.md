# spec-to-tickets evals

| what | where | graded by |
|---|---|---|
| the checks and the format | `../tests/` | pytest, every run |
| behaviour cases T1-T3 | `evals.json` (turns and arm-neutral expectations) | fresh Opus graders with quoted evidence |
| routing | `routing.json`, generated into the root `evals/` | `claude plugin eval` |

## Run

1. `python3 spec-to-tickets/evals/make_routing_cases.py` regenerates the routing cases.
2. `spec-to-tickets/evals/run_cases.sh spec-to-tickets/evals/runs/<date>` runs every case in three
   arms: with spec-to-tickets (and spec-ready), without, and with Matt Pocock's `to-tickets`
   (fetched at run time, called as `/to-tickets`).
3. Grade each run directory against its expectations, quoting evidence; save `grades.json` in the
   run directory (git-ignored). Report per arm and case, never pooled.

The PRD and spec in `fixtures/dictation/` were written by spec-ready in its own 2026-11-11 eval.

## Results

None yet.
