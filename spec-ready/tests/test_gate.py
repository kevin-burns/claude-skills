"""The gate: settled means a real user turn, a verifier's yes with a matching span, and no edits since.

Verifiers are faked here; the CLI tests run gate.py as a subprocess against fixture transcripts
with an answers file, so nothing calls a model.
"""

import json
import re
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


def test_no_transcript_is_attested_never_settled_and_never_passes():
    # Review finding 4: without a transcript the agent's own statement must not settle anything.
    called = []

    class Spy(Yes):
        def verify(self, item, turn_text):
            called.append(item.key)
            return super().verify(item, turn_text)

    doc = run_gate(proposals(), DEFAULT_ITEMS, None, [Spy()], None)
    assert doc["mode"] == "attested" and doc["pass"] is False and called == []
    assert {r["status"] for r in doc["items"]} == {"attested"}


def test_verifications_run_in_parallel():
    # Review finding 10: eight items must not take eight times one call.
    import time

    class Slow(Yes):
        def verify(self, item, turn_text):
            time.sleep(0.4)
            return super().verify(item, turn_text)

    start = time.monotonic()
    assert run_gate(proposals(), DEFAULT_ITEMS, turns(), [Slow()], None)["pass"] is True
    assert time.monotonic() - start < 1.5


def test_override_from_a_previous_run_needs_the_same_turn_and_hash():
    first = run_gate(proposals(), DEFAULT_ITEMS, turns(), [Answer("no")], None)
    goal = by_item(first)["goal"]
    goal["override"] = {"answer": "yes", "turn": "u-goal", "quote": "dictation"}
    again = run_gate(proposals(), DEFAULT_ITEMS, turns(), [Answer("no")], first)
    assert by_item(again)["goal"]["status"] == "settled"
    edited = turns()
    edited["u-goal"] = Turn("u-goal", "Something else entirely.")
    assert by_item(run_gate(proposals(), DEFAULT_ITEMS, edited, [Answer("no")], first))["goal"]["status"] == "open"


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


SESSION = "sess-1"


def session(tmp_path: Path, extra: list[dict] = ()) -> dict:
    """A repo dir plus its Claude Code transcript where the gate itself will look for it."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9-]", "-", str(repo.resolve()))
    lines = [{"type": "user", "uuid": f"u-{k}", "message": {"role": "user", "content": v}} for k, v in TEXT.items()]
    lines += list(extra)
    write(tmp_path / ".claude" / "projects" / slug / f"{SESSION}.jsonl", "".join(json.dumps(x) + "\n" for x in lines))
    return {"HOME": str(tmp_path), "CLAUDE_CODE_SESSION_ID": SESSION, "PATH": "/nonexistent"}


def run(tmp_path: Path, *args, env=None):
    return subprocess.run([sys.executable, str(GATE), *args], capture_output=True, text=True, check=False,
                          env=env, cwd=tmp_path / "repo")


def answers_for_all():
    return {k: {"answer": "yes", "p": 0.8, "span": TEXT[k][:15]} for k in TEXT}


def check(tmp_path, env, *extra):
    p = write(tmp_path / "p.json", proposals())
    return run(tmp_path, "check", "--proposals", str(p), "--out", str(tmp_path / "out"), *extra, env=env)


def readiness_doc(tmp_path):
    return json.loads((tmp_path / "out" / "readiness.json").read_text())


def test_cli_exit_codes_and_readiness_file(tmp_path):
    env = session(tmp_path)
    a = write(tmp_path / "a.json", answers_for_all())
    done = check(tmp_path, env, "--answers", str(a), "--answers-from", "subagent")
    assert done.returncode == 0, done.stdout + done.stderr
    doc = readiness_doc(tmp_path)
    assert doc["pass"] and doc["verifiers"] == ["subagent"] and doc["verification"] == "agent-relayed"
    # Review finding 1/6: where the evidence and the verifier came from is on record, as a
    # fingerprint, never as a local path: readiness.json is copied beside the PRD and committed.
    assert doc["harness"] == "claude-code" and len(doc["transcript_id"]) == 16
    assert doc["environment"] == {"claude_cli_found": False}
    assert doc["person_turns"] == [f"u-{k}" for k in TEXT]
    text = (tmp_path / "out" / "readiness.json").read_text()
    assert str(tmp_path) not in text and "/Users/" not in text and "/home/" not in text


def test_cli_has_no_transcript_flag(tmp_path):
    env = session(tmp_path)
    planted = write(tmp_path / "planted.jsonl", "")
    done = check(tmp_path, env, "--transcript", str(planted))
    assert done.returncode != 0 and "unrecognized arguments" in done.stderr


def test_cli_answers_from_is_required(tmp_path):
    env = session(tmp_path)
    a = write(tmp_path / "a.json", answers_for_all())
    done = check(tmp_path, env, "--answers", str(a))
    assert done.returncode == 1 and "--answers-from" in done.stderr


def test_cli_session_model_answers_are_self_assessed(tmp_path):
    env = session(tmp_path)
    a = write(tmp_path / "a.json", answers_for_all())
    assert check(tmp_path, env, "--answers", str(a), "--answers-from", "session-model").returncode == 0
    assert readiness_doc(tmp_path)["verification"] == "self-assessed"


def fake_claude(tmp_path: Path, reply: str) -> str:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    write(bin_dir / "claude", f"#!/bin/sh\ncat >/dev/null\nprintf '%s' '{reply}'\n").chmod(0o755)
    return str(bin_dir)


def test_cli_refuses_answers_file_when_an_independent_verifier_works(tmp_path):
    env = session(tmp_path)
    env["PATH"] = fake_claude(tmp_path, json.dumps({"is_error": False, "result": '{"answer":"no","p":0.9,"span":""}'}))
    a = write(tmp_path / "a.json", answers_for_all())
    done = check(tmp_path, env, "--answers", str(a), "--answers-from", "session-model")
    assert done.returncode == 1 and "independent verifier" in done.stderr


def test_cli_broken_verifier_exit_4_then_answers_allowed(tmp_path):
    # Review finding 11: a broken login is reported, and the subagent path opens.
    env = session(tmp_path)
    env["PATH"] = fake_claude(tmp_path, json.dumps({"is_error": True, "result": "Invalid API key"}))
    done = check(tmp_path, env)
    assert done.returncode == 4 and "verifier unavailable" in done.stderr
    a = write(tmp_path / "a.json", answers_for_all())
    assert check(tmp_path, env, "--answers", str(a), "--answers-from", "subagent").returncode == 0


def test_cli_no_transcript_exit_2_and_not_passed(tmp_path):
    (tmp_path / "repo").mkdir()
    env = {"HOME": str(tmp_path), "PATH": "/nonexistent"}
    a = write(tmp_path / "a.json", answers_for_all())
    done = check(tmp_path, env, "--answers", str(a), "--answers-from", "session-model")
    assert done.returncode == 2
    doc = readiness_doc(tmp_path)
    assert doc["mode"] == "attested" and doc["pass"] is False and doc["verification"] == "none"


def test_cli_accept_attested_records_the_acknowledgement(tmp_path):
    (tmp_path / "repo").mkdir()
    env = {"HOME": str(tmp_path), "PATH": "/nonexistent"}
    a = write(tmp_path / "a.json", answers_for_all())
    check(tmp_path, env, "--answers", str(a), "--answers-from", "session-model")
    done = run(tmp_path, "accept-attested", "--out", str(tmp_path / "out"), "--reason", "go ahead unverified",
               env=env)
    assert done.returncode == 0
    assert readiness_doc(tmp_path)["attested_ack"] == "go ahead unverified"


def override(tmp_path, env, *args):
    return run(tmp_path, "override", "--out", str(tmp_path / "out"), *args, env=env)


def test_cli_override_needs_a_quote_from_a_real_user_turn(tmp_path):
    # Review finding 5: an override carries its own evidence through the same chain.
    env = session(tmp_path, extra=[{"type": "user", "uuid": "u-ok",
                                    "message": {"role": "user", "content": "The goal answer is fine, overrule it."}}])
    a = answers_for_all()
    a["goal"] = {"answer": "no", "p": 0.6, "span": ""}
    a = write(tmp_path / "a.json", a)
    assert check(tmp_path, env, "--answers", str(a), "--answers-from", "subagent").returncode == 1
    assert override(tmp_path, env, "--item", "goal", "--turn", "u-missing", "--quote", "x").returncode == 1
    assert override(tmp_path, env, "--item", "goal", "--turn", "u-ok", "--quote", "not said").returncode == 1
    done = override(tmp_path, env, "--item", "goal", "--turn", "u-ok", "--quote", "overrule it")
    assert done.returncode == 0, done.stderr
    doc = readiness_doc(tmp_path)
    goal = by_item(doc)["goal"]
    assert goal["status"] == "settled" and goal["override"]["turn"] == "u-ok" and doc["pass"] is True


def test_cli_brief_uses_transcript_text_verbatim(tmp_path):
    env = session(tmp_path)
    done = run(tmp_path, "brief", "--item", "anti_goal", "--turn", "u-anti_goal", env=env)
    assert done.returncode == 0 and TEXT["anti_goal"] in done.stdout


def test_cli_turns_lists_only_the_persons_turns_with_ids(tmp_path):
    env = session(tmp_path, extra=[{"type": "assistant", "uuid": "a1",
                                    "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}])
    done = run(tmp_path, "turns", env=env)
    assert done.returncode == 0
    listed = json.loads(done.stdout)
    assert [x["id"] for x in listed] == [f"u-{k}" for k in TEXT]
