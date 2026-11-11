"""Opt-in PreToolUse guard: no prd.md or spec.md is written while the gate has not passed."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))

from guard import decide

GUARD = Path(__file__).resolve().parents[1] / "hooks" / "guard.py"


def event(path: Path, tool: str = "Write") -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"file_path": str(path)}}


def readiness(directory: Path, passed: bool) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "readiness.json").write_text(json.dumps({"pass": passed}), encoding="utf-8")


def test_blocks_spec_without_readiness(tmp_path):
    code, message = decide(event(tmp_path / "plan" / "spec.md"))
    assert code == 2 and "readiness gate has not passed" in message


def test_blocks_when_pass_false(tmp_path):
    readiness(tmp_path / "plan", False)
    assert decide(event(tmp_path / "plan" / "prd.md", "Edit"))[0] == 2


def test_allows_when_pass_true(tmp_path):
    readiness(tmp_path / "plan", True)
    assert decide(event(tmp_path / "plan" / "spec.md", "MultiEdit")) == (0, "")


def test_ignores_other_files_and_tools(tmp_path):
    assert decide(event(tmp_path / "notes.md"))[0] == 0
    assert decide({"tool_name": "Bash", "tool_input": {"command": "echo > spec.md"}})[0] == 0


def test_malformed_input_allowed():
    done = subprocess.run([sys.executable, str(GUARD)], input="not json", capture_output=True, text=True,
                          check=False)
    assert done.returncode == 0 and "spec-ready guard" in done.stderr
    assert decide({"tool_name": "Write"})[0] == 0
