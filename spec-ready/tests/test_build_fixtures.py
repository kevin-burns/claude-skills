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


def test_every_scenario_builds_and_loads(tmp_path):
    built = build(tmp_path)
    assert sorted(built) == sorted(e["id"] for e in EVALS) == [f"S{n}" for n in range(1, 9)]
    for case in EVALS:
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
        assert case["expectations"] and case["mode"] in ("session", "gate-only")
