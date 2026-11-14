"""Headings in singular or plural mean the same section (claude-skills-knvc, 2026-11-14).

A PRD headed '## Anti-goals' was not read as the anti-goal, so a Must quoting it failed the trace
check; a PRD headed '## Non-goal' was not read as a non-goal, so a Must could trace to it."""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))

from check_tickets import check_scope, check_trace
from tickets_md import Criterion, Increment, Slice, Tickets

OK = (Criterion("works", "the goal"),)


def prd(goal="Goal", success="Success check", anti="Anti-goal", non="Non-goals"):
    return f"""# Thing

## {goal}

Bills explained so every figure traces to a record.

## {success}

pytest shows the reasons add up exactly.

## {anti}

- Nothing left unexplained is hidden.

## {non}

- No tariff or switching advice at all.
"""


def tickets(traces):
    s = Slice(id="T1", title="T1", moscow="Must", size="S", layers=("a",), kind="slice", traces=traces,
              acceptance=OK, line=1)
    return Tickets({"layers": ["a"]}, (Increment(1, "one", (s,)),), ())


@pytest.mark.parametrize("anti", ["Anti-goal", "Anti-goals", "Anti-Goals"])
def test_anti_goal_heading_any_number(anti):
    assert check_trace(tickets('"Nothing left unexplained is hidden."'), prd(anti=anti), None) == []


@pytest.mark.parametrize("goal,success", [("Goal", "Success check"), ("Goals", "Success checks")])
def test_goal_and_success_headings_any_number(goal, success):
    text = prd(goal=goal, success=success)
    assert check_trace(tickets('"Bills explained so every figure traces"'), text, None) == []
    assert check_trace(tickets('"pytest shows the reasons add up exactly"'), text, None) == []


@pytest.mark.parametrize("non", ["Non-goals", "Non-goal"])
def test_non_goal_heading_any_number_never_traces(non):
    text = prd(non=non)
    assert check_trace(tickets('"No tariff or switching advice at all"'), text, None)


@pytest.mark.parametrize("heading", ["Assumption", "Open question", "Risk"])
def test_singular_never_sections_stay_out_of_scope(heading):
    text = (f"# Thing\n\n## Goal\n\nBills explained so every figure traces.\n\n"
            f"## {heading}\n\n- Tariff advice for every customer later.\n")
    s = Slice(id="T2", title="T2", moscow="Could", size="S", layers=("a",), kind="slice",
              traces='"Tariff advice for every customer later"', acceptance=OK, line=1)
    t = Tickets({"layers": ["a"]}, (Increment(1, "one", (s,)),), ())
    assert check_scope(t, text, "", None), heading
