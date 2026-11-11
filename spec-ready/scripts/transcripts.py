"""Read the person's own turns from the harness's session transcript.

The transcript is written by the harness, not by the agent, which is why it is the gate's
evidence. Only records that carry what the person typed count: Claude Code also stores tool
results, compaction summaries and side-chain prompts as `type: "user"`, and those are excluded.

Both formats are vendor formats and can change; the tests pin the shapes this reader expects.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Harness = Literal["claude-code", "codex"]

_TYPOGRAPHY = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "–": "-", "—": "-", "−": "-", " ": " ",
})
_EXCLUDED_FLAGS = ("isCompactSummary", "isSidechain", "isVisibleInTranscriptOnly", "isMeta")
# Plain-string user records the harness writes itself. Task notifications are the dangerous one:
# they carry a subagent's report, i.e. model output, under the user's role.
_HARNESS_PREFIXES = (
    "<task-notification>", "<command-name>", "<command-message>", "<command-args>",
    "<local-command-stdout>", "<local-command-stderr>", "<local-command-caveat>",
    "[Request interrupted",
)


@dataclass(frozen=True)
class Turn:
    id: str
    text: str


def normalise(text: str) -> str:
    """NFC, straight quotes and hyphens, single spaces: what dictation and copying disagree on."""
    return " ".join(unicodedata.normalize("NFC", text).translate(_TYPOGRAPHY).split())


def turn_hash(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def _records(path: Path) -> Iterator[tuple[int, dict]]:
    with path.open(encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield number, record


def _claude_text(content: object) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list) and content and all(
        isinstance(b, dict) and b.get("type") == "text" for b in content
    ):
        return "\n".join(str(b.get("text", "")) for b in content)
    return None


def _claude_turns(path: Path) -> list[Turn]:
    turns = []
    for _, record in _records(path):
        if record.get("type") != "user" or any(record.get(flag) for flag in _EXCLUDED_FLAGS):
            continue
        message = record.get("message") or {}
        text = _claude_text(message.get("content"))
        uuid = record.get("uuid")
        if text is None or not text.strip() or text.lstrip().startswith(_HARNESS_PREFIXES):
            continue
        if isinstance(uuid, str):
            turns.append(Turn(uuid, text))
    return turns


def _codex_turns(path: Path) -> list[Turn]:
    turns = []
    for number, record in _records(path):
        payload = record.get("payload") or {}
        if record.get("type") == "event_msg" and payload.get("type") == "user_message":
            text = payload.get("message")
            if isinstance(text, str) and text.strip():
                turns.append(Turn(f"L{number}", text))
    return turns


def load_user_turns(path: Path, harness: Harness) -> list[Turn]:
    if harness == "claude-code":
        return _claude_turns(path)
    if harness == "codex":
        return _codex_turns(path)
    raise ValueError(f"unknown harness: {harness}")


def _codex_cwd(path: Path) -> str | None:
    for _, record in _records(path):
        if record.get("type") == "session_meta":
            cwd = (record.get("payload") or {}).get("cwd")
            return cwd if isinstance(cwd, str) else None
    return None


def find_transcript(env: Mapping[str, str], home: Path, cwd: Path) -> tuple[Harness, Path] | None:
    session = env.get("CLAUDE_CODE_SESSION_ID")
    if session:
        projects = home / ".claude" / "projects"
        exact = projects / str(cwd).replace("/", "-") / f"{session}.jsonl"
        if exact.is_file():
            return "claude-code", exact
        matches = sorted(projects.glob(f"*/{session}.jsonl"))
        if matches:
            return "claude-code", matches[0]
    sessions = home / ".codex" / "sessions"
    if sessions.is_dir():
        candidates = sorted(sessions.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        for candidate in candidates:
            if _codex_cwd(candidate) == str(cwd):
                return "codex", candidate
    return None
