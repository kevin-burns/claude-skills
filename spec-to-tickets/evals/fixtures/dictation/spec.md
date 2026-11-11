# Local voice dictation for Mac — spec

The how. The PRD beside this file holds the why; do not repeat it here.

## Solution

The user speaks and the text appears at the cursor in whatever app has focus. Everything runs on the user's own Mac. [turn:9e7d5408-08d0-46a9-83d2-fe0b013cccaf]

## User stories

1. As someone who writes long emails and messages by voice, I want my speech typed at the cursor, so that I can write long emails by voice. [turn:9e7d5408-08d0-46a9-83d2-fe0b013cccaf]
2. Proposed: As the user, I want to start and stop dictation with one hotkey, so that I never leave the window I am typing in.
3. Proposed: As the user, I want spoken punctuation turned into punctuation and line breaks, so that a long email needs little hand editing.

## Implementation decisions

- The core library holds the dictation session state, text formatting and the commit decision. It has no audio or speech-model dependency, builds without a microphone, and is tested without one. [turn:d1c3345b-55db-454c-a5c8-b9333b18b291]
- The core owns the interfaces it needs (audio source, recognizer, text sink). Adapters implement them outside the core.
- Proposed: the adapters are microphone capture, the speech model, typing at the cursor, and the hotkey.
- English only; delay up to a second is acceptable. [turn:9e7d5408-08d0-46a9-83d2-fe0b013cccaf]
- Proposed: the speech model sits behind a port so a smaller, faster model can be used on slower Macs. This answers the latency risk but the user has not agreed to it. [turn:79b9184c-4ad8-4071-9f59-88a4728be105]
- Proposed: the language and toolkit are not chosen. The plan must choose them and mark them as a call, not the user's decision.

## Verification strategy and test seams

TDD on the core logic, plus a small recorded audio set for accuracy. [turn:7751e608-fb71-43ee-b762-64fff36e07ca]

- Core tests use a fake audio source and a fake recognizer, so they need no microphone and no model. [turn:d1c3345b-55db-454c-a5c8-b9333b18b291]
- Proposed: the recorded set is read from audio files through the real speech adapter, so it needs a model but no microphone. It should also record transcription time per clip, so latency on slower Macs is a measured number. The user asked for accuracy only; the timing is an addition for them to confirm. [turn:79b9184c-4ad8-4071-9f59-88a4728be105]
- No accuracy or latency threshold has been given, so none is set here.

## Boundaries and rules applied

The audio driver stays out of the core library. [turn:d1c3345b-55db-454c-a5c8-b9333b18b291]

Rules from clean-architecture.mini.md applied: dependencies point inward; the core owns its ports; adapters stay humble and make no decisions; the boundary is enforced by build structure, not naming; core tests use fakes. Rules knowingly broken: none.

## Out of scope

- Meeting transcription and speaker labels. [turn:55b4132b-e2f5-4f00-ad6f-a5236da4610b]
- Languages other than English. [turn:9e7d5408-08d0-46a9-83d2-fe0b013cccaf]
- Proposed: running anywhere other than the user's own Mac, such as a server or a phone.
