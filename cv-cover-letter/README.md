# cv-cover-letter

Draft a cover letter from a job posting and your own CV and evidence base — making only claims
that trace to something you actually said, and stopping when the evidence stops rather than
filling a word count.

Part of [claude-skills](../README.md).

## What it does

A cover letter is a volatile document. A mediocre one is ignored; a **wrong** one disqualifies
you before anything true about you is read. Bounded upside, unbounded downside — so this skill
is built to reduce the cost of producing a *true* letter, not to produce a persuasive one.

- **Tells you when not to bother.** It reads the posting for stated hard requirements — a
  language, a permit, a years-of-management threshold — and says plainly when one fails, before
  you spend an hour on an application that screens out.
- **Separates stated claims from derived ones.** "Reduced findings from 180 to 12" is in your
  CV. "Sixteen years of contracting" is arithmetic on a date range and you never said it. Both
  can appear; the derived ones are surfaced for you to confirm.
- **Refuses to diagnose the employer.** If the posting says their cloud spend is outpacing
  revenue, that is theirs and quotable. If it does not, guessing is the failure that cannot be
  recovered — you would be explaining someone's business to them, wrongly, in paragraph one.
- **Has no target length.** The letter ends when the sourced claims end. Three claims in three
  paragraphs is a finished letter.
- **Checks the letter against the CV you are actually sending.** Two documents agreeing on
  specifics is expensive to fake, which is what makes it worth anything now that fluent tailored
  prose is free.
- **Hands you the decisions it cannot make** — why this employer, relocation, notice period —
  marked in the draft rather than invented around.

Works on any posting: a URL, a pasted advert, an email. Not only LinkedIn.

## Why the rules are what they are

They come from measured outcomes rather than career-advice convention. The synthesis, with
citations and the grading of each source, is in [`references/evidence.md`](./references/evidence.md).

- **Composition beat tailoring.** Detail, clarity and structure predicted more interviews and a
  shorter search; tailoring predicted nothing (Wingate et al., 2025, *n* = 183, real outcomes).
- **Mirroring the posting has stopped signalling.** After an AI writing tool launched on a large
  labour platform, the correlation between textual alignment and callbacks fell **51%** (Cui et
  al., 2025) — replicated independently on different data (Galdin & Silbert, 2025).
- **A signal works only if it is costly to fake** (Spence, 1973). An adjective is free. A
  checkable fact is not.
- **Editing the draft correlated with hiring success**, so a finished letter is the wrong
  output.

The statistics you will see quoted everywhere — *"83% of recruiters read cover letters"* — range
from 83% to 26% on the same question and are all published by companies selling cover-letter
tools. This skill does not cite them and neither should you.

## Does it work on its own?

**Yes — and it is measurably better with the other two.**

On its own, with just a posting and a CV, every rule still works: it triages hard requirements,
separates stated claims from derived ones, refuses to invent, selects rather than pads, and
checks the letter against the CV. The letter it produces will be true.

What it cannot do alone is **reach for facts your CV does not contain** — and a CV is built to
leave things out.

Measured on one real application, the same role and the same person, with and without an
evidence base:

| | opening line |
|---|---|
| CV only | *"I'm applying for the Engineering Manager role in Europe."* |
| CV + evidence base | *"Between 2004 and 2008 I built and ran the infrastructure team at a mid-size ISP — five direct reports, three of whom I hired myself."* |

The second fact was **not on the CV**. It was in the evidence base, because a CV compresses
roles beyond roughly fifteen years and this one had dropped it. For an engineering-management
application whose CV showed only "mentored two junior engineers", that fact was the whole case —
and without `cv-evidence-base` there was nothing better to open with than the fact of applying.

The evidence base also carries something a CV never can: **your own conclusions about what you
cannot claim.** In another run it declined an entire application because the evidence base held a
recorded finding — "Kubernetes is operate-around, not own-the-platform" — against a posting whose
must-have was deep Kubernetes ownership. Nothing in the CV would have stopped that letter.

**So: no hard dependency, and no pretending.** Used alone it says when the letter came out thin
because the source was thin, and points upstream rather than padding. The family in order:

1. **[`cv-evidence-base`](../cv-evidence-base)** — recovers what is true, including what the CV drops
2. **[`cv-and-human`](../cv-and-human)** — tailors the CV itself
3. **`cv-cover-letter`** — this one, drawing on both

## How to use it well

- **Give it the posting, your CV, and your `evidence-base.md`** if you have one. It reads what
  you supply and does not go hunting for files.
- **Let it tell you not to apply.** That is the feature, not a failure to be talked out of.
- **Check the derived claims.** They are usually right; they are still things you did not say.
- **Expect it to be shorter than you think it should be.** The urge to fill a page is the
  convention it is deliberately ignoring.
- **Answer the open decisions rather than deleting them.** They are the parts only you know, and
  the evidence says the editing is where the value is.
- **Run [`cv-evidence-base`](../cv-evidence-base) first** if you have not. A thin evidence base
  makes a thin letter, and the fix is upstream of here.

## What it does NOT do

- **It does not invent a metric, a date, a duration or a scope.** Ever, under any pressure.
- **It does not diagnose the employer.** No problem is attributed to them that they did not
  state themselves.
- **It does not pad to a length**, and it has no target length.
- **It does not write "passionate about"** or substitute claimed enthusiasm for evidence.
- **It does not cite recruiter-survey statistics.**
- **It does not write or edit your CV** — that is [`cv-and-human`](../cv-and-human).
- **It does not decide whether you should apply.** It reports a failed hard requirement and
  leaves the choice with you.
- **It does not promise an outcome.** Nothing here predicts a callback, and any tool that tells
  you otherwise is selling something.

## Requirements

None to install. Three inputs, all supplied by you: the posting, the CV you are sending, and
optionally `evidence-base.md` from `cv-evidence-base`. Without the evidence base the CV alone is
the source of truth and the claims table will be thinner.

Uses [`clear-and-human`](../clear-and-human) for register if it is available, and web search, if
available, to read a posting from a URL — otherwise paste the text.

## Licence

MIT, like the rest of this repo. Structure adapted from
[Paramchoudhary/ResumeSkills](https://github.com/Paramchoudhary/ResumeSkills) (MIT); see the
Provenance note in `SKILL.md` for what was deliberately not carried over, and why.
