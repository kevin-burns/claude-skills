"""The shapes every backend produces and every consumer reads.

This module is the contract. A backend's job is to return a `Result` whose
segments look identical whichever engine decoded the audio, so that the quality
guard, the correction pass and the document writers never branch on backend.

WHY A DICT AND NOT A DATACLASS for segments: the JSON sidecar is the audit trail
for the guard's decisions, and a plain dict round-trips to JSON with no
conversion layer to get out of step with itself.

TIMESTAMPS. Everything a backend returns is on the *trimmed* clock. Nothing is
written to disk until `tslib.audio.ClockMap` has mapped it back to the original
recording. See tslib/audio.py.

QUALITY METRICS. `compression_ratio`, `no_speech_prob` and `avg_logprob` are
Whisper decoder metrics. Whisper-family backends (mlx-whisper, faster-whisper,
Groq, OpenAI) all return them and the full guard applies. Parakeet is a CTC/TDT
model and returns none of them, so those keys are `None` there and only the
repetition rule survives. `None` means "this backend cannot tell you", never
"this segment is fine" -- the guard must not read a missing metric as a pass.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class Word(TypedDict, total=False):
    word: str
    start: float
    end: float
    probability: float | None


class Segment(TypedDict, total=False):
    """One decoded span. Keys after `text` are populated where the backend can."""

    id: int
    start: float
    end: float
    text: str
    words: list[Word]

    # Whisper decoder metrics. None on backends that do not produce them.
    avg_logprob: float | None
    compression_ratio: float | None
    no_speech_prob: float | None

    # Written by the quality guard, never by a backend.
    suppressed: bool
    suppressed_reason: str


class Result(TypedDict):
    """What a backend returns, before the guard or the clock map have run."""

    text: str
    segments: list[Segment]
    language: str | None
    backend: str
    model: str


GuardMode = Literal["drop", "mark", "off"]


def empty_result(backend: str, model: str) -> Result:
    return {"text": "", "segments": [], "language": None, "backend": backend, "model": model}


def segment_metrics(segment: Segment) -> dict[str, Any]:
    """The three metrics, as a plain dict, with missing ones explicit."""
    return {
        "avg_logprob": segment.get("avg_logprob"),
        "compression_ratio": segment.get("compression_ratio"),
        "no_speech_prob": segment.get("no_speech_prob"),
    }
