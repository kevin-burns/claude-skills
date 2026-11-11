# Local voice dictation for Mac

Readiness: verified
Verifier: independent

## Problem

The user wants to write long emails by voice, with the dictated text typed wherever the cursor is. [turn:u1]

## Who it is for

The user first, and then people like them who write long emails and messages by voice. [turn:u2]

## Goal

A small Mac app that takes dictation and types the text wherever the cursor is, so the user can write long emails by voice. It runs locally on an Apple Silicon Mac, handles English only, and a delay of up to a second is acceptable. [turn:u1]

## Non-goals

- No meeting transcription. [turn:u3]
- No speaker labels. [turn:u3]

## Anti-goal

A clone of an existing app counts as a failure. [turn:u4]

## Success check

The user uses it daily for a week. [turn:u4]

## Risks

- Latency on older Macs might make it annoying. [turn:u5]

## Open questions

- Open question: should the speech model also stay outside the core library? The audio driver must (see the spec); the speech model was proposed but the user has not answered.
- Open question: what makes this not a clone of an existing app? The anti-goal is stated, but no differentiating feature has been named.
- Open question: which Mac chip is the user's, and is there an older Apple Silicon Mac it must work well on? The question was asked and not answered.

## Assumptions

- Assumption: it is a menu-bar app started and stopped by a hotkey.
- Assumption: spoken punctuation such as "comma" and "new paragraph" becomes real punctuation and line breaks.
- Assumption: typing at the cursor needs macOS Accessibility and Microphone permissions.
- Assumption: the speech engine is a local Whisper-type model.
