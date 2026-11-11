# The checks and why

| check | fails when | why |
|---|---|---|
| vertical | a `slice` touches one layer | feedback arrives only when the last layer exists; a thin slice through every layer gets it early |
| skeleton | increment 1 has no Must through every declared layer | the first increment proves the architecture end to end before anything is deepened |
| trace | a Must cites nothing or `Proposed:`; cites a turn that is not the settled goal, success check or anti-goal in a verified readiness.json; or quotes fewer than four words, or words not in the PRD's goal, success check or anti-goal | a Must is a Must because the PRD's goal, success check or anti-goal needs it |
| scope | a Should or Could traces to nothing, to a turn that is not the person's, or to words in neither the PRD nor the spec, and is not `Proposed:` | no invented scope: the person sees every addition and confirms it |
| mix | an increment's Must effort is over 60% | DSDM's guidance for confidence in the Musts (see dsdm.md) |
| contingency | an increment has no Could | the Coulds are what gets dropped when the timebox runs short |
| acceptance | no criteria, or a criterion that names nothing it proves | the trace runs PRD → slice → test |
| specifics | a criterion adds a figure ("five-minute", "95%") or a capitalised name ("TextEdit") the PRD and spec do not contain, and does not start `Proposed:` | a testable criterion often needs a number nobody chose; marking it makes it the person's choice, not a silent invention. New scope in plain lowercase words ("starts at login") has no surface form a script can see, so the person's review still matters |
| blocks | an unknown blocker, or a cycle | a cycle means nothing can start |
| size | an `L` with no note | a slice is one context window, one pull request, and demoable on its own |

Horizontal work that has to be horizontal (a prefactor that makes the next slice easy, or a wide
change done as expand, migrate, contract) is labelled with its `kind` and exempt from `vertical`.

An override is the person's decision, never the agent's. `check_tickets.py accept` records it only
when it matches a current finding, with the turn and quote of the person's own words. When a session
transcript can be read (through spec-ready), the quote is checked against that turn when it is
recorded and again on every `check`; an entry missing its turn, quote or mode is not applied. When no
transcript can be read, the override is recorded as attested: `check` then exits 2 and lists it, so
the person sees that their words were not checked. A hand-edited override is still possible; `check`
shows every override it applies, which is what makes one visible.
