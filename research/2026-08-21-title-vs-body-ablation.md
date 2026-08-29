# Ablation: does reading the pull-request body change the verdict, or only the confidence?

Raw measurement record, 21 August 2026. This is the primary data behind section 4, 5, 6, 7
and 8 of the verification-techniques briefing in this notebook.

## Design and result


Corpus: data/repos-2026-08-16.json, the same 159 merged PRs as the earlier passes.
Bodies: data/repos-2026-08-16-bodies.json, fetched 2026-08-21, 159/159, 0 failed.
Rubric: docs/RUBRIC.md as of 27e8d47 -- AFTER the 1.1 remediation term was added.

THREE ARMS, one variable. Same model and effort throughout, so movement is attributable to
the evidence and not to the rater. Changed-file paths were fetched and deliberately NOT
given to any arm: including them would move two variables at once.

A   title only                    3,536 tokens
A'  title only, replicate         identical input, second rater -- THE NOISE FLOOR
B   title + full body           117,911 tokens, untruncated

Untruncated on purpose: a null result had to be impossible to blame on the truncation.

RESULT
KEEP  UNSURE   CUT
A   title              44      26    89
A'  title replicate    41      19    99
B   title+body         46       8   105

A vs A'   agreement 84.3%   kappa 0.720   moved 25/159 (15.7%)   HARD FLIPS: 0
A vs B    agreement 74.8%   kappa 0.536   moved 40/159 (25.2%)   HARD FLIPS: 10

effect / noise = 1.60x

CORRECTED 2026-08-21, AND THE CORRECTION STRENGTHENS THE RESULT. The two kappas above are
correctly computed instances of the WRONG STATISTIC. They treat UNSURE as an ordinary
nominal category, which makes the arithmetic score KEEP-vs-UNSURE identically to
KEEP-vs-CUT -- hesitancy counted as reversal. Combined with the prevalence effect (CUT is
56-66% of every arm), that is the first Feinstein-Cicchetti paradox: high chance agreement
drags kappa down while raw agreement stays high.

The correct frame for a rater permitted to abstain is SELECTIVE PREDICTION -- classification
with a reject option, Chow (1970), formalised by El-Yaniv and Wiener (2010). Report two
axes: COVERAGE (both raters committed) and agreement on that covered subset.

A vs A'   coverage 124/159 = 78.0%   agreement 100.0%   conditional kappa 1.000    0 flips
A vs B    coverage 127/159 = 79.9%   agreement  92.1%   conditional kappa 0.818   10 flips

READ THAT AGAINST THE NOMINAL FIGURES. The headline is not "1.60x above noise, marginal".
It is ZERO RATER NOISE AGAINST TEN REVERSALS. Restricted to items where both raters
committed to a definite verdict, two title-only runs agreed PERFECTLY. The nominal 0.720
was penalising them for hesitancy they were right to have.

The original figures are left in place rather than edited out: they were published, and a
publication whose premise is verifiability does not quietly repair itself (RUBRIC.md,
Part 2).

PROVENANCE OF THE CORRECTION, because it matters. The framing came from a NotebookLM pass
over the evaluation literature. ITS REASONING WAS RIGHT AND ITS ARITHMETIC WAS NOT: it
asserted coverage 114/159 and 129/159 and a conditional kappa of 0.865, and three of those
four numbers are wrong. The figures above were recomputed locally from the 159 rows below.
Cite the argument, never the numbers, from a source you have not checked.

THE RATIO IS THE WEAK HALF OF THIS RESULT. 1.60x is marginal, one run per arm, n=159.
THE STRONG HALF IS 0 HARD FLIPS AGAINST 10. Two title-only runs never once disagreed about
a definite verdict -- every one of their 25 disagreements involved UNSURE. The body reversed
ten confident verdicts, and in EIGHT of the ten the two title-only runs had AGREED with each
other. That is not rater noise; it is a stable, confident, and different answer.

DIRECTION MATTERS AND THE ERRORS ARE NOT SYMMETRIC.
CUT -> KEEP  6 items -- title-only DROPS publishable items. Invisible: a false negative
never reaches triage, so nobody sees what was lost.
KEEP -> CUT  4 items -- title-only promotes items that do not qualify. Cheap: a human
meets them in triage.

FOUR OF THE SIX CUT->KEEP FLIPS ARE 'remediation'. The term added to 1.1 on 2026-08-21 is
SYSTEMATICALLY INVISIBLE IN A TITLE: a title says what changed, and whether a reader needs
it to diagnose a failure they are already having is in the description. The newest keep
reason is the one title-only triage cannot see.

UNSURE COLLAPSED 26 -> 8. Of A's 26 UNSUREs the body resolved 24: nineteen to CUT, five to
KEEP. So most title-level uncertainty was over-caution, but not all of it.

WHAT THIS DOES NOT ESTABLISH. That arm B is CORRECT. There is no ground truth here; B has
strictly more evidence, which is a reason to prefer it and not a proof. Same model in all
three arms: internally comparable, and NOT comparable to the kappa 0.545 inter-rater
baseline (different model, different rubric version) or to 0.832 (self-consistency, but a
different rubric again).

CONTROLS: items 15 and 55 have no body at all. Both behaved as they must -- #55 stable KEEP
across all three arms, #15 UNSURE in A and CUT in both A' and B, i.e. B could not have used
a body it did not have.

Columns: n, A, A_replicate, B, A_reason, B_reason

## Per-item verdicts

159 merged pull requests. Columns: item number, arm A (title only), arm A-prime
(title only, replicate), arm B (title plus full body), then the stated reason from
arm A and from arm B.

| n | A title | A' replicate | B title+body | A reason | B reason |
|---|---|---|---|---|---|
| 1 | UNSURE | CUT | CUT | docs vs announcement | docs |
| 2 | KEEP | KEEP | CUT | deprecation date | ui-cosmetic |
| 3 | KEEP | KEEP | KEEP | contract change | capability |
| 4 | KEEP | KEEP | KEEP | deprecation announcement | capability |
| 5 | CUT | UNSURE | CUT | UI affordance | internal |
| 6 | CUT | CUT | CUT | cosmetic labels | ui-copy |
| 7 | UNSURE | CUT | KEEP | scope unclear | capability |
| 8 | CUT | CUT | CUT | internal rename | internal |
| 9 | CUT | CUT | CUT | dead code | internal |
| 10 | CUT | CUT | UNSURE | internal refactor | unclear |
| 11 | KEEP | KEEP | UNSURE | privacy capability | telemetry |
| 12 | CUT | CUT | CUT | dead code | internal |
| 13 | CUT | CUT | CUT | UI affordance | ui-affordance |
| 14 | CUT | CUT | CUT | internal cleanup | internal |
| 15 | UNSURE | CUT | CUT | telemetry exposure unclear | internal |
| 16 | CUT | CUT | CUT | UI cosmetic | ui |
| 17 | CUT | CUT | CUT | repo hygiene | internal |
| 18 | UNSURE | UNSURE | CUT | contract unclear | ui |
| 19 | CUT | CUT | CUT | test infra | internal |
| 20 | CUT | CUT | CUT | cleanup | internal |
| 21 | UNSURE | KEEP | CUT | validation unclear | internal |
| 22 | CUT | CUT | CUT | cosmetic not limit | ui |
| 23 | CUT | CUT | CUT | UI internal | internal |
| 24 | UNSURE | UNSURE | CUT | capability unclear | internal |
| 25 | CUT | CUT | CUT | repo hygiene | internal |
| 26 | CUT | CUT | CUT | internal infra | internal |
| 27 | KEEP | KEEP | KEEP | price | price |
| 28 | KEEP | UNSURE | UNSURE | version support | version |
| 29 | CUT | CUT | CUT | internal dependency | internal |
| 30 | CUT | CUT | CUT | docs redirect | docs |
| 31 | UNSURE | CUT | UNSURE | experimental status unclear | docs |
| 32 | CUT | CUT | CUT | repo hygiene | internal |
| 33 | KEEP | UNSURE | KEEP | remediation | remediation |
| 34 | KEEP | UNSURE | KEEP | remediation | remediation |
| 35 | KEEP | KEEP | KEEP | capability removed | capability |
| 36 | KEEP | KEEP | KEEP | remediation | remediation |
| 37 | KEEP | KEEP | KEEP | contract breaking | remediation |
| 38 | CUT | CUT | CUT | CI internal | internal |
| 39 | CUT | CUT | CUT | test internal | internal |
| 40 | CUT | CUT | KEEP | internal build | version |
| 41 | UNSURE | CUT | CUT | public API unclear | internal |
| 42 | CUT | CUT | CUT | dead code | internal |
| 43 | KEEP | KEEP | KEEP | capability model | capability |
| 44 | KEEP | KEEP | KEEP | capability model | capability |
| 45 | KEEP | KEEP | UNSURE | remediation | unclear |
| 46 | CUT | CUT | CUT | dead code | cleanup |
| 47 | CUT | CUT | CUT | dead code | internal |
| 48 | CUT | CUT | CUT | dead code | internal |
| 49 | CUT | CUT | CUT | internal metadata | internal |
| 50 | CUT | CUT | CUT | test infra | internal |
| 51 | UNSURE | UNSURE | CUT | config unclear | cleanup |
| 52 | CUT | CUT | KEEP | internal workaround | remediation |
| 53 | UNSURE | CUT | CUT | backend scope unclear | internal |
| 54 | UNSURE | CUT | CUT | cryptic internal | no-mechanism |
| 55 | KEEP | KEEP | KEEP | capability status | capability |
| 56 | KEEP | KEEP | KEEP | remediation | remediation |
| 57 | UNSURE | UNSURE | CUT | model gating unclear | internal |
| 58 | CUT | CUT | CUT | perf | perf |
| 59 | KEEP | KEEP | KEEP | contract enforcement | capability |
| 60 | CUT | CUT | CUT | dead code | internal |
| 61 | CUT | CUT | CUT | cosmetic warning | no-mechanism |
| 62 | CUT | CUT | CUT | docs cosmetic | docs |
| 63 | CUT | CUT | CUT | dead code | internal |
| 64 | CUT | CUT | CUT | cleanup | internal |
| 65 | KEEP | UNSURE | CUT | remediation capability | perf |
| 66 | UNSURE | UNSURE | UNSURE | build option unclear | capability |
| 67 | UNSURE | CUT | KEEP | dependency template unclear | version |
| 68 | CUT | CUT | CUT | dead code | internal |
| 69 | KEEP | UNSURE | KEEP | remediation dependency | remediation |
| 70 | KEEP | KEEP | KEEP | capability added | capability |
| 71 | CUT | CUT | CUT | test internal | internal |
| 72 | CUT | CUT | CUT | internal benchmark | internal |
| 73 | CUT | CUT | CUT | perf | perf |
| 74 | UNSURE | UNSURE | CUT | version dependency unclear | perf |
| 75 | CUT | CUT | CUT | docs cosmetic | docs |
| 76 | KEEP | KEEP | CUT | capability removed | cleanup |
| 77 | UNSURE | CUT | KEEP | fix scope unclear | remediation |
| 78 | CUT | CUT | CUT | perf | perf |
| 79 | CUT | CUT | KEEP | dead code | remediation |
| 80 | CUT | CUT | KEEP | docs policy | capability |
| 81 | KEEP | KEEP | KEEP | capability removed | capability |
| 82 | KEEP | KEEP | KEEP | contract deprecation | capability |
| 83 | KEEP | KEEP | KEEP | contract deprecation | capability |
| 84 | CUT | CUT | CUT | dup | dup |
| 85 | KEEP | KEEP | KEEP | capability deprecation | capability |
| 86 | UNSURE | KEEP | CUT | rename scope unclear | internal |
| 87 | UNSURE | UNSURE | CUT | internal naming unclear | internal |
| 88 | KEEP | KEEP | KEEP | deprecation warning | capability |
| 89 | CUT | CUT | CUT | dead code | internal |
| 90 | UNSURE | CUT | KEEP | capability unclear | capability |
| 91 | UNSURE | UNSURE | CUT | config unclear | internal |
| 92 | CUT | CUT | CUT | CI internal | internal |
| 93 | CUT | UNSURE | KEEP | docs correction | remediation |
| 94 | UNSURE | CUT | CUT | behavior unclear | internal |
| 95 | CUT | CUT | CUT | CI internal | internal |
| 96 | CUT | CUT | CUT | CI internal | internal |
| 97 | CUT | CUT | CUT | dup | dup |
| 98 | CUT | CUT | CUT | test infra | internal |
| 99 | UNSURE | CUT | CUT | internal API unclear | internal |
| 100 | KEEP | KEEP | KEEP | remediation | remediation |
| 101 | CUT | CUT | CUT | dup | internal |
| 102 | CUT | CUT | CUT | internal benchmark | internal |
| 103 | KEEP | KEEP | KEEP | remediation | remediation |
| 104 | KEEP | KEEP | KEEP | price version | price |
| 105 | KEEP | KEEP | KEEP | version dates | capability |
| 106 | CUT | CUT | CUT | test infra | internal |
| 107 | CUT | CUT | CUT | UI cosmetic | ui |
| 108 | KEEP | KEEP | KEEP | capability | capability |
| 109 | CUT | CUT | KEEP | test infra | remediation |
| 110 | CUT | CUT | CUT | internal rename | internal |
| 111 | CUT | CUT | CUT | test internal | internal |
| 112 | CUT | CUT | CUT | internal tooling | internal |
| 113 | CUT | CUT | CUT | internal tooling | internal |
| 114 | CUT | CUT | CUT | test infra | internal |
| 115 | CUT | CUT | CUT | test internal | internal |
| 116 | CUT | UNSURE | CUT | test suite | internal |
| 117 | CUT | CUT | CUT | internal tooling | internal |
| 118 | CUT | CUT | CUT | test infra | internal |
| 119 | CUT | CUT | CUT | internal typing | internal |
| 120 | CUT | CUT | CUT | trivial cleanup | internal |
| 121 | CUT | CUT | CUT | internal lint | internal |
| 122 | CUT | CUT | CUT | dead code | internal |
| 123 | CUT | CUT | CUT | test compat | internal |
| 124 | UNSURE | CUT | CUT | rename note unclear | ui |
| 125 | CUT | CUT | CUT | test infra | internal |
| 126 | CUT | CUT | CUT | test infra | internal |
| 127 | CUT | CUT | CUT | UI affordance | ui-affordance |
| 128 | CUT | CUT | CUT | test infra | internal |
| 129 | CUT | CUT | CUT | UI cosmetic | ui |
| 130 | CUT | CUT | CUT | repo hygiene | internal |
| 131 | CUT | CUT | CUT | trivial docstring | internal |
| 132 | CUT | CUT | CUT | test coverage | internal |
| 133 | CUT | CUT | CUT | test coverage | internal |
| 134 | CUT | CUT | CUT | test coverage | internal |
| 135 | KEEP | KEEP | KEEP | default capability | capability |
| 136 | CUT | CUT | CUT | test infra | internal |
| 137 | CUT | CUT | CUT | internal process | internal |
| 138 | KEEP | KEEP | KEEP | contract removal | capability |
| 139 | KEEP | KEEP | KEEP | contract schema | capability |
| 140 | CUT | CUT | CUT | dead code | internal |
| 141 | CUT | CUT | CUT | test infra | internal |
| 142 | UNSURE | UNSURE | CUT | debug assertion unclear | internal |
| 143 | UNSURE | CUT | CUT | safety internal unclear | internal |
| 144 | KEEP | KEEP | CUT | deprecation version | internal |
| 145 | CUT | CUT | CUT | test infra | internal |
| 146 | CUT | CUT | CUT | dead code | internal |
| 147 | KEEP | KEEP | KEEP | remediation | remediation |
| 148 | KEEP | KEEP | KEEP | capability irreversible | capability |
| 149 | KEEP | KEEP | KEEP | remediation | remediation |
| 150 | UNSURE | UNSURE | KEEP | internal mechanism unclear | remediation |
| 151 | KEEP | KEEP | UNSURE | contract semconv | unclear |
| 152 | KEEP | KEEP | KEEP | contract rename | capability |
| 153 | CUT | UNSURE | CUT | docs guidance | docs |
| 154 | KEEP | KEEP | KEEP | remediation crash | remediation |
| 155 | KEEP | KEEP | UNSURE | format capability | format |
| 156 | KEEP | KEEP | KEEP | capability removed | capability |
| 157 | CUT | CUT | CUT | cleanup | internal |
| 158 | CUT | CUT | CUT | perf internal | perf |
| 159 | KEEP | KEEP | KEEP | capability removed | capability |
