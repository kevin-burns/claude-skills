# Interview Panel — Debrief Rubric

What an independent reviewer scores from a saved transcript of a completed panel session,
against the candidate's evidence base. This runs *after* the roleplay, never during it — the
panel in `personas.md` does not coach mid-run; this is where the coaching happens.

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

## Per-answer scoring

For each question the candidate answered, score:

**Structure (situation → action → result).**
Does the answer identify a specific situation, what the candidate actually did, and what
resulted — in that order, or recoverable in that order? Flag answers that skip straight to
result with no situation, or that describe the action taken by "the team" with the candidate's
own contribution never isolated.

**Specificity.**
Does the answer name a real, concrete detail — a decision, a number, a timeframe, a named
mechanism — or does it stay at the level of general principle? An answer can be well-structured
and still score poorly here if every noun in it could apply to any situation.

**Directness.**
Does the answer actually answer the question asked, or does it pivot to a more comfortable
adjacent topic? Note where the candidate answered a question they wished had been asked instead
of the one that was.

**Length.**
Flag answers that ran long enough to trigger the panel's rambling interruption (per
`personas.md`, roughly 2 minutes) and never reached a landing point unassisted. Also flag
answers that were too short to demonstrate the competency being tested, even if technically
on-topic.

**Evidence used vs. evidence available.**
Compare what the candidate said to what's in the evidence base. If the evidence base has a
stronger, more specific example for the same competency that the candidate didn't use, cite the
exact evidence-base line and note it as evidence left on the table. If the candidate used the
strongest available example, say so explicitly — this comparison should surface both directions,
not only gaps.

## Per-session scoring

**Topic coverage.**
Using the `topic` field from `bank.md`, list which topics were actually asked in this session
and which strong-answer criteria were met versus missed, per topic. A session that never touched
`risk-security` or `finops` should say so plainly, not be silently scored as if those topics
didn't exist.

**Consistency across answers.**
Cross-check claims the candidate made in different answers against each other — for example, the
reason given for leaving a current role (motivation) against the frustration described elsewhere
in the session, or a claimed delegation style (leadership) against how the candidate described
handling a peer disagreement (conflict). Note any answer that contradicts an earlier one, quoting
both.

**How the candidate handled each seat.**
Score the Head of Cloud portion and the Head of HR portion separately — a candidate can be
strong in one seat and weak in the other, and averaging them together hides that. Note any
difference in how the candidate handled pushback from each persona (per `personas.md`'s
interruption and vague-answer behavior).

**Questions the candidate asked at the end.**
Evaluate against Q50's strong-answer criteria: specific and researched versus generic, at least
one substantive question versus logistics-only, engagement with the answer given versus reading
from a list.

## Output format

The debrief must produce, in this order:

1. **Top 3 strengths** — each tied to a specific question and a specific thing the candidate
   said, not a general impression.
2. **Top 3 fixes** — each actionable and specific: what to change about a specific type of
   answer, not "be more confident."
3. **Per-question table** — one row per question asked, columns: question ID and title, seat,
   topic, structure score, specificity score, directness, one-line note.
4. **Evidence left on the table** — a list of moments where the evidence base had a stronger or
   more specific example than the one the candidate used, each with the exact evidence-base
   citation (line or entry) the candidate could have drawn on. If none, say so explicitly rather
   than omitting the section.
5. **3 answers to rehearse again** — the three specific questions (by ID) most worth practicing
   before a real panel, with a one-line reason each tied to what actually happened in the
   transcript.

## What this rubric does not do

It does not score the candidate against a hypothetical ideal candidate, does not compare the
candidate to other candidates, and does not predict a hiring outcome. It scores what happened in
this specific transcript against what's actually available in the evidence base — nothing more.
