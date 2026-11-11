# Worked example: a dictation app

The PRD (only the lines the slices trace to):

```text
## Goal

A small Mac app that takes dictation and types the text wherever my cursor is, so I can write long emails by voice.

## Success check

Success is that I use it every day for a week instead of typing emails.

## Boundaries touched

The audio driver must stay out of the core library; the core has to build and test without a microphone.
```

The breakdown after spec-to-tickets. Increment 1 is the walking skeleton: one Must through every
layer, a prefactor that makes it possible, and a Could to drop if the week runs short. Increment 2
goes over 60% Must, and the person accepted that in their own words, recorded in the front matter.

```markdown
---
source: built here
prd: prd.md
spec: spec.md
timebox: 1 week
layers: [audio, core, ui]
accepted:
  - {"rule": "mix", "slice": null, "turn": "c41f", "quote": "accuracy is the whole point of week two", "mode": "verified"}
---

## Increment 1 — walking skeleton

### T0 — Put the audio driver behind an interface
- moscow: Should
- size: S
- layers: [audio]
- kind: prefactor
- traces: "the core has to build and test without a microphone"
- blocked by: []
- acceptance:
  - The core's tests run with a fake audio source (proves: the boundary)

### T1 — Dictate one sentence into the focused app
- moscow: Must
- size: S
- layers: [audio, core, ui]
- kind: slice
- traces: "types the text wherever my cursor is"
- blocked by: [T0]
- parallel: no
- acceptance:
  - A spoken sentence appears at the cursor in a text editor (proves: the goal)

### T3 — Show when it is listening
- moscow: Could
- size: S
- layers: [core, ui]
- kind: slice
- traces: Proposed: a menu-bar indicator while dictation is on
- blocked by: [T1]
- acceptance:
  - The indicator is on exactly while audio is captured (proves: user story 2)

## Increment 2 — accurate enough to use daily

### T4 — Better recognition for long emails
- moscow: Must
- size: L
- layers: [audio, core]
- kind: slice
- traces: "Success is that I use it every day for a week instead of typing emails"
- blocked by: [T1]
- note: one model swap behind the existing interface, one pull request
- acceptance:
  - A recorded five-minute email transcribes with no more errors than the agreed clip set allows (proves: the success check)

### T5 — Punctuation by voice
- moscow: Could
- size: S
- layers: [core, ui]
- kind: slice
- traces: Proposed: saying "comma" and "full stop"
- blocked by: [T4]
- acceptance:
  - Saying "full stop" ends the sentence (proves: user story 4)
```

`check_tickets.py check` reports nothing: T0 is horizontal but labelled a prefactor, T1 is the walking
skeleton, both Musts quote the PRD, the Coulds are marked `Proposed:`, increment 2's 4-of-5 Must
share is accepted, and T4's size note says why an L is still one pull request.
