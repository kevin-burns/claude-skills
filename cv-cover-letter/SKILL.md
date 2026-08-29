---
name: cv-cover-letter
description: >
  Draft a cover letter from a job posting and the applicant's own CV and evidence base, making
  only claims that trace to something they actually said, and stopping when the evidence stops
  rather than filling a word count. Use when the user asks for a cover letter, a covering letter,
  a letter of application, a motivation letter or an Anschreiben; when they want an existing
  draft checked for claims it cannot support; or when they ask whether a posting is worth
  applying to before writing one. Runs on any posting — a URL, a pasted advert, an email — not
  only LinkedIn. Do NOT use for the CV itself (cv-and-human) or for recovering what someone has
  done in the first place (cv-evidence-base).
---

# Cover letter, from evidence

A cover letter is a **volatile document**: a mediocre one is ignored, but a wrong one
disqualifies before anything true about the applicant is read. The upside is bounded and the
downside is not, so this skill biases toward fewer sourced claims over more impressive ones,
and toward a shorter letter over a padded one.

Its purpose is **to reduce the cost of producing a true letter**, not to produce a persuasive
one. `cv-evidence-base` makes a weak CV less weak; this makes an expensive document cheap
without letting it drift from the facts.

## What the evidence actually supports

This skill's rules come from measured outcomes, not from career-advice convention. The full
synthesis with citations is in `references/evidence.md`. The four that change behaviour:

- **Composition beat tailoring.** Detail, clarity and structure predicted more interviews
  (β = 0.20, *p* = .016) and a shorter search; **tailoring predicted nothing** (*p* = .34).
  Wingate, Robie, Powell & Bourdage (2025), *Int. J. Selection and Assessment*.
- **Mirroring the posting has stopped signalling.** After an AI writing tool launched on a large
  labour platform, the correlation between a letter's textual alignment and callbacks **fell
  51%**, and employers moved to prior work history. Cui, Dias & Ye (2025). Replicated
  independently on different data by Galdin & Silbert (2025).
- **A signal only carries information if it is costly to fake.** Spence (1973). An adjective is
  free; a checkable fact is not. That is the whole basis of the rules below.
- **Editing the draft correlated with success.** So the output is a draft with the judgment
  calls left open, never a finished letter.

**Do not cite recruiter surveys** — the circulating figures range from 83% to 26% on the same
question and every one is published by a company selling cover-letter tools.

## Step 1 — Is this worth writing?

Read the posting for **stated hard requirements**: a language, a licence, a work permit, a
named years-of-management threshold, an on-site requirement. Check each against what the
applicant has given you.

**If a stated requirement clearly fails, say so before writing anything.** An hour spent on an
application that screens out on a language requirement is the burden this skill exists to
remove. Say which requirement, say it is the user's call, and write the letter if they still
want it.

Do not treat a preference as a requirement — "German a plus, not required" is not a barrier.

## Step 2 — Take the posting apart

Work from what the posting **requires**, separated from what it advertises. Most of a job advert
is marketing; the requirements are usually a short list inside it.

Look for a section describing **what success looks like** in the role, or the first ninety days.
Where it exists it is the most useful part of the advert: the employer stating their own
criteria, so nothing has to be inferred about what they want.

**Never assert a problem the employer has not stated.** Diagnosing a business to someone who
works there, from a guess, is the failure that cannot be recovered. If the posting says cloud
spend is outpacing revenue, that is theirs and quotable. If it does not, you do not know.
A question is safe where a diagnosis is not: *"I would want to understand how you currently
handle X"* claims nothing.

## Step 3 — Every claim is STATED or DERIVED

| | |
|---|---|
| **Stated** | appears in the CV or evidence base in words: "reduced critical findings from 180 to 12" |
| **Derived** | true only after a calculation or an inference: "sixteen years of contracting", from dates in a CV |

**Derived claims are not forbidden. They are surfaced.** Put them in the claims table marked
`derived` so the applicant confirms them. Two baseline runs of this task both produced
"sixteen years" from a date range and stated it as fact — never said by the person whose letter
it is.

**A year-count derived from a CV is not merely unverified. It is biased downward.** A CV
truncates early history by design — roles beyond roughly fifteen years are routinely dropped or
compressed — so **the earliest date on the page is a presentation choice, not a career start.**
Measured on a real pair: the CV's earliest year was 2000; the evidence base held 1997–2010 and
named 1995. Arithmetic on that CV understates its owner by five years, silently, and reads as
confident.

So the rule is not only "confirm it". It is: **the CV cannot answer how long someone has worked.
Ask, or take it from the evidence base, or leave it out.** Dated facts already show span without
anyone having to total them.

Anything that is neither stated nor derivable does not go in the letter. Not softened, not
hedged — out.

## Step 4 — Choose two or three claims, then stop

Impact comes from **selection, not invention**. The evidence base holds twenty true things; the
posting decides which two or three to spend.

**There is no word count.** The 250–400 word rule prescribed by most cover-letter tools has no
empirical support — nor do one-inch margins, 10.5–12pt type, or avoiding the first person.
**The letter ends when the sourced claims end.** A letter carrying three claims in three
paragraphs is finished; adding a fourth paragraph to reach a length adds words that signal
nothing.

**Lead with the strongest sourced claim, not with the fact of applying.** The reader already
knows which role this is — it is in the subject line, and "I am writing to apply for" spends the
most expensive sentence in the letter on nothing. Wingate et al. found *detail* predicted
outcomes; a statement of applying carries none. Open on the checkable fact that best answers
what the posting asks for.

This is the one place where impact and evidence pull the same way. The opening does not need a
manufactured hook — it needs the best true thing, first.

Prefer the claim that is **checkable and specific** over the one that sounds impressive.
"Reduced critical findings from 180 to 12 over nine months" survives contact with an interview.
"Extensive security experience" does not, and costs nothing to write, which is precisely why it
carries no information.

## Step 5 — Register

**Invoke `clear-and-human` for the prose.** Do not reinvent its rules here.

Two failures specific to this document, both of which reproduced across baseline runs:

**The pitch register.** "The discipline I'd bring", "a track record of taking ownership when it
counts", "doing it in a way that earns their trust rather than just meeting a spec", "sits at
the intersection of". These are unsourceable by construction — that is *why* they are empty,
not merely why they read badly. Cut them and the letter gets shorter and stronger at once.

**Conventions differ by market.** A German *Anschreiben* is more formal and more factual than a
US cover letter, and the confident-pitch register that American advice teaches can read as
overclaiming elsewhere. Where the applicant's market is known, follow it; where it is not, the
restrained factual version is the safer default and the one the evidence supports anyway.

## Step 6 — Check coherence with the CV

Every claim in the letter must appear in the CV the applicant is sending. **Two documents
agreeing on specifics is expensive to fake, and it is the signal that survives** now that
fluent tailored prose is free.

A claim in the letter that is absent from the CV is a flag, not an error — it may mean the CV
is missing something worth adding, which is `cv-and-human`'s job. Report it; do not silently
drop it or silently rewrite the CV.

## Output

1. **A triage line** — either "no stated requirement fails" or which one does.
2. **The draft.** No contact-block boilerplate unless asked; the applicant has that.
3. **The claims table** — every claim, its source line, `stated` or `derived`, and whether the
   CV corroborates it. This is what makes the rules checkable rather than promised.
4. **Open decisions**, listed. Why this employer specifically, relocation, notice period,
   anything only the applicant knows. **Do not guess these and do not write around them** —
   leave them marked in the draft.
5. **What was refused**, and why. A requirement with no supporting evidence is named here.

## What this skill does NOT do

- **It does not invent a metric, a date, a duration or a scope.**
- **It does not diagnose the employer.** No problem is attributed to them that they have not
  stated.
- **It does not pad to a length**, and it has no target length.
- **It does not write "passionate about"**, or any claim of enthusiasm in place of evidence.
- **It does not cite recruiter-survey statistics.**
- **It does not write or edit the CV** — that is `cv-and-human`.
- **It does not decide whether to apply.** It reports a failed hard requirement; the choice is
  the applicant's.
- **It does not promise an outcome.** Nothing here predicts a callback.

## Requirements

Three inputs, supplied by the user — **this skill does not go looking for files**:

1. **The posting.** A URL, a pasted advert, or a file. Any source; not only LinkedIn.
2. **The CV** being sent.
3. **`evidence-base.md`** from `cv-evidence-base`, if it exists.

**Running without an evidence base is supported and produces a true letter.** Every rule still
applies; the CV is simply the only source. **Say so when it costs something.** A CV compresses
early roles by design, so if the posting asks for something the CV cannot evidence and the letter
comes out thin, name that — "the strongest claim available from the CV alone is X; if you have run
`cv-evidence-base`, there may be a better one it dropped" — rather than padding to cover the gap.
Do not present this as a blocker and do not refuse to write.

The CV family has no shared path convention and this skill does not invent one.

## Provenance

Structure — hook types, opening don'ts, and the underqualified / overqualified / career-change
scenarios — adapted from
[Paramchoudhary/ResumeSkills](https://github.com/Paramchoudhary/ResumeSkills) (MIT). Its
"include at least one specific metric" checklist item and its 250–400 word rule are
deliberately **not** carried over: the first is an instruction to produce a number without a
source, and the second has no empirical basis.
