# Council harness

Two questions about `design-council`, neither of which the ablation harness in
`../ablation/` can answer — its arms are built from `clear-and-human`, and its `run.sh`
disallows the Read tool, which is the exact mechanism a pointer depends on.

## 1. Anchoring (`anchor_*`)

design-council's own **first documented failure mode** is members echoing each other, and
its mitigation is procedural: "read and respond one at a time". That cannot work. Reading
one at a time stops *deliberate* echoing; it does nothing about member six having members
one to five sitting in its context.

This measures whether it actually happens. One member is run in two conditions against the
same brief:

  FIRST  nothing precedes it
  LAST   five other members' contributions precede it, byte-identical across replicates

The metric is **borrowed vocabulary**: content words that appear in the prefix and *not* in
the brief, counted in the target member's own output. A term the target could only have got
from its predecessors. If the LAST condition borrows no more than the FIRST condition, the
architecture's anchoring risk is theoretical and the sequential design is fine.

Read the result the way `../ablation/` reads its own: a difference is only a difference if
it beats the replicate-to-replicate noise floor within each condition.

## 2. Pointer firing (`pointer_*`)

Whether a member with a `## What to consult` pointer actually reads the file. Needs Read
*allowed* and the skills on disk — the opposite of the ablation sandbox.

## Result, 2026-08-18 — anchoring is real, and the designed metric was the weakest evidence for it

Target `pragmatist`, five preceding members, five replicates per condition. $1.33 for 15 runs (10 matrix cells plus 5 one-off prefix generations).

| signal | FIRST | LAST | reading |
|---|---|---|---|
| borrowed-vocabulary rate | 0.457 | 0.484 | +0.027, p=0.083, **1.10× the noise floor — not significant** |
| output length (raw words) | 605 | 697 | **+15%, exact p=0.0119** |
| borrowed-rate variance | sd 0.0375 | sd 0.0114 | **10.9× tighter** |
| names a preceding member | 0 of 5 | 2 of 5 | hand-verified; "architect", "data engineer" |

**The metric this harness was built around barely moved, and the reason is a design fault
worth keeping.** Borrowed vocabulary sits near 0.46 in *both* conditions, because two
independent readings of the same brief converge on the same technical words anyway —
p99, precompute, staleness, fan-out. A metric with a 46% floor has almost no headroom for
the effect to show up in. Build the baseline into the design next time: if the control
condition already scores half, the instrument is measuring the domain, not the treatment.

**What did show it.** LAST outputs are longer, far more consistent with each other, and two
of five name the members that preceded them — which the FIRST condition cannot do by
construction. The variance collapse is the sharpest signal and the most damaging one: a
council's proposers are supposed to *vary*, since "the disagreement is the finding". Members
that have read each other converge.

**Scope, honestly.** One member, one brief, n=5, and the naming evidence is 2 runs. Enough
to support isolating the red team — the seat where contamination does the most harm, since
it reviews a synthesis it would otherwise have watched being written. Not enough to justify
rebuilding all seven proposers as sub-agents. Widen to two more members and a second brief
before going further.
