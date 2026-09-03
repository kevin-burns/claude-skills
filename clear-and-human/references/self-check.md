# Self-check

**Answer every item by number, in order, with a verdict and one clause of evidence.** Not a
summary of how it went — item 7, then item 8, then item 9.

This exists because the prose self-audit in `SKILL.md` is skippable and was skipped. In a
graded set of ten outputs, **six narrated running `fidelity_check.py` and one pasted its
output**. A checklist you have to answer item by item is harder to narrate past than a
paragraph asking you to reflect, which is the whole reason it is numbered.

**It does not replace `fidelity_check.py`.** The script measures what moved — numbers, quotes,
URLs, code spans, claim words. This list is judgement about what the text now does. Substituting
one for the other is the failure both are here to prevent. Run the script, then answer these.

**Adapt, do not recite.** Some items will not apply — a runbook has no closer to check, a Slack
message has no analogy budget. Say "N/A, no closing line" and move on. An item marked pass that
you did not actually look at is worse than an item skipped honestly.

---

## A. Fidelity — did the meaning survive?

1. Does every number, date, name, quote, URL and code span in the output appear in the source
   or in `WRITING_CONTEXT.md`? Quote `fidelity_check.py`'s count; do not assert it.
2. Did you open every row of that report's **CLAIM WORDS** section and decide whether the claim
   survives without the dropped word? Name the rows you opened and what you concluded. A row
   you did not open is a row you did not check.
3. Is any specific *without a digit* invented — a claim about state, a file path, a filename,
   an authorial stance, or a measurement of the text itself? Both generate-mode failures in the
   graded set were numberless, which is how they got past every other check.
3a. **Generate mode only: paste the fact ledger.** Every factual claim with its source —
   `WRITING_CONTEXT.md`, the user's message, or the user asked. A row with no source must
   already have been cut or bracketed. `fidelity_check.py` cannot run here, so this is the only
   fabrication check generate mode has, and three of this skill's worst graded failures were
   generate mode.
4. If any environment-specific value is bracketed as a placeholder, is **every** one bracketed?
   Half-marking tells the reader the unmarked ones are real.
5. Was an argument added or dropped? A rewrite changes delivery, not substance.
5a. **Does every script result you pasted still describe the text you are delivering?** Both
   scripts print `measured: <name> sha256:<digest>`. Hash the delivered artefact and check it
   matches. If you edited anything after running a check, that check is stale and must be
   re-run — a stale paste is indistinguishable from a fabricated one to the reader, and this
   failure has happened.

## B. Voice — is it still this person?

6. Would the author recognise this as theirs — vocabulary, cadence, bluntness, humour,
   uncertainty, digressions?
7. Was any edit made for tidiness rather than for a named defect? Strong human sentences are
   left alone.
8. Is the cutting proportional to the actual slop, with no compression that strips character?
9. Are contractions, asides, profanity and strong opinions preserved where the author uses
   them? Check the author's own corpus before "correcting" any of them.
10. Were em dashes, curly quotes or sentence rhythm changed on a blanket rule rather than on
    `ai-patterns.md`'s author-relative one? That reference is the authority, not a habit.

## C. Patterns — the list, applied to the output you are about to hand over

11. **Binary contrast / negative parallelism** — including the softened forms and the ones that
    cross a sentence boundary.
12. **Colon reveal** — a noun phrase, a colon, a lowercase dramatic reveal.
13. **Fake-profound kicker** — a final metaphor, aphorism or mic-drop. If you found one, did you
    *delete* it and end on a concrete sentence already present, rather than rewriting it into a
    better metaphor?
14. **Summary-recap ending** — a closing paragraph restating the piece. Different failure from 13.
15. **Faux-insight setup** — "what most people miss", "here's what nobody tells you".
16. **Signposting and evidence-rating asides** — announcing what is coming, or rating what just
    arrived.
17. **Superficial `-ing` tails** and **significance inflation**.
18. **Weasel attribution** — "experts agree", "studies show" with no named source.
19. **Synonym cycling**, **stacked fragments**, **rule of three forced**.
20. **Analogy budget** — none under 800 words, at most one per 800–1,500, never stacked, and all
    five permission tests passed.
21. **Formatting** — emoji in headings, mid-sentence bold for emphasis, bullets where two
    sentences read better, headers over two-sentence sections.

## D. Substance — clean is not enough

22. **The portability test.** Could any sentence move unchanged to another person, company,
    country or product? If so it is filler: cut it, or replace it with a fact, example,
    mechanism, consequence or judgement specific to *this* subject.
23. Does the piece carry an opinion, a specific, and a reason to exist? Zero AI tells with
    nothing to say is still slop — say so explicitly rather than reporting clean.
24. Does it do the job it was for, for the audience it was for? If you never established who
    that is and where it publishes, ask now rather than guessing.

---

**Every defect this list surfaces takes an exit — FIXED, REFUSED or ESCALATED — and you name
which.** Writing a defect down is not addressing it. In the graded set, three of four failures
described the problem accurately and delivered it anyway; the most quotable said *"still an
unsupported hype claim… I'm not going to manufacture the evidence that would justify it"* and
then shipped the claim. **A named defect with no stated exit counts as a failed item**, and
"inherited from the source" is not an exit.

**If any item fails, fix the draft and answer the failed items again.** Then present the final
version. Never certify what you did not check: say what you checked and how, not that nothing
was wrong.

## Provenance

The numbered-checklist form, and items 12, 13 and 22, are adapted from
[`no-ai-slop`](https://github.com/petergyang/no-ai-slop) (MIT), whose `eval.md` is a numbered
pass/fail list the model must answer after editing. Its em-dash rule is a flat prohibition and
was **deliberately not carried over** — `ai-patterns.md` holds an author-relative rule measured
against a real corpus, and a graded eval already caught this skill giving itself two opposite
instructions on that once.
