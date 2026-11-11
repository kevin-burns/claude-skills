---
name: spec-ready
license: MIT
description: >-
  Check that a plan is ready to spec before anyone writes one, then write the PRD (why) and the spec (how). A script reads the person's own turns from the session transcript and has an independent verifier confirm each required item (goal, who it is for, non-goals, anti-goal, success check, verification strategy, boundaries touched); anything missing comes back as one round of questions, least-certain first. Use after an interview or brainstorm and before an implementation plan: "is this ready to spec", "write the PRD", "turn this into a spec", "are we done planning". Not an interviewer from scratch (frontier-rounds, brainstorming) and not the implementation plan (writing-plans).
---

# spec-ready

Planning with an agent usually ends when the agent decides it understands, and agents over-claim.
This skill answers one question before a spec is written: **has the person actually decided the
things a spec depends on?** It answers from the person's own turns in the session transcript, which
the harness wrote and you did not, checked by a verifier the script calls. You propose; the script
decides.

## The rules above all others

1. **Evidence comes from the person, not the agent.** An item is settled only when it cites one of
   the person's turns and a verifier the script calls agrees that turn states it, quoting the exact
   words it relied on. Your summaries, ledgers and playbacks are never evidence.
2. **Never pretend to be verified.** With no readable transcript the gate runs in attested mode
   (exit 2) and says so; the PRD header then reads `Readiness: attested`.
3. **No invented facts.** Every decision line in the PRD cites its turn as `[turn:<id>]`. A figure
   with no source is refused. Guesses go under Assumptions, labelled.
4. **No personal data in the skill.** Machine settings come from environment variables the user sets.

## Steps

Scripts live in this skill's `scripts/` directory; run them with `uv run` or `python3`, always
from the repository root (the gate finds the session transcript and `.spec-ready/items.json` from
there), and give the Bash call a timeout of at least 180000 ms: verifier calls run in parallel but
each may take up to a minute. Work in a scratch directory `$D` (`mktemp -d`) until the output
location is confirmed.

1. **Propose rows.** `gate.py turns` lists the person's turns with their ids. For each required
   item, find the turn that states it and write `$D/proposals.json`: a list of
   `{"item", "turn", "status": "settled" | "guessed", "statement"}`. `statement` is your one-line
   paraphrase, used as the recommendation if the item is asked. Only `risks` may be `guessed`.
2. **Gate.** `gate.py check --proposals $D/proposals.json --out $D`. It finds the transcript
   itself, calls the verifiers it chooses, writes `$D/readiness.json` and prints the open questions.
   Exit 0 ready, 1 items open, 2 no transcript, 4 no verifier could run.
3. **Exit 4, or "no verifier available".** On exit 4 the gate printed "verifier unavailable" and
   why (a broken login, for example): tell the person, since they may want to fix it. Otherwise,
   for each item dispatch a fresh subagent and paste the output of `gate.py brief` verbatim as its
   whole prompt (`gate.py brief --item <key> --turn <id>`); collect its JSON replies into
   `$D/answers.json` keyed by item, and re-run step 2 with
   `--answers $D/answers.json --answers-from subagent`. You never answer a brief yourself while a subagent tool exists; only without one, use `--answers-from session-model`, and the PRD will
   say the check was self-assessed.
4. **Ask.** When items are open, ask them all in one round, least-certain first, in the order the
   gate printed, each with your recommendation:

   ```
   ❓ **Q1** — **<item label>**: <the gate's question>

   ➡️ <your recommendation, and the reason in a clause>
   ```

   The person's answers are new turns. Update `proposals.json` to cite them and go to step 2.
   **Run gate.py override only when the person says so**: when they tell you a verifier got an item
   wrong, run `gate.py override --out $D --item <key> --turn <id> --quote "<their words>"`, where
   the turn is the one in which they said so and the quote is copied from it. The gate checks the
   quote is in that turn and records the override as a calibration label.
5. **Exit 2 (attested).** Tell the person no transcript could be read, so their decisions cannot be
   checked against their own words, and nothing is settled. Continue only if the person explicitly agrees to continue unverified; then run
   `gate.py accept-attested --out $D --reason "<their words>"`.
6. **Boundaries.** If the boundaries item names a boundary (not "none"), check the implementation
   decisions against the matching file of the `software-design-rules` skill when it is installed;
   otherwise ask the questions in `references/boundary-questions.md`. Record which rules were
   applied or knowingly broken in the spec.
7. **Write.** Find where this repository keeps specs (`docs/specs/`, `docs/superpowers/specs/`,
   `docs/prd/`, an existing pattern); otherwise propose `docs/specs/<date>-<slug>/`. The person
   confirms the path. Copy `readiness.json` there, then write `prd.md` from
   `references/prd-template.md` (its `Readiness:` and `Verifier:` header lines copy `mode` and
   `verification` from readiness.json) and `spec.md` from `references/spec-template.md`. Run
   `check_sources.py <dir>/prd.md <dir>/readiness.json --spec <dir>/spec.md` and fix every
   finding. A question nobody has answered goes under Open questions in the PRD, never under
   Assumptions; a user story or out-of-scope line nobody stated starts `Proposed:`.

Never write prd.md or spec.md while gate.py exits non-zero, except after exit 2 when the person
explicitly agrees to continue unverified.

## After writing

The next step is an implementation plan (`superpowers:writing-plans`). Offer adr-author for a
contested decision worth a record. Create tickets only when the person asks, through what they use:
the `use-linearis` skill (linearis), beads (`bd create`), or `gh issue create`.

## Verifiers

The script picks them, strongest first, and records which ran:

1. headless `claude -p` on Haiku, with no tools and no saved session;
2. a local model through Ollama, alongside 1, when `SPEC_READY_DECIDER=ollama:<model>` and
   `OLLAMA_HOST` are set; a disagreement between them becomes a question;
3. a fresh subagent given the script-built brief (step 3);
4. you, as a last resort, labelled `session-model`.

Every verifier must quote the span of the turn it relied on; a yes whose words are not in the turn
counts as unsure.

## Optional guard

An opt-in PreToolUse hook, `hooks/guard.py`, refuses writes to `prd.md` or `spec.md` while the
`readiness.json` beside them has not passed. The skill never installs it; README.md shows how.

## Credit

The PRD and spec sections adapt Matt Pocock's `to-spec`, and the question format his `grilling`
(github.com/mattpocock/skills, MIT). It sits between superpowers' brainstorming and writing-plans.
