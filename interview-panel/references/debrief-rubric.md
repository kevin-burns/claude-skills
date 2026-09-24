# Interview Panel — Debrief Rubric

What an independent reviewer looks for in a saved transcript of a completed panel session,
against the candidate's evidence base. This runs *after* the roleplay, never during it — the
panel (see `panel-rules.md`) does not coach mid-run; this is where the coaching happens.

## Hard rule: no invented facts

The reviewer works from two sources only:

1. **The transcript** — what the candidate and the panel actually said in this session.
2. **The candidate's evidence base** — a separate document of the candidate's real experience,
   supplied alongside the transcript.

The reviewer never invents, infers, or assumes a fact about the candidate that isn't in one of
those two sources. If the transcript doesn't say how a story ended, the reviewer says "the
transcript doesn't show the result" — it does not guess a plausible one. If the evidence base
doesn't contain a matching example for a question the candidate answered weakly, the reviewer
says "no matching evidence found in the evidence base" — it does not invent one to fill the gap.
Every claim the reviewer makes about what the candidate could have said must cite the specific
line or entry in the evidence base it came from.

## Per-answer review

For each question the candidate answered, look at:

**Structure (situation → action → result).**
Does the answer identify a specific situation, what the candidate actually did, and what
resulted — in that order, or recoverable in that order? Flag answers that skip straight to
result with no situation, or that describe the action taken by "the team" with the candidate's
own contribution never isolated.

**Specificity.**
Does the answer name a real, concrete detail — a decision, a number, a timeframe, a named
mechanism — or does it stay at the level of general principle? An answer can be well-structured
and still fall short here if every noun in it could apply to any situation.

**Directness.**
Does the answer actually answer the question asked, or does it pivot to a more comfortable
adjacent topic? Note where the candidate answered a question they wished had been asked instead
of the one that was.

**Length.**
Flag answers that ran long enough to trigger the panel's rambling interruption (per
the persona files, roughly 2 minutes) and never reached a landing point unassisted. Also flag
answers that were too short to demonstrate the competency being tested, even if technically
on-topic.

**Evidence used vs. evidence available.**
Compare what the candidate said to what's in the evidence base. If the evidence base has a
stronger, more specific example for the same competency that the candidate didn't use, cite the
exact evidence-base line and note it as evidence left on the table. If the candidate used the
strongest available example, say so explicitly — this comparison should surface both directions,
not only gaps.

## Per-session review

**Topic coverage.**
Using each question's `topic` field, list which topics were actually asked in this session
and which strong-answer criteria were met versus missed, per topic. A session that never touched
`risk-security` or `finops` should say so plainly, not be silently reviewed as if those topics
didn't exist.

**Consistency across answers.**
Cross-check claims the candidate made in different answers against each other — for example, the
reason given for leaving a current role (motivation) against the frustration described elsewhere
in the session, or a claimed delegation style (leadership) against how the candidate described
handling a peer disagreement (conflict). Note any answer that contradicts an earlier one, quoting
both.

**How the candidate handled each seat.**
Describe each seat's portion separately — a candidate can be
strong in one seat and weak in the other, and averaging them together hides that. Note any
difference in how the candidate handled pushback from each persona (per that seat's persona file's
interruption and vague-answer behavior).

**Questions the candidate asked at the end.**
Evaluate against the closing-questions rubric in the bank, or failing that: specific and researched versus generic, at least
one substantive question versus logistics-only, engagement with the answer given versus reading
from a list.

## Stance: a learning tool, not a grade

The debrief is for reflection. **No answer is marked wrong, incorrect, failed or passed.** For
each answer that fell short, say three things plainly:

- **What you said.** Quote or closely paraphrase the transcript.
- **What the panel was listening for.** Take this from the question's `strong answer contains`
  and, where the question has one, its `why they ask`. Explain *why* that matters to this seat,
  so the candidate learns the intent and not only the checklist.
- **The step from one to the other.** One concrete change, ideally drawn from the evidence base
  ("the landing-zone migration would have answered this: …").

This is not permission to soften. A missed point is still named as missed, and in the same
words the panel would have used to judge it. What changes is the frame: an explanation of what
was expected replaces a verdict. Strengths get the same treatment: say *why* it landed, so the
candidate can do it on purpose next time.

## Output format

The debrief must produce, in this order:

1. **What landed.** Three moments, each tied to a specific question and a specific thing the
   candidate said, and why each worked for that seat.
2. **Three things to work on.** Each is specific and actionable: what to change about a kind
   of answer, not "be more confident".
3. **Question by question.** One entry per question asked: question ID and title, seat, what
   you said (1–2 lines), what the panel was listening for (1–2 lines), and the step between
   them. Where the answer covered it, say so and move on.
4. **Evidence left on the table.** Moments where the evidence base held a stronger or more
   specific example than the one used, each with the exact evidence-base citation. If there
   are none, say so; do not omit the section.
5. **Reflection prompts.** Three to five questions for the candidate to answer in their own
   words before the next run, e.g. "Which answer would you give differently if the Head of
   Cloud asked it again, and what would you open with?" These are for them to think through,
   not for the reviewer to answer.
6. **Three answers to rehearse again.** The questions (by ID) most worth another pass, each
   with a one-line reason tied to what actually happened in the transcript.

## What this rubric does not do

It does not grade the candidate against a hypothetical ideal candidate, does not compare the
candidate to other candidates, and does not predict a hiring outcome. It reviews what happened in
this specific transcript against what's actually available in the evidence base — nothing more.
