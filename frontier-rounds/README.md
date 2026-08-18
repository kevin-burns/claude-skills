# frontier-rounds

Interviews you in **breadth-first rounds** until a design is settled, instead of one question
per message.

The difference is the algorithm. `superpowers:brainstorming` asks one question at a time, which
is right for an idea with no shape yet. This maps the work as a **design tree** and asks the whole
**frontier** each round — every decision whose prerequisites are already settled — so questions
that were never dependent on each other stop being serialised. Your answers reshape the tree, push
the frontier outward, and the next round asks what just became askable.

It produces **settled decisions, not deliverables**. The pull to start building is the signal to
hand off.

## How to use it well

**Bring a design that already exists.** This is for pinning something down, not for finding it.
If there is nothing to interrogate yet, use `superpowers:brainstorming` and come back.

**Answer by number.** Questions arrive numbered with a recommended answer under each. Answering
"1 yes, 2 the second option, 3 your call" is a complete round — you never have to write prose.

**Disagree with the recommendation.** It is there so you can react to a position rather than
compose one from nothing. Rejecting it is a fast, high-signal answer.

**Say when a question is unanswerable.** "I don't know yet" is a real answer: it moves the
question back into the tree rather than forcing a guess that later rounds build on.

**Let it look things up.** If a question turns on what a file contains, what a command prints or
which version is installed, it goes and finds out rather than asking you. Those lookups run in the
background — only the questions downstream of a lookup wait, so the round keeps moving.

**Expect a verification question near the end.** Settling how the work will be checked — tests,
combinatorial coverage, an ablation, or a decision about what gets faked at a network boundary —
is much cheaper here than after a plan exists.

## What it does NOT do

- **It does not build anything.** No code, no files, no plan. It produces decisions, and stops
  when the frontier is empty and you confirm a shared understanding. If it starts drifting into
  implementation, that is a bug.
- **It does not decide for you.** Sub-agents are used only to fetch read-only environment facts —
  file contents, command output, installed versions. Never to decide, design, draft, review or
  answer on your behalf. The decisions are yours; putting them to you is the point.
- **It does not invent facts to fill a gap.** If a question needs a fact it cannot look up, it
  asks or says which fact would settle it. It does not assume one and continue.
- **It does not modify `superpowers`.** That is an independent plugin, and the cache carries more
  than one version — an edit would be wiped on upgrade and would fork someone else's work. This
  skill sits beside it and never touches it.
- **It does not replace brainstorming.** Different algorithm for a different stage. An idea with
  no shape yet is brainstorming's job.
- **It does not guarantee the tree is complete.** The frontier empties when nothing further is
  *askable*, which is not proof nothing was missed. It surfaces assumptions; it does not certify
  their absence.

## Requirements

**Nothing.** Prose all the way down — no scripts, no dependencies, no API keys.

Two optional integrations, both degrading cleanly if absent: it reads the `nano` files from the
`software-design-rules` skill when a question turns on a design decision, and it can dispatch a
sub-agent for environment lookups.

## Provenance

The design-tree / frontier / rounds algorithm, the recommended-answer-per-question format, and
the rule that finding facts is the agent's job rather than the user's come from Matt Pocock's
`grilling` skill ([mattpocock/skills](https://github.com/mattpocock/skills), MIT). Adapted here:
sub-agent dispatch is scoped to read-only environment facts, and the design-rules table and the
verification-strategy step are additions. Design rules content belongs to the
`software-design-rules` skill, which credits its own sources.
