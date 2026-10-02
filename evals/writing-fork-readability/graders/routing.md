---
type: llm
weight: 1
---

# Grader: did `readability` handle this?

This is a **routing** check. Grade which skill's behaviour the response shows, not how good it is.

## Pass

The response shows `readability`'s characteristic work: it LOCATES where the reader falls off
(a back-reference with no clear antecedent such as "This", "That", "it"; a term used before it is
explained; a junction where the argument jumps) and points at those spots, without rewriting the
passage and without giving a grade-level or Flesch score.

## Fail

- It rewrites the passage, or reviews it for AI texture and voice (that is `clear-and-human`).
- It gives a readability score or grade level as the answer.
- It is generic: competent advice that names none of the specific places the text loses the reader.
