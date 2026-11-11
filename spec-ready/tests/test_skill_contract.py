"""SKILL.md contract: the instructions the gate relies on are present and say what the spec says.

Instruction text alone failed twice in adr-author's evals, so the script is the gate; these tests
pin the instructions that send the agent to the script and keep it from routing around it.
"""

import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")
README = (SKILL / "README.md").read_text(encoding="utf-8")


def front_matter() -> str:
    match = re.match(r"^---\n(.*?)\n---\n", TEXT, re.DOTALL)
    assert match, "SKILL.md needs YAML front matter"
    return match.group(1)


def test_front_matter():
    fm = front_matter()
    assert re.search(r"^name: spec-ready$", fm, re.MULTILINE)
    assert re.search(r"^license: MIT$", fm, re.MULTILINE)
    description = fm.split("description:", 1)[1]
    assert "ready to spec" in description and "PRD" in description
    assert "after" in description and "plan" in description


def test_the_four_rules():
    for heading in ("Evidence comes from the person, not the agent", "Never pretend to be verified",
                    "No invented facts", "No personal data in the skill"):
        assert heading in TEXT, heading


def test_commands_named():
    for command in ("gate.py turns", "gate.py check", "gate.py brief", "gate.py override", "check_sources.py"):
        assert command in TEXT, command


def test_never_write_while_gate_fails():
    assert "Never write prd.md or spec.md while gate.py exits non-zero" in TEXT
    assert "explicitly agrees to continue unverified" in TEXT


def test_override_only_on_the_persons_word():
    assert "Run gate.py override only when the person says so" in TEXT


def test_subagent_brief_verbatim_and_no_self_answers():
    assert "paste the output of `gate.py brief` verbatim" in TEXT
    assert "never answer a brief yourself while a subagent tool exists" in TEXT


def test_question_round_format():
    assert "least-certain first" in TEXT and "❓" in TEXT and "➡️" in TEXT


def test_boundaries_and_handover():
    assert "software-design-rules" in TEXT and "references/boundary-questions.md" in TEXT
    assert "superpowers:writing-plans" in TEXT
    for tracker in ("linearis", "beads", "gh issue"):
        assert tracker in TEXT, tracker
    assert "only when the person asks" in TEXT


def test_hook_is_opt_in_and_documented():
    assert "opt-in" in TEXT
    assert "hooks/guard.py" in README and "PreToolUse" in README


def test_credit():
    assert "to-spec" in TEXT and "Matt Pocock" in TEXT and "MIT" in TEXT


def test_templates_sections():
    prd = (SKILL / "references" / "prd-template.md").read_text(encoding="utf-8")
    spec = (SKILL / "references" / "spec-template.md").read_text(encoding="utf-8")
    for section in ("Problem", "Who it is for", "Goal", "Non-goals", "Anti-goal", "Success check", "Assumptions"):
        assert f"## {section}" in prd, section
    assert "Readiness: verified" in prd
    for section in ("Solution", "User stories", "Implementation decisions", "Verification strategy and test seams",
                    "Boundaries and rules applied", "Out of scope"):
        assert f"## {section}" in spec, section


def test_instructions_match_the_reviewed_cli():
    # Final review fixes: the instructions must describe the CLI as it now is.
    assert "--transcript" not in TEXT
    assert "from the repository root" in TEXT
    assert 'gate.py override --out $D --item <key> --turn <id> --quote "<their words>"' in TEXT
    assert "gate.py accept-attested" in TEXT
    assert "Exit 4" in TEXT and "verifier unavailable" in TEXT
    assert "--answers-from subagent" in TEXT and "--answers-from session-model" in TEXT
    assert "timeout" in TEXT and "Verifier:" in TEXT
    assert "appending a turn" in README and "--resume" in README


def test_open_questions_and_spec_sources_are_described():
    assert "--spec <dir>/spec.md" in TEXT
    prd = (SKILL / "references" / "prd-template.md").read_text(encoding="utf-8")
    spec = (SKILL / "references" / "spec-template.md").read_text(encoding="utf-8")
    assert "## Open questions" in prd and "Open question:" in prd
    assert "Proposed:" in spec and "[turn:<id>]" in spec
