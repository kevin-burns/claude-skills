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

### 2026-11-11 rerun after the `specifics` check (T1, T2; with arm only)

The first run's only with-arm misses were unmarked specifics in acceptance criteria, and the skill's
own worked example modelled one ("a recorded five-minute email"). Commit c75cd3b added the
`specifics` check and marked the example `Proposed:`. Rerun graded blind against the first run's
without and to-tickets outputs, inputs rebuilt from fixtures (no leaked files):

| case | with | without | to-tickets |
|---|---|---|---|
| T1 | 6/6 (was 5/6) | 1/6 | 1/6 |
| T2 | 6/6 (was 5/6) | 3/6 | 2/6 |

The unchanged arms scored the same as in the first grading. Both with-arm runs marked their figures
`Proposed:` ("the pass threshold is agreed with the user, since none is given"). Open: in T1 the with
arm wrote "the spec names no finer split" and declared only core and adapters as layers, although
the spec names four adapters. The agent chooses the layers that `vertical` checks against.

### 2026-11-12, T4: a breakdown too heavy on Must (all three arms)

Food-bank rota fixture; the earlier breakdown is 73% Must, and the person only says "Go ahead and
finish it". One blind Opus grader, inputs rebuilt from fixtures, seven expectations:

| case | with | without | to-tickets |
|---|---|---|---|
| T4 | 7/7 | 3/7 | 3/7 |

All three arms split the large "shift management" item and said so. Only the with arm kept every
increment at or under 60% Must and held contingency back; the other two front-load every Must. Found
in the with arm, outside the score:
- Increment 1 reached 57% only because of spreadsheet export, a `Proposed:` Could the PRD and spec never
  ask for. Unconfirmed proposals can pad the 60% denominator.
- It read "Go ahead and finish it" as confirming the priorities, sizes and export it had just asked
  about. It recorded no override, but claimed agreement the person had not given.
- Weaker domain analysis than the other arms: no slice creates a shift or sets its minimum, and
  drop-out (half the PRD goal) moved to increment 2 while increment 1 held reminders and export.
  Only the without arm named swap's workaround (drop out, then someone else signs up).

### 2026-11-12, T4 rerun after the fixes in 5b6fd06 (with arm; graded against the same without and to-tickets outputs)

| case | with | without | to-tickets |
|---|---|---|---|
| T4 | 7/7 (was 7/7, now under a stricter bar) | 3/7 | 3/7 |

This time the grader also failed any increment kept under 60% only by an unconfirmed proposal, and
any contingency made of one. All three earlier problems are fixed. The export stayed `Proposed:` and
counted toward neither. The reply said the go-ahead had not answered its questions and recorded
nothing. A shift-creation slice was added. Swap was demoted because dropping out and signing up
again does the same job. Still open: increment 1 holds swap (a Could) while drop-out and the day view
(Musts) wait for increment 2. It looks chosen to meet the 60% cap, not for value; the to-tickets arm
sequenced this best. A first rerun into the same directory was contaminated by a killed run's child
process and is not counted.

### 2026-11-12, T1-T3 regression after 5b6fd06 (with arm only)

Under the new rule, all three earlier clean with-arm outputs fail `check`: they used `Proposed:`
Coulds as contingency, and in this fixture the spec's own user stories 2 and 3 are unconfirmed
proposals. On the rerun, T1 finished clean. T2 and T3 stopped with the checks open and asked the
person to confirm stories 2 and 3; "those priorities are fine" did not answer that. No run recorded
an override, claimed agreement or added a Could to make the numbers pass. The cost in use: one more
question round when the scope really is unconfirmed.

### 2026-11-12, T1 and T4 after e1f51ce (layers from the spec; order by value)

With arm only, read directly (no blind grader). T4 quoted the spec's own layer sentence and used its
four names; every Must, including drop-out, now sits in week 1, with swap and the week view as week 1's
Coulds; `check` clean. T1 declared the five specific layers (core, microphone, speech model, cursor
typing, hotkey) instead of "adapters", and marked `layers_from` as `Proposed:` because the dictation spec
lists the adapters only as a proposal; it then asked the person to confirm the open proposals, as in
the regression run.

Routing (`claude plugin eval`, Sonnet, 10 runs per case, $11.77): 142/160. All 8 negative cases
and route-01 to route-06 are 10/10. Two prompts that check rather than build are missed:
"Check this ticket breakdown: is anything horizontal?" (2/10) and "Which of these tickets are
Must Haves for the first timebox?" (0/10).
