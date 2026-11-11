# DSDM: the points spec-to-tickets builds on

Paraphrased from *The DSDM Agile Project Framework* handbook (DSDM Consortium, now the Agile
Business Consortium; agilebusiness.org). Section numbers refer to that handbook. The method is free to
use; the handbook's text is copyright with all rights reserved, so the wording here is ours and nothing
is quoted. Read the handbook for the full method.

## Why DSDM and not just "agile"

DSDM fixes time, cost and quality up front and lets the set of features flex. A traditional project
treats everything as essential and lets the end date slip; DSDM keeps the date and decides in advance
what can be dropped. Prioritisation is therefore not a ranking exercise but the mechanism that protects
the deadline. (Ch. 10.3)

## The principles that matter here (Ch. 4)

DSDM has eight principles. Four drive this skill:

- **Focus on the business need.** Every decision is judged by what the business needs and when it
  needs it; the project is a means, not an end. The team guarantees a minimum usable set of features
  rather than everything. (Principle 1)
- **Deliver on time.** Timebox the work and protect the deadline by managing priorities, which builds
  confidence through predictable delivery. (Principle 2)
- **Build incrementally from firm foundations.** Understand the problem and the solution well enough
  to start, without analysis paralysis ("enough design up front"), then deliver in increments so that
  real benefit and feedback arrive early. Re-assess priorities after each increment. (Principle 5)
- **Develop iteratively.** Little is right first time; build feedback into every iteration, let most
  detail emerge later, and treat change as how the right solution is found. (Principle 6)

The others: collaborate, never compromise quality (agree the quality level at the start and test early
and continuously), communicate continuously and clearly, demonstrate control.

## MoSCoW (Ch. 10)

- **Must Have:** the Minimum Usable SubseT (MUST), which the project guarantees. A useful test: if this
  were missing, would delivering on the date still be worth it? If not (no point, not legal, not safe,
  no viable solution), it is a Must. (10.2.1)
- **Should Have:** important but not vital. Leaving it out hurts, perhaps needing a workaround, but the
  solution is still viable. The size of the pain, in business value or people affected, separates a
  Should from a Could. (10.2.2)
- **Could Have:** wanted but less important, with less impact if left out. Coulds are the main
  contingency: when the deadline is at risk, they are dropped first. (10.2.3)
- **Won't Have this time:** agreed not to be delivered in this timeframe and written down, so they are
  not quietly reintroduced and expectations stay honest. (10.2.4)

Why not high, medium and low: relative labels invite arguments about ordering and say nothing about
what will actually be delivered; each MoSCoW label sets an expectation. (10.1)

**Priorities belong to a timeframe.** One requirement can carry three priorities: for the project, for
the current increment, and for the current timebox. At timebox level most requirements are Won't Have
for now; only what the team will work on in that timebox gets a Must, Should or Could. (10.3)

## Balancing the mix (Ch. 10.4)

- Keep Must effort to the level the team is confident of delivering: **typically no more than 60%** of
  the effort for the timeframe. Above that, the risk of failure rises, unless estimates are known to be
  accurate, the approach is well understood, the team is performing, and the environment is low risk.
- Hold a pool of Coulds as contingency: **around 20%** of the effort.
- Won't Haves are left out when the effort is added up.
- Fewer Musts than 60% is fine, and gives more room to deliver Shoulds.

The numbers are DSDM's guidance for a typical project, not a law; what matters is visible flexibility in
what must be delivered.

## When the Musts will not fit (Ch. 17.2, statement 5)

DSDM's questionnaire for judging whether a project suits the method asks whether the requirements can
be prioritised so that scope, not the date, gives way. When the top-level list looks like nearly all
Musts, the handbook offers two moves, in this order:

- **Look below the top level.** A requirement that is a Must as a whole often breaks into parts where
  only some are Musts. Its own example, paraphrased: in a diary feature, making and cancelling an
  entry are Musts, while changing one is not, because cancelling and re-making it is a workaround.
- **Only then, contingency in time.** Add one or more contingency timeboxes at the end. Commit to the
  date that includes them, but plan to an earlier target date that does not. When the target is at
  risk, the least important work moves into the contingency timebox instead of being dropped. This
  works only while everyone treats the earlier date as the real one; otherwise the contingency is
  spent early and carelessly.

## Timeboxes (Ch. 13)

- A kick-off opens every timebox and a close-out finishes it. Between them, DSDM offers a structured
  style (investigation, about 10-20% of the timebox, to confirm deliverables, acceptance criteria and
  measures of success; then refinement; then consolidation, each ending in a review) or a free-format
  style. (13.2-13.3)
- The timebox's deliverables come with their own acceptance criteria, agreed at the start. (13.2)

## How spec-to-tickets uses this

| DSDM idea | in the skill |
|---|---|
| Minimum Usable SubseT | a Must must trace to the PRD's goal, success check or anti-goal |
| Coulds as contingency | `mix` check: no increment without a Could |
| 60% Must effort | `mix` check, with S/M/L sizes; override needs the person's own words |
| Won't Have this time | recorded in tickets.md, excluded from the effort sum |
| Priorities per timeframe | MoSCoW per increment, re-assessed after each one |
| Firm foundations, incremental delivery | increment 1 is a walking skeleton |
| Acceptance criteria per deliverable | each slice's criteria name what they prove |
