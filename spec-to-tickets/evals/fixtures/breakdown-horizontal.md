---
source: an earlier planning session
prd: specs/dictation/prd.md
spec: specs/dictation/spec.md
timebox: 1 week
layers: [audio, core, ui]
---

## Increment 1 — foundations

### B1 — Audio capture layer
- moscow: Must
- size: L
- layers: [audio]
- kind: slice
- traces: "types the text wherever my cursor is"
- blocked by: []
- acceptance:
  - Microphone audio is captured to a buffer (proves: the goal)

### B2 — Core session and formatting layer
- moscow: Must
- size: L
- layers: [core]
- kind: slice
- traces: "types the text wherever my cursor is"
- blocked by: [B1]
- acceptance:
  - Recognised text is formatted (proves: the goal)

## Increment 2 — user interface

### B3 — Typing at the cursor and hotkey
- moscow: Must
- size: M
- layers: [ui]
- kind: slice
- traces: ""
- blocked by: [B2]
- acceptance:
  - Text appears at the cursor (proves: the goal)
