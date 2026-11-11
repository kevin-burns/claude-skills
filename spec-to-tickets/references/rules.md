# The checks and why

| check | fails when | why |
|---|---|---|
| vertical | a `slice` touches one layer | feedback arrives only when the last layer exists; a thin slice through every layer gets it early |
| skeleton | increment 1 has no Must through every declared layer | the first increment proves the architecture end to end before anything is deepened |
| trace | a Must cites nothing, a turn that is not settled, or text not in the PRD | a Must is a Must because the PRD's goal, success check or anti-goal needs it |
| scope | a slice traces to nothing and is not `Proposed:` | no invented scope: the person sees every addition and confirms it |
| mix | an increment's Must effort is over 60%, or it has no Could | the Coulds are what gets dropped when the timebox runs short (DSDM, see dsdm.md) |
| acceptance | no criteria, or a criterion that names nothing it proves | the trace runs PRD → slice → test |
| blocks | an unknown blocker, or a cycle | a cycle means nothing can start |
| size | an `L` with no note | a slice is one context window, one pull request, and demoable on its own |

Horizontal work that has to be horizontal (a prefactor that makes the next slice easy, or a wide
change done as expand, migrate, contract) is labelled with its `kind` and exempt from `vertical`.

An override is the person's decision, never the agent's: `check_tickets.py accept` records it with
the quote of their own words, checked against their turn in the session transcript.
