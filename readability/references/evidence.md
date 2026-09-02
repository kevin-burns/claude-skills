# What the research actually says

Every rule in this skill traces to something here. Read this before arguing with the skill,
and before adding a metric to it.

## The formulas are not valid for this material, and nobody knows whether they are

**Redish, J. (2000). "Readability formulas have even more limitations than Klare discusses."**
*ACM Journal of Computer Documentation* 24(1), 132–137.
Read in full 2026-09-01: `redish.net/wp-content/uploads/Redish_on_Readability_Formulas.pdf`

Three things from it, verbatim:

> "How valid are readability formulas for technical material for adult readers? No one knows."

> Citing Duffy (1985) on the grade-level criterion — 50% of children at a grade level got 50%
> of the questions right: **"Should we be happy if 50% of our readers understand 50% of our
> documents?"**

> Formulas "say nothing about the causes of any problems people might have."

That last one is the design of this skill in a sentence. A formula correlates with
comprehension; it does not locate a defect. Everything `cohesion_report.py` prints names a
line, because a location can be acted on and a number cannot.

Redish also records that teams game the scores by adding words to the "acceptable" list with
no research showing readers know them — which is what a domain-vocabulary exemption would be,
if it fed a score. Here it feeds nothing: `--terms` only stops known jargon crowding the
un-glossed list.

## The obvious conclusion about expert readers is wrong

**O'Reilly, T. & McNamara, D. S. (2007). "Reversing the reverse cohesion effect: Good texts can
be better for strategic, high-knowledge readers."** *Discourse Processes* 43(2), 121–152.

Earlier work found low-knowledge readers comprehend more from **high**-cohesion text, while
high-knowledge readers learn more from **low**-cohesion text, because the gaps force inference.
The tempting design conclusion — *"expert audience, so don't over-explain, write denser"* — is
**wrong**.

O'Reilly & McNamara found the low-cohesion benefit was restricted to **less skilled**
high-knowledge readers. **Skilled** high-knowledge readers benefited from the high-cohesion
text.

An audience of engineers reading a technical blog is high-knowledge **and** skilled, so the
answer is high cohesion anyway. A skill that told an expert-audience author to write denser
prose would be citing the 1996 half of this literature and missing the 2007 correction.

Same shape, different literature: **Kalyuga (2007)**, *Educational Psychology Review*, on the
expertise reversal effect.

## Cohesion is measurable; readability formulas cannot see it

**Graesser, A. C., McNamara, D. S., Louwerse, M. M. & Cai, Z. (2004). "Coh-Metrix: Analysis of
text on cohesion and language."** *Behavior Research Methods, Instruments, & Computers* 36(2),
193–202.
**Graesser, A. C., McNamara, D. S. & Kulikowich, J. M. (2011).** *Educational Researcher* 40(5).

Coh-Metrix exists *because* the formulas cannot see cohesion. Its referential-cohesion measures
are built on content-word and stem overlap between text segments — which is exactly what
`cohesion_report.py` computes between adjacent paragraphs and across a rolling window.

**What this skill does not claim.** Coh-Metrix reports dozens of indices with published norms
across corpora. This script computes one family of them, on one document, with a crude stemmer
and no norms at all. It ranks; it does not threshold. Any cut-off would be invented, and an
invented cut-off is the same error as a grade band wearing better clothes.

## The second reader has a track record; the linters do not

Three recorded catches, all on this author's own drafts, all found by a fresh reader and missed
by everything mechanical:

- **2026-08-19,** recorded in the `prose-linting-verdict` memory. **Vale** produced 102 findings,
  34 of them `FirstPerson` against a `WRITING_CONTEXT.md` that permits first person. **Harper**
  produced 34 findings and **zero true positives** on a cleaned draft. A second reader found a
  contradiction all three linters missed.

- **2026-09-01, the CI-gates draft.** A sonnet subagent reading cold found a **contradiction
  four paragraphs wide**: the post said the German edition "sidesteps the whole thing" while
  the gate section described a German tripwire for that same problem. Confirmed against
  `verify_ats.py`. It also found the thesis restated five times, two of them near-verbatim
  seven lines apart.

- **2026-09-02, the same draft, on this skill's first run.** By then it had passed `check.sh`,
  a full `clear-and-human` register pass **and the 2026-09-01 reader above**. A fresh reader
  still found four more things:
  - A **contradiction**: line 46 dismisses "avoid hyphens" as unenforceable and "mostly wrong
    anyway", while lines 50–54 credit a deliberately unhyphenated phrase for the one keyword
    that survives extraction. The logic reconciles — you cannot *gate* on it, but you can
    *choose* it — and the text never says so, so the reader hits the collision.
  - A **numeric ambiguity in the footnote whose whole job is to make the table believable**:
    "four column widths … two generators … two extractors … four cells" invites the reader to
    multiply to sixteen and find the summary says four. Two different runs, one sentence.
  - **"the same four pages"** used with its antecedent forty lines later, colliding with the
    "four column widths" in the next clause.
  - **"the shared renderer"** and **"tripwire phrase"** used as established labels before either
    is introduced.

No formula and no linter can see a contradiction, because neither reads for meaning.

**And the load-bearing lesson from the third catch: the second reader missed everything the
third one found.** One fresh reader is a sample, not an audit. Findings do not converge on a
fixed list, so run the reader again after a revision rather than treating the previous pass as
a clearance — and do not report "the reader found nothing" as though the document were clear.

## Deliberately not used

- **AI-detector scores.** Liang et al., *Patterns* 4(7):100779, measured a **61.22%
  false-positive rate** against non-native English writers across seven detectors.
- **Burstiness.** No grounding found; GPTZero dropped it in autumn 2023.
- **Flesch Reading Ease, Flesch-Kincaid, Gunning Fog, SMOG.** See Redish above. If a number is
  genuinely required — a client contract, an accessibility standard that names one — install
  `textstat` and compute it. **Never ask a model to compute one.** All four need syllable
  counts, and a model asked for one produces a plausible figure it never calculated. That is
  the same failure `clear-and-human` already names: "a measurement of the text you are
  reviewing" is on its fabrication list.

## Provenance

The upstream skill this replaces —
`github.com/humanizerai/agent-skills/blob/main/skills/readability/SKILL.md` — computes all four
formulas, defines a complex word as three or more syllables, maps onto US grade bands, cites no
sources, and ships no script. The missing script is the fatal half: without one, every number
it reports was produced by a model reading text and asserting a figure.
