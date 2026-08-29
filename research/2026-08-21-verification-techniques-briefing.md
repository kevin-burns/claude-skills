# Verification techniques used in one working session

A field report, not a methodology paper. Every technique below was used on 21 August 2026
across two projects: a security-control rollback, and an editorial pipeline for a technical
digest. Each is stated with what it cost and what it caught, because several of them failed.

The through-line: **the expensive errors were all cases where something looked verified and
was not.**

---

## 1. Behavioural probe over documentation

Repeatedly, the documented behaviour and the actual behaviour differed.

- A sandbox setting (`excludedCommands`) was applied the previous evening on the strength of
  its name. Tested the next morning by invoking the command two ways, it had never worked.
- A permission rule (`Read(**/.dev.vars)`) had been in place for a day. Tested with a decoy
  file, it protected one directory and not the four others in daily use — the glob was
  project-relative and nobody had checked.
- A tool's own schema contradicted the plan: read-deny rules propagate into the sandbox, so
  the "obvious" fix would have broken the CLI it was meant to protect.

**Cost:** one to three shell commands each. **Caught:** three controls that were believed
active and were not.

## 2. Test a deny rule where failure is not the harm

The natural test of "can the agent read the credential file" is to try reading it. But if the
rule does not work, the test *is* the leak — the secret lands in the transcript.

Instead: create a decoy at a path the rule covers **that does not yet exist**. If the rule
works, the write is refused and nothing is created. If it does not, a dummy file appears and
is deleted. Same evidence, no exposure.

Generalisation: **when a test's failure mode is the harm it tests for, construct an
isomorphic test on worthless data.**

## 3. Bisect by tool family, not by error message

Enabling an OS-level sandbox produced, in one hour: a TLS certificate failure, a read-only
database, a bind refusal, a connection refusal, and a Python traceback about a log file. None
mentioned permissions. Each had an obvious wrong explanation close to hand — an expired login,
a corrupt cache, a port in use, a firewall.

What identified the real cause was noticing that `curl` succeeded where a Go binary failed —
a *tool-family* split, invisible in the error text.

**When enforcement happens below the application, failures surface as whatever the syscall
returned.** Suspect the layer you changed, not the message you received.

## 4. Ablation with a replicate noise floor

The central technique, and the one that produced the session's most useful result.

Question: does reading a pull-request body change the editorial verdict, or only the
confidence?

Naive design: rate 159 items from titles, rate them again with bodies, count the movement.
This is uninterpretable — a language model rating the same items twice will not agree with
itself, so *some* movement is guaranteed.

Design used — three arms, one variable:

| arm | input | purpose |
|---|---|---|
| A | title only | the current protocol |
| A′ | title only, second run | **the noise floor** |
| B | title + full body | the treatment |

Movement A→B means something only if it exceeds A→A′. Same model and effort in all three
arms, so movement is attributable to the evidence rather than the rater.

Result: noise 15.7%, effect 25.2%, ratio 1.60×. **The ratio was the weak half of the finding.**

## 5. Look at the shape of the disagreement, not only its size

The ratio was marginal. The decisive statistic was categorical:

- A vs A′: 25 disagreements, **all 25 involving an "unsure" verdict, zero reversals** between
  two definite verdicts.
- A vs B: 40 disagreements, **ten of them outright reversals** — and in eight of those ten,
  both title-only runs had agreed with each other.

Two runs on identical input never once reversed a confident verdict. Adding evidence reversed
ten. That separates two hypotheses a movement count conflates:

- **the rubric is ambiguous** → disagreement would appear as confident reversals between runs
- **the evidence is insufficient** → disagreement appears as hesitancy

It was the second. The instrument was fine; the input was too thin.

## 6. Make "I cannot tell" a first-class verdict

Raters answered three ways, not two, and the brief said the third answer was being measured
and should not be avoided. Without it, uncertainty is silently forced into a guess and the
signal in §5 is destroyed.

Uncertainty collapsed from 26 items to 8 when bodies were supplied — 24 of 26 resolved, 19 to
reject and 5 to keep. **Most hesitancy was over-caution.** That is only knowable because
hesitancy was recordable.

## 7. Do not let a null be blamed on your own shortcut

The treatment arm was 118,000 tokens of untruncated text. Truncating to a comfortable size
would have been cheaper and would have made a null result unpublishable — indistinguishable
from "you cut the part that mattered".

Two items in the corpus had no body at all. They were kept in as internal controls and
behaved as they must: one stable across all three arms, one matching the title-only replicate.

## 8. Directional error accounting

Ten reversals is not the finding; **which way they went** is.

- 6 rejected→keep — the pipeline silently drops publishable items. A false negative never
  reaches review, so nobody sees what was lost.
- 4 keep→rejected — the pipeline promotes items that do not qualify. A human meets these
  downstream.

Same count, different cost. The invisible direction was the more common one.

## 9. Independence as a hard constraint on evaluation

A prior agreement measurement could not be repeated because the second rater had, in the
interval, **written the document being tested**. Authorship disqualifies a judge.

The same rule then disqualified *this session*: having drafted two sections of the rubric that
morning, the orchestrating agent could not serve as a rater. Fresh raters were dispatched with
no access to the session's context and explicit instructions not to search for prior verdicts.

**A judge who has seen the answer key is not a judge.** This applies to the agent doing the
orchestrating, not only to the humans.

## 10. Declared budgets beat inferred ones

An editorial system had a slot budget for one section, derived from what had historically been
published — a number explaining the outcome that produced it. Circular and unfalsifiable: no
observation could contradict it.

Replaced with declared numbers for every section. Two past issues immediately violated the
declared budget. **Those were recorded as misses rather than used to move the number**, which
is the entire value: a declared budget can be wrong, and an inferred one cannot.

## 11. Elicit the shape before eliciting the values

A ranking function was assumed missing and a ranking function was designed for. Offered forced
pairs — one slot, which item goes in — the expert **refused three of four**: "publish both".

That refusal was the finding. He did not hold a total order; he held an absolute threshold.
The mechanism needed was a bar, with ordering only as a tie-break inside an over-subscribed
section. Months of ranking-function design would have been wasted.

**Ask the expert to choose. What they refuse to choose tells you the shape of the function.**

## 12. Exact-match edits that abort on miss

Seven changes to two live documents were applied by a script that asserted each target string
matched exactly once and exited before writing if any did not. No fuzzy matching, no partial
application. A wrong assumption fails loudly and changes nothing.

## 13. Read the record back after writing it

An issue tracker silently discarded two notes whose bodies began with a delimiter it parsed as
flags, and reported success both times. Every subsequent write was followed by reading it back
and grepping for a distinctive phrase.

**A write that reports success has not been verified. Exit zero is not evidence.**

## 14. Preserve the rejected fork

Compaction and handover preserve conclusions and lose alternatives. By the next session the
conclusion looks obvious and the discarded alternative gets re-litigated from scratch.

Every non-trivial decision recorded what was *not* chosen and why, in three lines, pointing at
a tracker item for detail.

---

## What failed

**A hand-written guard that could not parse its own input.** A pre-execution hook blocking
credential-printing shell commands produced four false positives in one morning: a JSON field
selector read as a filename, a write redirect read as a print, a path-listing command read as
a file read, and a loop keyword read as a verb. It matched on the first token because it could
not parse shell.

The documented workaround — put the command in a script and run the script — **makes the guard
invisible**, because it never sees the script's contents. It was removed.

**Lesson: a guard that cannot parse the language it polices is a speed bump on careless
one-liners, and it will be switched off.** The escape hatch matters as much as the rule: the
replacement tool evaluated offers an explicit bypass prefix, which is what lets a guard survive
contact with real work.

**A control at the wrong layer.** A proxy was built to redact secrets from outbound model
traffic. It worked. It was retired unused, because the transcript is written to local disk
*before* anything reaches the network — so by construction it could never protect the artefact
that actually held the leaked material. **Verify that a control can reach the thing it is
protecting before building it.**

---

## Research questions

1. Is the replicate-arm design (§4) a named pattern in the LLM-evaluation literature, and what
   is the accepted way to report effect-over-noise for a categorical judgement task?
2. §5 distinguishes instrument ambiguity from input insufficiency by the *shape* of
   disagreement. Does psychometrics or inter-rater-reliability literature formalise this? Is
   there an established statistic beyond comparing reversal counts?
3. What is the state of the art on three-way rating with an explicit abstention class — how is
   abstention handled in agreement coefficients, and does Cohen's kappa mistreat it?
4. n=159, one run per arm. What is the accepted power analysis for this design, and how many
   replicate arms would make a 1.6× ratio decisive rather than suggestive?
5. §9 claims authorship disqualifies a judge. Is there evidence on self-preference or
   authorship bias when an LLM evaluates against criteria it helped write?
6. §11 — is "elicit the shape by observing refusals" a documented preference-elicitation
   technique? What is the literature on threshold versus total-order preference structures?
7. §10 — is there prior art on falsifiability as a design criterion for editorial or selection
   rubrics, as opposed to accuracy?
8. On the failure: what is the evidence base for static guards over shell command strings, and
   is the consensus that parsing is required, or that the layer is simply wrong?
9. Where should credential controls sit for an autonomous coding agent — at tool execution, at
   the network boundary, or at the secret's origin — and what does the literature say about
   which layer reaches the local transcript?
10. Which of the fourteen techniques above are already standard practice under names I have not
    used, and which are genuinely unusual?
