# readability

Finds where a reader falls off a draft, and never gives it a grade.

A readability formula tells you a document is "grade 12". It cannot tell you which paragraph
lost the reader, and Redish (2000) reports that whether the formulas are valid for technical
material read by adults is unknown at all. So this skill does two things a formula cannot:

- **`scripts/cohesion_report.py`** ranks paragraph junctions by content-word overlap, flags
  paragraphs opening on a back-reference over a weak junction, and lists terms used before they
  are explained. Every finding names a line. Stdlib only, sub-second, no thresholds.
- **A fresh-context second reader** — one subagent that has not seen the draft being written —
  looks for contradictions, repetition, and the sentence where it lost the thread. This is the
  half with a track record: it found a contradiction four paragraphs wide in a draft that Vale,
  Harper and a full register pass had all cleared.

```bash
UV="$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv 2>/dev/null | head -1)"
"$UV" run "$HOME/.claude/skills/readability/scripts/cohesion_report.py" draft.md
```

`--terms known-terms.txt` exempts vocabulary your audience already has, so real gaps stop
competing with jargon they know. `--json` for a gate. `--top N` for a longer shortlist.

## Where it sits

```
draft  →  clear-and-human   AI texture, voice, register
       →  readability       cohesion + a fresh reader     ← here
       →  publish
```

Run it **after** the rewrite, not before: cohesion measured on a draft that is about to be
restructured describes a document that will not exist.

## What it refuses to do

No Flesch, no Flesch-Kincaid, no Gunning Fog, no SMOG, no grade level, no target score, and no
"looks fine". Where it has nothing rankable it says `NOTHING TO CHECK` rather than reporting
clean, because a pass over an empty set is not evidence.

The reasoning, with citations — Redish (2000), O'Reilly & McNamara (2007), Graesser et al.
(2004) — is in [`references/evidence.md`](references/evidence.md). The short version: formulas
"say nothing about the causes of any problems people might have", and the tempting conclusion
that expert readers want denser prose is contradicted by the 2007 correction.

## Tests

```bash
uv run --with pytest -m pytest tests -q
```

They pin the properties that would make the report lie: line numbers surviving front matter,
structure (code, tables, quotes, lists) not scoring as prose, short paragraphs being reported
as unmeasurable rather than as breaks, and the report never attaching a number to a formula
name.
