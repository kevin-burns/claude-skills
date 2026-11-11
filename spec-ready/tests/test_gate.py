"""The gate: settled means a real user turn, a verifier's yes with a matching span, and no edits since.

Verifiers are faked here; the CLI tests run gate.py as a subprocess against fixture transcripts
with an answers file, so nothing calls a model.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from gate import questions, run_gate
from items import DEFAULT_ITEMS
from transcripts import Turn
from verifiers import Verdict

GATE = Path(__file__).resolve().parents[1] / "scripts" / "gate.py"
TEXT = {
    "goal": "Goal: dictation on the Mac that types where the cursor is.",
    "audience": "It is for people who write long emails by voice.",
    "non_goals": "We are not doing meeting transcription.",
    "anti_goal": "It fails if it becomes a clone of an existing app.",
    "success_check": "Success is me using it daily for a week.",
    "verification": "Verify with TDD on the core and an eval set for accuracy.",
    "boundaries": "Boundaries: the audio driver stays out of the core crate.",
    "risks": "Risk: latency on older Macs.",
}


class Yes:
    name = "fake"

    def verify(self, item, turn_text):
        return Verdict("yes", 0.9, turn_text.split(":")[-1].strip()[:12] or turn_text[:12], self.name)


class Answer:
    def __init__(self, answer):
        self.answer, self.name = answer, f"fake-{answer}"

    def verify(self, item, turn_text):
        return Verdict(self.answer, 0.5, turn_text[:5] if self.answer == "yes" else "", self.name)


def turns(keys=TEXT):
    return {f"u-{k}": Turn(f"u-{k}", TEXT[k]) for k in keys}


def proposals(keys=TEXT, **status):
    return [{"item": k, "turn": f"u-{k}", "status": status.get(k, "settled"), "statement": TEXT[k]} for k in keys]


def by_item(doc):
    return {row["item"]: row for row in doc["items"]}


def test_all_settled_passes():
    doc = run_gate(proposals(), DEFAULT_ITEMS, turns(), [Yes()], None)
    assert doc["pass"] is True and doc["mode"] == "verified"
    assert all(r["status"] == "settled" for r in doc["items"])
    assert by_item(doc)["goal"]["turn_hash"]


def test_missing_anti_goal_is_open_and_asked_first_when_least_certain():
    keys = [k for k in TEXT if k != "anti_goal"]
    doc = run_gate(proposals(keys), DEFAULT_ITEMS, turns(keys), [Yes()], None)
    assert doc["pass"] is False and by_item(doc)["anti_goal"]["status"] == "open"
    asked = questions(doc, DEFAULT_ITEMS)
    assert asked[0]["item"] == "anti_goal" and asked[0]["n"] == 1
    assert asked[0]["question"].startswith("What would make this a failure")


def test_turn_id_not_in_transcript_is_open():
    rows = proposals()
    rows[0]["turn"] = "u-invented"
    doc = run_gate(rows, DEFAULT_ITEMS, turns(), [Yes()], None)
    assert by_item(doc)["goal"]["status"] == "open" and "not found" in by_item(doc)["goal"]["reason"]


def test_assistant_turn_cited_is_open():
    rows = proposals()
    rows[1]["turn"] = "assistant-uuid"  # readers only return user turns, so an assistant id is absent
    assert by_item(run_gate(rows, DEFAULT_ITEMS, turns(), [Yes()], None))["audience"]["status"] == "open"


def test_guessed_allowed_only_for_risks():
    doc = run_gate(proposals(risks="guessed", goal="guessed"), DEFAULT_ITEMS, turns(), [Yes()], None)
    assert by_item(doc)["risks"]["status"] == "guessed"
    assert by_item(doc)["goal"]["status"] == "open"


def test_changed_turn_hash_fails_on_rerun():
    first = run_gate(proposals(), DEFAULT_ITEMS, turns(), [Yes()], None)
    edited = turns()
    edited["u-goal"] = Turn("u-goal", TEXT["goal"] + " Also an iPhone app.")
    second = run_gate(proposals(), DEFAULT_ITEMS, edited, [Yes()], first)
    assert by_item(second)["goal"]["status"] == "open" and "changed" in by_item(second)["goal"]["reason"]


def test_no_transcript_is_attested():
    doc = run_gate(proposals(), DEFAULT_ITEMS, None, [Yes()], None)
    assert doc["mode"] == "attested"


def test_verifiers_disagree_becomes_question():
    doc = run_gate(proposals(), DEFAULT_ITEMS, turns(), [Answer("yes"), Answer("no")], None)
    assert doc["pass"] is False
    assert by_item(doc)["goal"]["verdict"]["reason"] == "verifiers disagree"


def test_questions_order_unproposed_then_unsure_then_no():
    keys = [k for k in TEXT if k not in ("non_goals",)]
    rows = proposals(keys)
    doc = run_gate(rows, DEFAULT_ITEMS, turns(keys), [Answer("no")], None)
    doc["items"][0]["verdict"]["answer"] = "unsure"  # goal
    order = [q["item"] for q in questions(doc, DEFAULT_ITEMS)]
    assert order[:2] == ["non_goals", "goal"]
    assert "risks" in order


def write(path: Path, data) -> Path:
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


def transcript(tmp_path: Path) -> Path:
    lines = [{"type": "user", "uuid": f"u-{k}", "message": {"role": "user", "content": v}} for k, v in TEXT.items()]
    return write(tmp_path / "t.jsonl", "".join(json.dumps(x) + "\n" for x in lines))


def run(*args, env=None):
    return subprocess.run([sys.executable, str(GATE), *args], capture_output=True, text=True, check=False,
                          env=env)


def answers_for_all():
    return {k: {"answer": "yes", "p": 0.8, "span": TEXT[k][:15]} for k in TEXT}


def test_cli_exit_codes_and_readiness_file(tmp_path):
    t, out = transcript(tmp_path), tmp_path / "out"
    p = write(tmp_path / "p.json", proposals())
    a = write(tmp_path / "a.json", answers_for_all())
    env = {"PATH": "/nonexistent"}  # no claude CLI, so the answers file is allowed
    done = run("check", "--proposals", str(p), "--out", str(out), "--transcript", str(t), "--harness",
               "claude-code", "--answers", str(a), "--answers-from", "subagent", env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    doc = json.loads((out / "readiness.json").read_text())
    assert doc["pass"] and doc["verifiers"] == ["subagent"]
    assert json.loads(done.stdout)["pass"] is True


def test_cli_refuses_answers_file_when_an_independent_verifier_exists(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write(fake_bin / "claude", "#!/bin/sh\nexit 1\n").chmod(0o755)
    t, p = transcript(tmp_path), write(tmp_path / "p.json", proposals())
    a = write(tmp_path / "a.json", answers_for_all())
    done = run("check", "--proposals", str(p), "--out", str(tmp_path / "o"), "--transcript", str(t),
               "--harness", "claude-code", "--answers", str(a), "--answers-from", "session-model",
               env={"PATH": str(fake_bin)})
    assert done.returncode == 1 and "independent verifier" in done.stderr


def test_cli_no_transcript_exit_2(tmp_path):
    p = write(tmp_path / "p.json", proposals())
    a = write(tmp_path / "a.json", answers_for_all())
    done = run("check", "--proposals", str(p), "--out", str(tmp_path / "o"), "--answers", str(a),
               "--answers-from", "session-model", env={"PATH": "/nonexistent", "HOME": str(tmp_path)})
    assert done.returncode == 2
    assert json.loads((tmp_path / "o" / "readiness.json").read_text())["mode"] == "attested"


def test_cli_override_is_recorded_as_label(tmp_path):
    t, out = transcript(tmp_path), tmp_path / "out"
    p = write(tmp_path / "p.json", proposals())
    a = answers_for_all()
    a["goal"] = {"answer": "no", "p": 0.6, "span": ""}
    a = write(tmp_path / "a.json", a)
    env = {"PATH": "/nonexistent"}
    assert run("check", "--proposals", str(p), "--out", str(out), "--transcript", str(t), "--harness",
               "claude-code", "--answers", str(a), "--answers-from", "subagent", env=env).returncode == 1
    done = run("override", "--out", str(out), "--item", "goal", "--answer", "yes", "--reason", "it is the goal")
    assert done.returncode == 0, done.stderr
    doc = json.loads((out / "readiness.json").read_text())
    goal = by_item(doc)["goal"]
    assert goal["status"] == "settled" and goal["override"] == {"answer": "yes", "reason": "it is the goal"}
    assert doc["pass"] is True


def test_cli_brief_uses_transcript_text_verbatim(tmp_path):
    t = transcript(tmp_path)
    done = run("brief", "--item", "anti_goal", "--turn", "u-anti_goal", "--transcript", str(t), "--harness",
               "claude-code")
    assert done.returncode == 0 and TEXT["anti_goal"] in done.stdout


def test_cli_turns_lists_only_the_persons_turns_with_ids(tmp_path):
    t = transcript(tmp_path)
    with t.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "assistant", "uuid": "a1",
                                 "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}) + "\n")
    done = run("turns", "--transcript", str(t), "--harness", "claude-code")
    assert done.returncode == 0
    listed = json.loads(done.stdout)
    assert [x["id"] for x in listed] == [f"u-{k}" for k in TEXT]
    assert listed[3]["text"] == TEXT["anti_goal"]
