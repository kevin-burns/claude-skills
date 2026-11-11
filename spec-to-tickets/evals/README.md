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

### 2026-11-11 (Sonnet, one run per arm and case)

Behaviour, six expectations per case, one blind Opus grader (labels shuffled per case):

| case | with | without | to-tickets |
|---|---|---|---|
| T1 no breakdown yet | 5/6 | 1/6 | 1/6 |
| T2 horizontal breakdown | 5/6 | 3/6 | 2/6 |
| T3 issue-per-file | 6/6 | 4/6 | 3/6 |

- The with arm's only misses are expectation 5: unmarked acceptance specifics ("five-minute
  dictation") in T1 and T2. Acceptance criteria are not traced the way slices are.
- The without arm in T1 ran six weeks with nothing usable until week 4, and called a headless
  core a walking skeleton. The to-tickets arm in T2 told the user they had approved additions
  they had never answered.
- The with arm in T3 changed the least: it did not split the oversized issue 001 and carried
  issue 003's punctuation mismatch forward, which both other arms caught.
- Blinding was imperfect. The grader's input copy came from the with-arm repo and included its
  `tickets.md`, and the replies name their tools. The grader noticed and graded on content.
- Cost (CLI figures): with $1.86, without $1.59, to-tickets $1.45.

Routing (`claude plugin eval`, Sonnet, 10 runs per case, $11.77): 142/160. All 8 negative cases
and route-01 to route-06 are 10/10. Two prompts that check rather than build are missed:
"Check this ticket breakdown: is anything horizontal?" (2/10) and "Which of these tickets are
Must Haves for the first timebox?" (0/10).
