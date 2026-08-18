# writing-for-agents — vendored, read-only

Source: https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents
Author: Matt Pocock. Licence: MIT — full text and copyright notice in `LICENSE`,
redistributed with these files as the licence requires.
Pinned at commit: 9c9f36ccd3995266cd675468af71639c8dde1ec5
Vendored: 2026-08-18

## Why this is here and not in a skill directory

Deliberately **not installed as a skill**. Its upstream description reads
"Use when creating or editing skills, or modifying AGENTS.md or CLAUDE.md" — model-invoked,
so installing it puts a permanently-loaded pointer into context that fires on every skill
edit across all 22 skills here. The routing harness that gates skill descriptions sits at
54/54; a new competing pointer is a change that harness has to adjudicate, not a free add.

Consulted by hand. Nothing routes to it.

## What it is

1,806 words of all-reference — seven lever families (context pointers, the two loads,
information hierarchy, completion criteria, when to split, leading words, pruning).
No steps, no audit procedure, no exhaustiveness bar. Using it as a red team means
supplying the procedure ourselves.

## The reason it earns shelf space

Its central test — "does this line change behaviour versus the default? ... settle it by
running the document, not by debate" — is the question `evals/ablation/` already answers.
It supplies hypotheses; the harness adjudicates them. Neither half works alone.
