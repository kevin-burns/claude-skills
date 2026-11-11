"""SKILL.md contract: the instructions the checks rely on are present and match the CLI."""

import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")
README = (SKILL / "README.md").read_text(encoding="utf-8")


def front_matter() -> str:
    match = re.match(r"^---\n(.*?)\n---\n", TEXT, re.DOTALL)
    assert match
    return match.group(1)


def test_front_matter():
    fm = front_matter()
    assert re.search(r"^name: spec-to-tickets$", fm, re.MULTILINE)
    assert re.search(r"^license: MIT$", fm, re.MULTILINE)
    description = fm.split("description:", 1)[1]
    for phrase in ("break the spec into tickets", "prd-to-tickets", "prioritise", "what do we build first",
                   "existing breakdown"):
        assert phrase in description, phrase
    assert len(description.strip()) <= 1024


def test_the_five_rules():
    for heading in ("Prioritise by outcome", "Vertical first", "No invented scope",
                    "The person confirms; the script checks", "No personal data in the skill"):
        assert heading in TEXT, heading


def test_commands_and_steps():
    assert "check_tickets.py check" in TEXT and "check_tickets.py accept" in TEXT
    assert "Run check_tickets.py accept only when the person says so" in TEXT
    assert "walking skeleton" in TEXT
    assert "in one round" in TEXT and "confirms" in TEXT


def test_handover_and_trackers():
    assert "superpowers:writing-plans" in TEXT and "just in time" in TEXT
    assert "only when the person asks" in TEXT
    for tracker in ("bd create", "gh issue create", "use-linearis"):
        assert tracker in TEXT, tracker


def test_references_exist_and_are_linked():
    for name in ("tickets-format.md", "rules.md", "worked-example.md", "dsdm.md"):
        assert (SKILL / "references" / name).is_file(), name
        assert f"references/{name}" in TEXT, name


def test_credit_and_copyright_note():
    for name in ("Matt Pocock", "to-tickets", "Cole Medin", "plan-create-stories", "piv-slice-epic",
                 "Hunt", "Thomas", "DSDM Consortium"):
        assert name in TEXT, name
    dsdm = (SKILL / "references" / "dsdm.md").read_text(encoding="utf-8")
    assert "all rights reserved" in dsdm and "paraphrase" in dsdm.lower()


def test_worked_example_passes_the_checks():
    import sys
    sys.path.insert(0, str(SKILL / "scripts"))
    from check_tickets import run_checks
    from tickets_md import parse

    example = (SKILL / "references" / "worked-example.md").read_text(encoding="utf-8")
    block = re.search(r"```markdown\n(---\n.*?)```", example, re.DOTALL).group(1)
    prd = re.search(r"```text\n(.*?)```", example, re.DOTALL).group(1)
    tickets, problems = parse(block)
    assert problems == []
    assert run_checks(tickets, prd, None) == []
    assert tickets.accepted and any(s.kind == "prefactor" for s in tickets.slices())
