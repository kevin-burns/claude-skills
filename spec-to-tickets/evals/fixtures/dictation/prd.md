# Local voice dictation for Mac

Readiness: verified
Verifier: independent

## Problem

The user wants to write long emails by voice, with the dictated text typed wherever the cursor is. [turn:9e7d5408-08d0-46a9-83d2-fe0b013cccaf]

## Who it is for

The user first, and then people like them who write long emails and messages by voice. [turn:9bc67cff-8cc7-4a12-b221-80450c45a53f]

## Goal

A small Mac app that takes dictation and types the text wherever the cursor is, so the user can write long emails by voice. It runs locally on an Apple Silicon Mac, handles English only, and a delay of up to a second is acceptable. [turn:9e7d5408-08d0-46a9-83d2-fe0b013cccaf]

## Non-goals

- No meeting transcription. [turn:55b4132b-e2f5-4f00-ad6f-a5236da4610b]
- No speaker labels. [turn:55b4132b-e2f5-4f00-ad6f-a5236da4610b]

## Anti-goal

A clone of an existing app counts as a failure. [turn:cc9de5ef-13f9-4238-b749-dc7cfaf52655]

## Success check

The user uses it daily for a week. [turn:cc9de5ef-13f9-4238-b749-dc7cfaf52655]

## Risks

- Latency on older Macs might make it annoying. [turn:79b9184c-4ad8-4071-9f59-88a4728be105]

## Open questions

- Open question: should the speech model also stay outside the core library? The audio driver must (see the spec); the speech model was proposed but the user has not answered.
- Open question: what makes this not a clone of an existing app? The anti-goal is stated, but no differentiating feature has been named.
- Open question: which Mac chip is the user's, and is there an older Apple Silicon Mac it must work well on? The question was asked and not answered.

## Assumptions

- Assumption: it is a menu-bar app started and stopped by a hotkey.
- Assumption: spoken punctuation such as "comma" and "new paragraph" becomes real punctuation and line breaks.
- Assumption: typing at the cursor needs macOS Accessibility and Microphone permissions.
- Assumption: the speech engine is a local Whisper-type model.
