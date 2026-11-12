"""Final-review fixes (2026-11-11): every way found to pass the checks without substance, or to
override them without the person's words, pinned so it stays closed."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))

from check_tickets import check_mix, check_scope, check_trace
from tickets_md import Criterion, Increment, Slice, Tickets, parse

SCRIPT = HERE / "scripts" / "check_tickets.py"
PRD = """# Dictation

Readiness: verified

## Goal

Dictation that types where the cursor is, so I can write long emails by voice. [turn:u1]

## Non-goals

- No meeting transcription. [turn:u3]

## Success check

I use it every day for a week instead of typing. [turn:u5]

## Assumptions

- Assumption: it is a menu-bar app started and stopped by a hotkey.
"""
READY = {"mode": "verified", "items": [
    {"item": "goal", "status": "settled", "turn": "u1"},
    {"item": "non_goals", "status": "settled", "turn": "u3"},
    {"item": "success_check", "status": "settled", "turn": "u5"},
    {"item": "risks", "status": "settled", "turn": "u8"}],
    "person_turns": ["u1", "u3", "u5", "u8", "u9"]}
OK = (Criterion("types at the cursor", "the goal"),)


def sl(id_, moscow="Must", traces='"Dictation that types where the cursor is"', layers=("audio", "core", "ui"),
       size="S"):
    return Slice(id=id_, title=id_, moscow=moscow, size=size, layers=tuple(layers), kind="slice", traces=traces,
                 acceptance=OK, line=1)


def tickets(*slices, accepted=()):
    return Tickets({"layers": ["audio", "core", "ui"]}, (Increment(1, "one", tuple(slices)),), tuple(accepted))


# I1: a Must traces to the goal, the success check or the anti-goal, and says enough to mean something.

def test_trace_rejects_short_quotes():
    for quote in ('"the"', '"a"', '"types where"'):
        assert check_trace(tickets(sl("T1", traces=quote)), PRD, READY), quote


def test_trace_rejects_non_goals_and_assumptions():
    for quote in ('"No meeting transcription."', '"it is a menu-bar app started and stopped by a hotkey"'):
        assert check_trace(tickets(sl("T1", traces=quote)), PRD, READY), quote


def test_trace_accepts_goal_and_success_quotes():
    for quote in ('"Dictation that types where the cursor is"', '"I use it every day for a week"'):
        assert check_trace(tickets(sl("T1", traces=quote)), PRD, READY) == [], quote


def test_trace_turns_must_be_goal_success_or_anti_goal_items():
    assert check_trace(tickets(sl("T1", traces="[turn:u1]")), PRD, READY) == []
    assert check_trace(tickets(sl("T1", traces="[turn:u8]")), PRD, READY)  # the risks turn
    attested = {**READY, "mode": "attested"}
    assert check_trace(tickets(sl("T1", traces="[turn:u1]")), PRD, attested)


# I2: Shoulds and Coulds trace to something real too, or say Proposed.

def test_scope_rejects_invented_quotes_and_turns():
    invented = tickets(sl("T1"), sl("T2", moscow="Should", traces='"Translate everything into French"'))
    assert [f.slice for f in check_scope(invented, PRD, "", READY)] == ["T2"]
    ghost = tickets(sl("T1"), sl("T2", moscow="Could", traces="[turn:nonexistent]"))
    assert [f.slice for f in check_scope(ghost, PRD, "", READY)] == ["T2"]
    spec_story = tickets(sl("T1"), sl("T2", moscow="Could", traces='"start and stop dictation with one hotkey"'))
    assert check_scope(spec_story, PRD, "As the user, I want to start and stop dictation with one hotkey.", READY) == []
    assert check_scope(tickets(sl("T1"), sl("T2", moscow="Could", traces="[turn:u9]")), PRD, "", READY) == []


# I4: mix findings are per increment, and missing contingency is its own rule.

def test_mix_and_contingency_are_per_increment():
    two = Tickets({"layers": ["audio", "core", "ui"]}, (
        Increment(1, "a", (sl("T1", size="L"), sl("T2", moscow="Could"))),
        Increment(2, "b", (sl("T3"), sl("T4", moscow="Should")))))
    found = {(f.rule, f.slice) for f in check_mix(two)}
    assert found == {("mix", "increment-1"), ("contingency", "increment-2")}


# I3, I5: layers and ids are checked, not trusted.

FILE = """---
prd: prd.md
layers: [audio, core, ui]
---

## Increment 1 — skeleton

### T1 — One
- moscow: Must
- size: S
- layers: [audio, audio]
- kind: slice
- traces: "Dictation that types where the cursor is"
- acceptance:
  - x (proves: the goal)

### T1 — Again
- moscow: Could
- size: S
- layers: [frontend, backend]
- kind: slice
- traces: Proposed: something
- acceptance:
  - y (proves: user story 2)
"""


def test_duplicate_and_undeclared_layers_and_duplicate_ids():
    _, problems = parse(FILE)
    text = " ".join(problems)
    assert "duplicate layer" in text and "undeclared layer" in text and "duplicate slice id T1" in text


def test_front_matter_layers_need_brackets():
    _, problems = parse(FILE.replace("layers: [audio, core, ui]\n---", "layers: audio, core, ui\n---"))
    assert any("front matter layers" in p for p in problems)


# C1: overrides need the person's words, are shown, and attested ones never pass silently.

def write_spec(tmp_path, accepted_lines=(), body_slices=None):
    d = tmp_path / "repo" / "docs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "prd.md").write_text(PRD, encoding="utf-8")
    (d / "readiness.json").write_text(json.dumps(READY), encoding="utf-8")
    front = "---\nprd: prd.md\nlayers: [audio, core, ui]\nlayers_from: Proposed: test fixture\n"
    if accepted_lines:
        front += "accepted:\n" + "".join(f"  - {line}\n" for line in accepted_lines)
    body = body_slices or """
## Increment 1 — skeleton

### T1 — One
- moscow: Must
- size: S
- layers: [audio, core, ui]
- kind: slice
- traces: "Translate everything into French please"
- acceptance:
  - x (proves: the goal)

### T2 — Two
- moscow: Could
- size: S
- layers: [core, ui]
- kind: slice
- traces: Proposed: a polish item
- acceptance:
  - y (proves: user story 2)

### T3 — Three
- moscow: Could
- size: S
- layers: [core, ui]
- kind: slice
- traces: "I use it every day for a week instead of typing"
- acceptance:
  - z (proves: the success check)
"""
    (d / "tickets.md").write_text(front + "---\n" + body, encoding="utf-8")
    return d / "tickets.md"


def check(path, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), "check", str(path)], capture_output=True, text=True,
                          check=False, env=env)


def test_bare_accepted_entry_is_a_format_problem_not_an_override(tmp_path):
    path = write_spec(tmp_path, ['{"rule": "trace", "slice": "T1"}'])
    done = check(path)
    assert done.returncode == 1 and "format" in done.stdout and "trace" in done.stdout


def test_check_lists_applied_overrides_and_proposed_slices(tmp_path):
    path = write_spec(tmp_path, ['{"rule": "trace", "slice": "T1", "turn": "u9", "quote": "x", "mode": "verified"}'])
    done = check(path, env={**os.environ, "HOME": str(tmp_path)})
    assert "override" in done.stdout and "verified" in done.stdout
    assert "proposed" in done.stdout and "T2" in done.stdout


def test_attested_override_exits_2(tmp_path):
    path = write_spec(tmp_path, ['{"rule": "trace", "slice": "T1", "turn": "u9", "quote": "x", "mode": "attested"}'])
    done = check(path, env={**os.environ, "HOME": str(tmp_path)})
    assert done.returncode == 2 and "attested" in done.stdout


def test_verified_override_is_rechecked_against_the_transcript(tmp_path):
    repo = tmp_path / "repo"
    path = write_spec(tmp_path, ['{"rule": "trace", "slice": "T1", "turn": "u9", "quote": "French is fine", '
                                 '"mode": "verified"}'])
    slug = re.sub(r"[^A-Za-z0-9-]", "-", str(repo.resolve()))
    t = tmp_path / ".claude" / "projects" / slug / "s.jsonl"
    t.parent.mkdir(parents=True)
    t.write_text(json.dumps({"type": "user", "uuid": "u9", "message": {"role": "user", "content": "No."}}) + "\n")
    env = {**os.environ, "HOME": str(tmp_path), "CLAUDE_CODE_SESSION_ID": "s"}
    done = subprocess.run([sys.executable, str(SCRIPT), "check", str(path)], capture_output=True, text=True,
                          check=False, env=env, cwd=repo)
    assert done.returncode == 1 and "no longer" in done.stdout


def test_accept_refuses_an_override_that_matches_no_finding(tmp_path):
    path = write_spec(tmp_path)
    done = subprocess.run([sys.executable, str(SCRIPT), "accept", "--tickets", str(path), "--rule", "size",
                           "--slice", "T1", "--turn", "u9", "--quote", "x"], capture_output=True, text=True,
                          check=False, env={**os.environ, "HOME": str(tmp_path)})
    assert done.returncode == 1 and "no current finding" in done.stderr


# I6: no tracebacks on bad input.

def test_unclosed_front_matter_and_bad_readiness_do_not_crash(tmp_path):
    path = write_spec(tmp_path)
    (path.parent / "readiness.json").write_text("{not json", encoding="utf-8")
    done = check(path)
    assert done.returncode == 1 and "Traceback" not in done.stderr and "readiness.json" in done.stdout
    path.write_text("---\nprd: prd.md\n\n## Increment 1\n", encoding="utf-8")
    done = subprocess.run([sys.executable, str(SCRIPT), "accept", "--tickets", str(path), "--rule", "mix",
                           "--turn", "u9", "--quote", "x"], capture_output=True, text=True, check=False)
    assert done.returncode == 1 and "Traceback" not in done.stderr


# M1: a module named transcripts elsewhere on the path does not shadow spec-ready's.

def test_shadowing_transcripts_module_is_ignored(tmp_path):
    (tmp_path / "transcripts.py").write_text("raise RuntimeError('wrong module')\n", encoding="utf-8")
    path = write_spec(tmp_path)
    done = check(path, env={**os.environ, "PYTHONPATH": str(tmp_path), "HOME": str(tmp_path)})
    assert "Traceback" not in done.stderr


# M3: fixtures carry no ids from a real session and no fingerprint of a local path.

def test_fixtures_carry_no_real_session_ids():
    fixtures = HERE / "evals" / "fixtures" / "dictation"
    text = "".join(p.read_text(encoding="utf-8") for p in fixtures.iterdir())
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)
    assert json.loads((fixtures / "readiness.json").read_text())["transcript_id"] == "fixture"
