"""Eval fixtures: each scenario is a synthetic session the real reader can load."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(HERE / "evals"))

from build_fixtures import build
from transcripts import load_user_turns

EVALS = json.loads((HERE / "evals" / "evals.json").read_text(encoding="utf-8"))["evals"]


SCENARIOS = [e for e in EVALS if "turns" in e]


def test_every_scenario_builds_and_loads(tmp_path):
    built = build(tmp_path)
    assert sorted(built) == sorted(e["id"] for e in SCENARIOS) == [f"S{n}" for n in range(1, 10)]
    for case in SCENARIOS:
        turns = load_user_turns(built[case["id"]] / "transcript.jsonl", "claude-code")
        assert [t.text for t in turns] == case["turns"]
        assert (built[case["id"]] / "repo" / ".git").is_dir()
        assert json.loads((built[case["id"]] / "proposals.json").read_text())


def test_s1_has_no_anti_goal_turn():
    s1 = next(e for e in EVALS if e["id"] == "S1")
    assert not any("clone" in t for t in s1["turns"])


def test_s3_is_paraphrase_only():
    s3 = next(e for e in EVALS if e["id"] == "S3")
    joined = " ".join(s3["turns"]).lower()
    for label in ("anti-goal", "non-goal", "success check", "verification strategy", "boundary"):
        assert label not in joined


def test_proposals_cite_the_affirmation_turns_in_s2(tmp_path):
    built = build(tmp_path)
    proposals = json.loads((built["S2"] / "proposals.json").read_text())
    turns = {t.id: t.text for t in load_user_turns(built["S2"] / "transcript.jsonl", "claude-code")}
    cited = {p["item"]: turns[p["turn"]] for p in proposals}
    assert cited["non_goals"] == "Sounds fine." and cited["anti_goal"] == "Sure."


def test_expectations_and_modes():
    for case in EVALS:
        assert case["expectations"] and case["mode"] in ("session", "gate-only", "verifier")


def test_expectations_are_arm_neutral():
    # Eval 2026-11-11: expectations naming the skill's own files or scripts could not grade the
    # other arms fairly. Session expectations describe what happened, not how spec-ready does it.
    for case in (e for e in EVALS if e["mode"] == "session"):
        for text in case["expectations"]:
            for word in ("gate.py", "readiness.json", "[turn:", "check_sources", "prd.md", "spec.md"):
                assert word not in text, (case["id"], text)
        assert any("nothing beyond what was asked" in t for t in case["expectations"]), case["id"]


def test_s9_invites_a_bare_affirmation_for_the_anti_goal():
    s9 = next(e for e in EVALS if e["id"] == "S9")
    assert "Sure." in s9["turns"] and s9["item_turns"]["anti_goal"] == s9["turns"].index("Sure.")


def test_verifier_case_reuses_a_scenario_with_weak_proposals():
    v = next(e for e in EVALS if e["mode"] == "verifier")
    source = next(e for e in EVALS if e["id"] == v["source"])
    weak = {k for k, i in source["item_turns"].items() if source["turns"][i] in ("Sounds fine.", "Sure.")}
    assert weak == {"non_goals", "anti_goal"}


def test_scenarios_answer_the_usual_clarifying_questions():
    # Eval 2026-11-11: the scripted person never answered "local or cloud, which Mac, what latency".
    for case in (e for e in EVALS if e["mode"] == "session"):
        joined = " ".join(case["turns"]).lower()
        assert "locally" in joined and "second" in joined, case["id"]
