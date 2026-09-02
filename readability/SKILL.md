---
name: readability
description: Check whether a draft is actually readable by locating where a reader falls off — weak paragraph junctions, back-references with no antecedent nearby, and terms used before they are explained — then dispatch a fresh-context second reader to catch contradictions and repetition that no script can see. Use this whenever the user asks whether something is readable, clear, hard to follow, confusing, well-structured or "does this flow"; whenever they ask for a readability check, a readability score, a Flesch or grade-level reading, or a second opinion on a draft; and as the last review pass before publishing a blog post, README, ADR, runbook or long technical explanation. Also trigger on "read this end to end", "does this make sense", "fresh eyes on this", "where does this lose people", "is this too dense", "second reader", "cohesion", "flow check". Reports locations and never a grade level — if the user explicitly wants a Flesch or Gunning Fog number, use this skill and explain why it is not computed. For AI texture, voice and register use clear-and-human instead; for a CV use cv-and-human.
---

# Readability

Two things a draft can be wrong about, and only one of them is visible to a script.

**A script can find where the argument jumps.** Two paragraphs that share no vocabulary, a
paragraph opening on "This" with the referent stranded in the previous one, a term used forty
lines before it is explained. Those have locations, and `cohesion_report.py` names them.

**Only a reader can find a contradiction.** On 2026-09-01 a second reader found this author's
draft asserting that a German edition "sidesteps the whole thing" four paragraphs after
describing a German tripwire built for that same problem. Vale, Harper and every formula
missed it, because none of them read for meaning. That is why this skill is a script **and** a
reader, and why the reader is not optional.

**Run the reader again after a revision, rather than treating the last pass as a clearance.**
On 2026-09-02 a second reader on that same draft — by then through `check.sh`, a full register
pass and the earlier reader — found four more things, including a contradiction and a numeric
ambiguity in the one footnote whose job was to make the evidence believable. Findings do not
converge on a fixed list. One reader is a sample, not an audit.

**No grade level, ever.** Not because grade levels are unfashionable, but because Redish (2000)
reports that whether the formulas are valid for technical material read by adults is unknown,
and because the grade-level criterion means 50% of children at that grade answered 50% of the
questions. The full argument with citations is in `references/evidence.md`. If the user asks
for a Flesch score, give them this skill's output and one sentence on why the number is absent.

## Run it in this order

The script is cheap and narrows where the reader should look. Run it first.

### 1. Locate the gaps

```bash
UV="$(command -v uv || ls "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)"
cohesion() { "$UV" run "$HOME/.claude/skills/readability/scripts/cohesion_report.py" "$@"; }

cohesion draft.md
cohesion draft.md --terms ~/.config/readability/known-terms.txt   # audience vocabulary
cohesion draft.md --json                                          # for a gate
```

Stdlib only, so `python3 <path>` works if `uv` will not resolve.

**Read the output as a shortlist, not a verdict.** It ranks junctions by content-word overlap
and stops there — there is no threshold anywhere in it, because no published cut-off exists for
one author's technical prose and inventing one would be a grade band under another name.

Three things it prints, in descending order of how often they matter:

| finding | what to do about it |
|---|---|
| **Cold open over a weak junction** | The paragraph asks the reader to carry a referent across a gap the text does not bridge. Name the thing, or stitch the junction. This is the one to fix first. |
| **Weakest junctions** | Read the top few. Some are deliberate turns — a low-overlap junction opening on "But" is a change of direction, and the report says so. The ones with no connective and nothing shared are where the argument actually jumped. |
| **Terms used without a gloss** | Often correct for an expert audience. Worth a look when a term appears many times and was never introduced. Feed the ones your reader already knows into `--terms` so they stop crowding the list. |

It also counts the junctions it **could not** measure — a paragraph under ten content words
gives the overlap nothing to work with, and a 0.00 there means "too short", not "disconnected".
Those are separated out rather than ranked, because a metric that reports confident zeros for
short paragraphs earns false confidence fast.

### 2. Dispatch the second reader

**This is the part with a track record. Do not skip it to save a few minutes.**

Spawn **one** subagent with **no context from this session** — not a fork. The whole value is
that it has not seen the draft being written, has no investment in the argument, and cannot
pattern-match on what you meant. Pass it the file path and nothing else about your intentions.

Use `general-purpose` with an explicit `model` (this is a judge seat, so it runs at a capable
tier and high effort — `sonnet` is the recorded default and produced both catches). Give it
this brief:

```
Read <path> end to end as a first-time reader who knows the domain but has not seen
this draft or anything about how it was written. Report only what you can point at:

1. CONTRADICTIONS. Any two places that cannot both be true. Quote both and give line
   numbers. This is the highest-value finding and the reason you were asked.
2. REPEATED CLAIMS. The same point made more than once. Say which instance is the
   strongest and which are redundant, with line numbers.
3. WHERE YOU LOST THE THREAD. The first sentence you had to re-read, and why —
   an undefined term, a referent you could not resolve, a jump you could not follow.
4. TERMS USED BEFORE THEY WERE EXPLAINED. Line of first use, line where it is
   explained if it ever is.
5. THE ONE QUESTION YOU STILL HAVE after finishing.

Do NOT rewrite anything, do not suggest wording, do not comment on style or voice, and
do not compute any readability score. Do not be encouraging — say what is wrong. If a
section is fine, say nothing about it.
```

**Why those five and nothing else:** each is checkable against the text, so you can verify the
reader rather than trusting it. Style feedback from a fresh reader is noise — `clear-and-human`
owns voice and register, and asking for both gets you a diluted version of each.

### 3. Reconcile the two, and say which found what

The script and the reader disagree usefully. A junction the script ranked worst that the reader
sailed through was a false alarm — say so. A contradiction the reader found that the script
could not see is the point of running both.

**Report which findings came from which.** A finding with a line number and a source is
actionable; a merged list of impressions is not, and it hides whether the expensive step earned
its place.

## Who the reader is changes nothing here

The literature has a trap in it and it is worth knowing about before someone "optimises" this
skill for an expert audience.

Earlier work found high-knowledge readers learn **more** from **low**-cohesion text, because
gaps force inference. The tempting conclusion — expert audience, so write denser, stop
explaining — is wrong. O'Reilly & McNamara (2007) found that benefit was restricted to *less
skilled* high-knowledge readers. **Skilled** high-knowledge readers did better on the
high-cohesion text.

An audience of engineers is high-knowledge and skilled, so the answer is high cohesion anyway.
Do ask who the reader is; do not conclude that a technical audience wants a denser draft.

## At a post a day

The cadence this was built for is one post per day, sometimes one per two days, so the
constraint is the author's attention rather than compute.

- The script runs in well under a second. There is no reason not to run it on every draft.
- The second reader is one subagent, a couple of minutes, and it is where the real findings
  come from. **It is the step to protect when time is short**, not the one to drop.
- What does not scale is a report someone has to interpret. That is why the output names lines
  and refuses to produce a number that would need explaining.

Where this sits in the existing pipeline for a blog post:

```
draft  →  check.sh          markdown structure, spelling          mechanical
       →  clear-and-human   AI texture, voice, register           measured
       →  readability       cohesion + a fresh reader             THIS SKILL
       →  ghost-publish     upload, then verify what arrived      mechanical
```

Run this one **after** `clear-and-human`, not before. A rewrite moves paragraphs, and cohesion
findings computed against a draft that is about to be rewritten are findings about a document
that will not exist.

## What this skill will not do

- **It will not emit a grade level, a Flesch score, or any target number.** If one is genuinely
  required by a contract or a standard, install `textstat` and compute it — and never ask a
  model for one, because all four formulas need syllable counts and a model will produce a
  plausible figure it never calculated.
- **It will not rewrite the draft.** It locates; you decide. `clear-and-human` does the prose.
- **It will not tell you a draft is fine.** If the script finds nothing rankable it says
  `NOTHING TO CHECK` rather than reporting clean, because a pass over an empty set is not
  evidence.
- **It will not delegate the reading to a fork of the current session.** A fork carries the
  context that caused the blind spot.
