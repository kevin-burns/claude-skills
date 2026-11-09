# adr-author evals

Three kinds of evidence, each graded by something other than the skill's author.

| what | where | graded by |
|---|---|---|
| behaviour cases W1-W6, A1-A2 | `evals.json` | the expectations, `check_record.py`, and the reader grader |
| a cold reader's view of each record | `reader-grader.md` | a fresh opus subagent with no context |
| routing: does the skill fire, and only when it should | `routing.json`, generated into the root `evals/` | `claude plugin eval` |
| publish gate (P1) | `../tests/test_publish_gate.py` | pytest, every run |

## Run the behaviour cases

1. Build the fixtures somewhere temporary:
   `python3 adr-author/evals/build_fixtures.py "$(mktemp -d)"`
2. For each case, open a session inside its `fixture` repository and send the `prompt`, twice: once
   with the skill installed and once without it (the baseline).
3. Run `scripts/check_record.py` on every record written, with `--repo` set to the fixture.
4. Grade every record with the reader grader prompt.
5. Grade each expectation as pass or fail with the evidence quoted. Save transcripts, records and
   grades under `adr-author/evals/runs/<date>/` (git-ignored).

v1 is evaluated under Claude Code with Sonnet as the session model. Results are reported per model,
never pooled, when other models are added.

## Results

None yet.
