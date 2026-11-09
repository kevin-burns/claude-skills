"""Tests for the routing case generator.

Routing cases are generated from one JSON file into the root evals/ layout that
`claude plugin eval` reads. A should-not case must use a grader that passes only when the skill
did NOT fire; getting that inverted would turn every false positive into a pass.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "evals"))

import make_routing_cases as m


def test_routing_json_has_ten_and_ten():
    data = json.loads((HERE / "evals" / "routing.json").read_text(encoding="utf-8"))
    assert len(data["should_trigger"]) == 10
    assert len(data["should_not"]) == 10


def test_twenty_cases_written(tmp_path):
    written = m.write_cases(tmp_path)
    assert len(written) == 20
    assert all((p / "prompt.md").is_file() and (p / "graders" / "fired.md").is_file() for p in written)


def test_front_matter_present(tmp_path):
    for case in m.write_cases(tmp_path):
        prompt = (case / "prompt.md").read_text(encoding="utf-8")
        assert prompt.startswith("---\nmax_turns: ")
        assert "allowed_tools: " in prompt.split("---")[1]
        grader = (case / "graders" / "fired.md").read_text(encoding="utf-8")
        assert grader.startswith("---\ntype: tool_used\ntool: Skill\n")
        assert "adr-author" in grader


def test_should_not_graders_invert(tmp_path):
    for case in m.write_cases(tmp_path):
        grader = (case / "graders" / "fired.md").read_text(encoding="utf-8")
        if "-not-" in case.name:
            assert "min: 0\nmax: 0\n" in grader
        else:
            assert "max: 0" not in grader


def test_rewriting_is_idempotent(tmp_path):
    first = {p.name: (p / "prompt.md").read_text() for p in m.write_cases(tmp_path)}
    second = {p.name: (p / "prompt.md").read_text() for p in m.write_cases(tmp_path)}
    assert first == second
