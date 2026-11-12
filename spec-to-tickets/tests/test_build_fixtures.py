"""Eval fixtures: each case gets a repository with the PRD, spec and its starting breakdown."""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(HERE / "evals"))

from build_fixtures import build
from check_tickets import check_vertical
from tickets_md import parse

EVALS = json.loads((HERE / "evals" / "evals.json").read_text(encoding="utf-8"))["evals"]


def test_every_case_builds(tmp_path):
    built = build(tmp_path)
    assert sorted(built) == ["T1", "T2", "T3", "T4"]
    for case in EVALS:
        repo = built[case["id"]]
        fixture = case.get("fixture", "dictation")
        assert (repo / ".git").is_dir()
        for name in ("prd.md", "spec.md"):
            assert (repo / "docs" / "specs" / fixture / name).is_file()
        assert (repo / "docs" / "specs" / fixture / "readiness.json").is_file() == (fixture == "dictation")


def test_t2_starts_horizontal(tmp_path):
    repo = build(tmp_path)["T2"]
    tickets, problems = parse((repo / "docs" / "breakdown-horizontal.md").read_text())
    assert problems == [] and {f.slice for f in check_vertical(tickets)} == {"B1", "B2", "B3"}


def test_t3_has_issue_files_only(tmp_path):
    repo = build(tmp_path)["T3"]
    assert len(list((repo / "docs" / "issues").glob("*.md"))) == 3


def test_t4_starts_over_the_must_limit(tmp_path):
    """T4 exists to exercise the over-60% path: its starting breakdown must actually be over it."""
    repo = build(tmp_path)["T4"]
    text = (repo / "docs" / "breakdown-rota.md").read_text()
    points = {"S": 1, "M": 2, "L": 4}
    items = re.findall(r"Priority: (\w+)\. Size: ([SML])\.", text)
    must = sum(points[size] for priority, size in items if priority == "Must")
    assert len(items) == 5 and must / sum(points[size] for _, size in items) > 0.6


def test_expectations_are_arm_neutral():
    for case in EVALS:
        for text in case["expectations"]:
            for word in ("tickets.md", "check_tickets", "MoSCoW", "spec-to-tickets"):
                assert word not in text, (case["id"], text)
