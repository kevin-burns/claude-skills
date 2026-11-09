"""SKILL.md must carry the rules the evals showed were missing or inconsistent (2026-11-09 run).

Each assertion names the failure it guards, so a later edit that drops the rule fails here
before it fails in an expensive eval run.
"""

import re
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


def test_complete_example_record_is_shipped_and_linked():
    # Asked for 2026-11-09: one finished record to imitate, not just fragments.
    example = Path(__file__).resolve().parents[1] / "references" / "example-adr.md"
    assert "references/example-adr.md" in SKILL
    text = example.read_text(encoding="utf-8")
    for part in ("## Context", "## Decision", "## Consequences", "## Considered Options", "Status:"):
        assert part in text, part
    assert "NEEDED" not in text


AMEND = (Path(__file__).resolve().parents[1] / "references" / "amend.md").read_text(encoding="utf-8")


def test_scratch_files_live_in_the_per_record_directory():
    # r2: W4 found W3's notes in a shared temp file with a fixed name.
    for text in (SKILL, AMEND):
        for name in ("notes.md", "approved-draft.md"):
            for match in re.finditer(re.escape(name), text):
                assert text[max(0, match.start() - 3):match.start()] == '$D/', text[match.start() - 30:match.end()]
    assert "mktemp" in SKILL


def test_draft_shown_as_text_not_only_in_a_command():
    # r2: W3 and A1 wrote the record without showing the draft outside a heredoc.
    assert "Show the full draft as text in your reply" in " ".join(SKILL.split())


def test_script_is_found_wherever_the_skill_is_installed():
    # r2: A1 spent turns locating check_record.py under a project install.
    assert "find " in SKILL and "check_record.py" in SKILL


def test_amend_mode_compares_with_the_committed_record():
    # r2: A1 copied its own edited record in as the 'approved draft'.
    assert "--baseline" in AMEND
    assert "git diff" in AMEND
