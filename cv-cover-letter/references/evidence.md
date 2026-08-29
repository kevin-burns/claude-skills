# The evidence behind this skill

What the evidence actually supports about cover letters, graded by what each source can carry. Compiled 2026-08-29 from direct reads, plus a NotebookLM notebook of 89 sources used for discovery and cross-checking.

## The evidence, graded

| tier | source | what it can support |
|---|---|---|
| **Peer-reviewed, real outcomes** | Wingate, Robie, Powell & Bourdage (2025), *International Journal of Selection and Assessment*, [10.1111/ijsa.70022](https://onlinelibrary.wiley.com/doi/10.1111/ijsa.70022) | n=183 co-op students, Canada 2024. Outcomes were interviews-per-application and days-to-job — real outcomes, not opinions |
| **Peer-reviewed meta-analysis** | Kristof-Brown, Zimmerman & Johnson (2005), *Personnel Psychology* 58(2), [10.1111/j.1744-6570.2005.00672.x](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1744-6570.2005.00672.x) | 172 studies, 836 effect sizes, on person–job and person–organisation fit |
| **Working paper, causal** | Cui, Dias & Ye (2025), *Signaling in the Age of AI: Evidence from Cover Letters*, [arXiv:2509.25054](https://arxiv.org/abs/2509.25054) | Difference-in-differences around an AI writing tool's launch on a large labour platform |
| **Working paper, causal** | Galdin & Silbert (2025), *Making Talk Cheap: Generative AI and Labor Market Signaling*, [arXiv:2511.08785](https://arxiv.org/abs/2511.08785) | Freelancer.com data, structural model. Independent of Cui et al. and agrees with it |
| **Theory** | Spence (1973), *Job Market Signaling*, *QJE* 87(3) | Why any of this works at all |
| **Commercial, weak** | Ladders (2018) eye-tracking | n=30, not peer-reviewed, and about **résumés** not cover letters |
| **Unusable** | vendor surveys (Zety, ResumeBuilder, Novoresume) | 83% vs 26% on the same question; all sold by companies selling cover-letter tools |

## What the credible sources converge on

**Spence (1973):** a signal carries information only if it is *costly to fake*.

**Cui et al. (2025):** after an AI cover-letter tool launched, the correlation between a letter's textual alignment with the posting and callbacks **fell 51%**. Employers shifted toward prior work history.

**Galdin & Silbert (2025):** independently, on different data. Customisation signals lost the ability to predict worker effort or contract success. In their simulated counterfactual where written signals carry nothing, **top-quintile-ability workers are hired 19% less and bottom-quintile 14% more** — the market becomes measurably less meritocratic.

**Wingate et al. (2025):** detail, clarity and structure predicted more interviews (β = 0.20, p = .016) and a shorter search (β = −0.19, p = .048), holding after controls for experience and achievement. **Tailoring predicted nothing** (p = .34 for interviews, p = .52 for days).

**Kristof-Brown et al. (2005):** what is being assessed is *fit*; directly-assessed fit correlates ~.61 with intent to hire.

**Synthesised: the letter's job is to make fit legible using claims that are expensive to fake.** A specific checkable fact costs nothing to write if true and is unavailable if false. An adjective and a paragraph of the employer's own language cost nothing either way, and therefore now carry nothing. "Passionate" is not merely weak writing — it is a signal with a demonstrated value of approximately zero.

Two documents agreeing on specifics is itself expensive to fake. A letter making two or three checkable claims that the CV then confirms is a **coherence signal**, and coherence is the part AI has not made cheap.

## Two traps found while compiling this

**The 250–400 word rule has no empirical basis.** It is prescribed by the popular `cover-letter-generator` skill and by most career sites, and the sources contain no study supporting it. Same for one-inch margins, 10.5–12pt type, avoiding the first person, and matching colour bars. All untested convention presented as rule. (One vendor analysis found **50% of hired candidates used "I"** on their documents, against the common advice to avoid it — weak evidence, but it points the opposite way to the folklore.)

**A "Murdoch RCT on cover letters" is a domain-confusion false positive.** NotebookLM surfaced it confidently as evidence. It is a randomised trial about **cover letters attached to a veterans' health survey**, measuring emotional affect and survey participation — nothing to do with job applications. Right words, wrong domain. This is why the sources above were verified individually rather than taken from the synthesis.

## The finding that should change how a tool behaves

From Cui et al.: **time spent editing the AI draft correlated positively with hiring success.**

A tool that emits a finished letter is optimising against the evidence. The right output is a short draft with the judgment calls left open and marked — which two facts to spend, and what is actually known about the employer — for the applicant to close.

## What this makes a cover letter

Short, factual, and specific; it states why this person is a credible candidate for this role and lets the CV corroborate. Not because brevity is elegant, but because:

- composition beat tailoring, so structure and concreteness are what paid;
- alignment with the posting has decayed 51%, so echoing their language is spent effort;
- employers moved to verifiable history, so checkable facts are the surviving signal;
- fit is what is assessed, so it should be stated rather than implied.

## How this file was built

Sources were found by web search and by a NotebookLM notebook of 89 imported sources, then
**each citation above was opened and verified individually.** That was not ceremony: the
synthesis confidently offered a "Murdoch RCT on cover letters" as strong evidence, and it is a
randomised trial about cover letters attached to a veterans' health survey — right words, wrong
domain. A citation that is not in the table above did not survive checking.

Figures quoted from Wingate et al. were read from the article page rather than the publisher
PDF, which was paywalled. The abstract's own qualitative claim — that better-composed materials
"secured substantially more interviews" and "took less time to secure a position" — is the part
that is quoted verbatim and is what the skill's rules rest on.

Compiled 2026-08-29.
