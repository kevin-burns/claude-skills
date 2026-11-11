"""check and accept: the commands the skill runs, and how an override is recorded."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))

import check_tickets
from spec_ready_link import find_spec_ready, load_transcripts
from tickets_md import parse

SCRIPT = HERE / "scripts" / "check_tickets.py"
PRD = "## Goal\n\nDictation that types where the cursor is.\n"
TICKETS = """---
source: built here
prd: prd.md
spec: spec.md
timebox: 1 week
layers: [audio, core, ui]
---

## Increment 1 — walking skeleton

### T1 — Dictate one sentence
- moscow: Must
- size: L
- layers: [audio, core, ui]
- kind: slice
- traces: "Dictation that types where the cursor is"
- blocked by: []
- note: one pipeline end to end
- acceptance:
  - A spoken sentence appears at the cursor (proves: the goal)

### T2 — Hotkey
- moscow: Could
- size: S
- layers: [core, ui]
- kind: slice
- traces: Proposed: a way to start dictation
- blocked by: [T1]
- acceptance:
  - Pressing the hotkey starts dictation (proves: user story 2)
"""


def spec_dir(tmp_path: Path, tickets: str = TICKETS) -> Path:
    d = tmp_path / "repo" / "docs" / "specs" / "x"
    d.mkdir(parents=True)
    (d / "prd.md").write_text(PRD, encoding="utf-8")
    (d / "tickets.md").write_text(tickets, encoding="utf-8")
    return d


def run(*args, cwd=None, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False,
                          cwd=cwd, env=env)


def test_check_exit_codes(tmp_path):
    d = spec_dir(tmp_path)
    over = run("check", str(d / "tickets.md"))
    assert over.returncode == 1 and "mix" in over.stdout  # T1 is 4 of 5 points Must
    (d / "tickets.md").write_text(TICKETS.replace("size: L", "size: S"), encoding="utf-8")
    assert run("check", str(d / "tickets.md")).returncode == 0


def test_check_reads_prd_relative_to_tickets(tmp_path):
    d = spec_dir(tmp_path, TICKETS.replace("size: L", "size: S").replace("types where", "speaks where"))
    done = run("check", str(d / "tickets.md"), cwd=tmp_path)
    assert done.returncode == 1 and "not in the PRD" in done.stdout


def test_check_reports_format_problems(tmp_path):
    d = spec_dir(tmp_path, TICKETS.replace("- kind: slice\n- traces: \"Dict", "- kind: layer\n- traces: \"Dict"))
    done = run("check", str(d / "tickets.md"))
    assert done.returncode == 1 and "format" in done.stdout


def session(tmp_path: Path, turns: dict[str, str]) -> dict:
    repo = tmp_path / "repo"
    slug = re.sub(r"[^A-Za-z0-9-]", "-", str(repo.resolve()))
    path = tmp_path / ".claude" / "projects" / slug / "sess-1.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("".join(json.dumps({"type": "user", "uuid": k, "message": {"role": "user", "content": v}}) + "\n"
                            for k, v in turns.items()), encoding="utf-8")
    return {"HOME": str(tmp_path), "CLAUDE_CODE_SESSION_ID": "sess-1", "PATH": os.environ.get("PATH", "")}


def accept(d, *extra, env, cwd):
    return run("accept", "--tickets", str(d / "tickets.md"), "--rule", "mix", *extra, env=env, cwd=cwd)


def test_accept_verified_with_a_real_turn(tmp_path):
    d = spec_dir(tmp_path)
    env = session(tmp_path, {"u7": "Going over sixty percent Must is fine for week one."})
    done = accept(d, "--turn", "u7", "--quote", "fine for week one", env=env, cwd=tmp_path / "repo")
    assert done.returncode == 0, done.stderr
    tickets, problems = parse((d / "tickets.md").read_text())
    assert problems == [] and tickets.accepted[0]["mode"] == "verified" and tickets.accepted[0]["slice"] is None
    assert run("check", str(d / "tickets.md")).returncode == 0


def test_accept_refuses_a_quote_not_in_the_turn(tmp_path):
    d = spec_dir(tmp_path)
    env = session(tmp_path, {"u7": "Let's think about it."})
    done = accept(d, "--turn", "u7", "--quote", "fine for week one", env=env, cwd=tmp_path / "repo")
    assert done.returncode == 1 and "not in that turn" in done.stderr
    assert parse((d / "tickets.md").read_text())[0].accepted == ()


def test_accept_without_spec_ready_is_attested(tmp_path):
    d = spec_dir(tmp_path)
    code, message = check_tickets.accept_override(d / "tickets.md", "mix", None, "u7", "fine", transcripts=None,
                                                  env={}, home=tmp_path, cwd=tmp_path)
    assert code == 0 and "attested" in message
    assert parse((d / "tickets.md").read_text())[0].accepted[0]["mode"] == "attested"


def test_find_spec_ready_from_a_symlinked_install(tmp_path):
    collection = tmp_path / "skills"
    (collection / "spec-ready" / "scripts").mkdir(parents=True)
    (collection / "spec-ready" / "scripts" / "transcripts.py").write_text("", encoding="utf-8")
    (collection / "spec-to-tickets").symlink_to(HERE, target_is_directory=True)
    link = collection / "spec-to-tickets" / "scripts" / "spec_ready_link.py"
    assert find_spec_ready(link) == collection / "spec-ready" / "scripts"
    assert find_spec_ready(tmp_path / "nowhere" / "scripts" / "x.py") is None


def test_this_checkout_finds_spec_ready():
    assert find_spec_ready() is not None and load_transcripts() is not None
