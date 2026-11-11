"""Transcript readers: the gate's evidence is the person's own turns, so the readers decide what counts.

The trap these tests pin: Claude Code logs tool results, compaction summaries and side-chain
messages as `type: "user"` records. Counting any of them as the person's words would let the
agent's own text pass as evidence.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from transcripts import Turn, find_transcript, load_user_turns, normalise, turn_hash


def write_jsonl(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def claude_user(uuid: str, content, **extra) -> dict:
    return {"type": "user", "uuid": uuid, "message": {"role": "user", "content": content}, **extra}


def test_claude_user_turns_by_uuid(tmp_path):
    path = write_jsonl(tmp_path / "s.jsonl", [
        claude_user("u1", "We are building a transcription engine."),
        {"type": "assistant", "uuid": "a1",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}},
        claude_user("u2", [{"type": "text", "text": "Not a clone."}]),
    ])
    assert load_user_turns(path, "claude-code") == [
        Turn("u1", "We are building a transcription engine."),
        Turn("u2", "Not a clone."),
    ]


def test_claude_tool_results_and_summaries_are_not_user_turns(tmp_path):
    path = write_jsonl(tmp_path / "s.jsonl", [
        claude_user("t1", [{"type": "tool_result", "tool_use_id": "x", "content": "file contents"}]),
        claude_user("c1", "This session is being continued...", isCompactSummary=True),
        claude_user("s1", "subagent prompt", isSidechain=True),
        claude_user("v1", "caveat", isVisibleInTranscriptOnly=True),
        claude_user("u1", "The anti-goal is a clone."),
    ])
    assert [t.id for t in load_user_turns(path, "claude-code")] == ["u1"]


def test_codex_user_message_events(tmp_path):
    path = write_jsonl(tmp_path / "rollout.jsonl", [
        {"type": "session_meta", "payload": {"cwd": "/w"}},
        {"type": "response_item", "payload": {
            "type": "message", "role": "user",
            "content": [{"type": "input_text", "text": "<environment_context>x</environment_context>"}],
        }},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "Ship it by Friday."}},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "ok"}},
    ])
    assert load_user_turns(path, "codex") == [Turn("L3", "Ship it by Friday.")]


def test_find_transcript_claude_by_session_id(tmp_path):
    cwd = Path("/work/proj")
    path = write_jsonl(tmp_path / ".claude" / "projects" / "-work-proj" / "abc.jsonl", [])
    assert find_transcript({"CLAUDE_CODE_SESSION_ID": "abc"}, tmp_path, cwd) == ("claude-code", path)


def test_find_transcript_claude_falls_back_to_any_project_dir(tmp_path):
    path = write_jsonl(tmp_path / ".claude" / "projects" / "-elsewhere" / "abc.jsonl", [])
    assert find_transcript({"CLAUDE_CODE_SESSION_ID": "abc"}, tmp_path, Path("/x")) == ("claude-code", path)


def test_find_transcript_codex_latest_matching_cwd(tmp_path):
    base = tmp_path / ".codex" / "sessions" / "2026" / "11" / "11"
    write_jsonl(base / "rollout-a.jsonl", [{"type": "session_meta", "payload": {"cwd": "/w"}}])
    newer = write_jsonl(base / "rollout-b.jsonl", [{"type": "session_meta", "payload": {"cwd": "/w"}}])
    write_jsonl(base / "rollout-c.jsonl", [{"type": "session_meta", "payload": {"cwd": "/other"}}])
    import os
    os.utime(base / "rollout-a.jsonl", (1, 1))
    os.utime(base / "rollout-c.jsonl", (3_000_000_000, 3_000_000_000))
    assert find_transcript({}, tmp_path, Path("/w")) == ("codex", newer)


def test_find_transcript_none(tmp_path):
    assert find_transcript({}, tmp_path, tmp_path) is None


def test_turn_hash_ignores_typography():
    assert turn_hash("it’s  “done” – now") == turn_hash("it's \"done\" - now")
    assert normalise("  a\n\tb  ") == "a b"


def test_claude_harness_injected_strings_are_not_user_turns(tmp_path):
    # Found on a real transcript: task notifications carry SUBAGENT output, and command echoes
    # and interrupt markers are written by the harness, all as plain-string user records.
    path = write_jsonl(tmp_path / "s.jsonl", [
        claude_user("n1", "<task-notification>\n<task-id>x</task-id> agent says the plan is settled"),
        claude_user("c1", "<command-name>/compact</command-name>"),
        claude_user("o1", "<local-command-stdout>Compacted</local-command-stdout>"),
        claude_user("m1", "<command-message>compact</command-message>"),
        claude_user("i1", "[Request interrupted by user for tool use]"),
        claude_user("u1", "<b>bold</b> is how I'd write it"),
    ])
    assert [t.id for t in load_user_turns(path, "claude-code")] == ["u1"]


def test_claude_bash_mode_records_are_not_user_turns(tmp_path):
    # Review finding 8: `!cmd` in Claude Code stores input and output as user records; the output
    # can be the contents of a file the agent wrote.
    path = write_jsonl(tmp_path / "s.jsonl", [
        claude_user("b1", "<bash-input>cat summary.md</bash-input>"),
        claude_user("b2", "<bash-stdout>The anti-goal is a clone.</bash-stdout><bash-stderr></bash-stderr>"),
        claude_user("b3", "<bash-stderr>oops</bash-stderr>"),
        claude_user("u1", "real words"),
    ])
    assert [t.id for t in load_user_turns(path, "claude-code")] == ["u1"]


def test_find_transcript_slug_replaces_dots(tmp_path):
    cwd = Path("/work/.hidden/proj.v2")
    path = write_jsonl(tmp_path / ".claude" / "projects" / "-work--hidden-proj-v2" / "abc.jsonl", [])
    assert find_transcript({"CLAUDE_CODE_SESSION_ID": "abc"}, tmp_path, cwd) == ("claude-code", path)


def test_find_transcript_refuses_an_ambiguous_session_id(tmp_path):
    # Review finding 1: a planted copy under another project directory must not be picked silently.
    write_jsonl(tmp_path / ".claude" / "projects" / "-a" / "abc.jsonl", [])
    write_jsonl(tmp_path / ".claude" / "projects" / "-b" / "abc.jsonl", [])
    assert find_transcript({"CLAUDE_CODE_SESSION_ID": "abc"}, tmp_path, Path("/x")) is None
