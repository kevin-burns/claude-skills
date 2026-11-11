"""Routing cases are generated in the layout `claude plugin eval` reads."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

from make_routing_cases import write_cases


def test_sixteen_cases_with_graders(tmp_path):
    cases = write_cases(tmp_path)
    assert len(cases) == 16
    assert sum(c.name.startswith("spec-to-tickets-route-") for c in cases) == 8
    silent = (tmp_path / "spec-to-tickets-not-01" / "graders" / "fired.md").read_text()
    assert "max: 0" in silent and "spec-to-tickets" in silent
