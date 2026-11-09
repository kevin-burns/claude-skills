"""SKILL.md must carry the rules the evals showed were missing or inconsistent (2026-11-09 run).

Each assertion names the failure it guards, so a later edit that drops the rule fails here
before it fails in an expensive eval run.
"""

from pathlib import Path

SKILL = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")


def test_figures_need_sources():
    # Every number or date must come from the author's words or the repo, checked mechanically.
    assert "--sources" in SKILL
    assert "Every fact needs a source" in SKILL


def test_draft_saved_before_writing():
    # The run compared the final file with itself because the draft was copied afterwards.
    assert "Save the approved draft" in SKILL
    assert "before you write the record" in SKILL


def test_advance_approval_is_honoured_consistently():
    # W1/A1 accepted advance approval, W2/W3 refused the same wording.
    assert "If the request already approves" in SKILL


def test_no_placeholders_in_a_written_record():
    # The cold reader failed a record that shipped with [... NEEDED] placeholders.
    assert "Never write a record that still has a placeholder" in SKILL


def test_confirmed_names_belong_in_the_decision():
    # W1 put a confirmed name only in Context.
    assert "in Decision or Consequences" in SKILL
