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
2. Run `adr-author/evals/run_cases.sh adr-author/evals/runs/<date>`, or by hand: for each case, open a session inside its `fixture` repository and send the `prompt`, twice: once
   with the skill installed and once without it (the baseline).
3. Run `scripts/check_record.py` on every record written, with `--repo` set to the fixture.
4. Grade every record with the reader grader prompt.
5. Grade each expectation as pass or fail with the evidence quoted. Save transcripts, records and
   grades under `adr-author/evals/runs/<date>/` (git-ignored).

v1 is evaluated under Claude Code with Sonnet as the session model. Results are reported per model,
never pooled, when other models are added.

## Results

All runs 2026-11-09, Claude Code with Sonnet as the session model, one run per case and arm (so a
single case can flip between runs). Graded by a fresh Opus subagent that did not write the skill;
grades with quoted evidence are in each run's `grades.json` (git-ignored). Both arms load the same
user-level configuration, so the baseline is not a factory-default agent.

Expectations passed, with the skill / without it. "r1 rules" excludes the figure-source
expectation, which was added after the first run.

| run | skill changes before it | with skill (r1 rules) | with skill (all) | baseline (r1 rules) | baseline (all) |
|---|---|---|---|---|---|
| r1 | first build | 54/57 | n/a | 36/57 | n/a |
| r2 | sources rule, approval, no placeholders, draft saved first | 55/57 | 63/65 | 34/57 | 41/65 |
| r4 | committed-record comparison, scratch dirs, draft shown, A2 prompt reworded | 57/57 | 65/65 | 36/57 | 43/65 |

Where the baseline lost points: it wrote a record for an undecided question (W6) and for a lint rule
(W5), picked one of two filename schemes without asking (W4), set status to Accepted unasked, and
added rationale or figures nobody gave ("December 2026", "14 days").

Cold reader (fresh Opus subagent, record only): with the skill, W1, W3 and A1 pass in r4; W2 fails
in every run on both arms, because the prompt gives no reason beyond "newcomers keep doing it". The
skill now asks what goes wrong without the decision instead of writing around the gap.

Routing (`claude plugin eval`, Sonnet): should-not cases 30/30 silent in r1 and 10/10 after the
description change; route-07 and route-10 went from 1/3 to 10/10 after the description named those
phrasings. Route-11 ("... ADR 3 is still right. Handle it.") fired 0/10: a request that vague does
not reach the skill. Naming the exception ("Record the exception.") does.

Known limits found by the evals and not fixed by an eval rerun since: a final review on
2026-11-09 found parsing and name-lookup defects (code fences, `f()` and `a.py:12` forms, dated
supersede links, headingless records, figure units, the script finder under symlinked installs);
they are fixed test-first in the commit that adds this section, but the behaviour cases have not
been rerun on that commit.
