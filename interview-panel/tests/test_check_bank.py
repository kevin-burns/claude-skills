import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import check_bank  # noqa: E402

GOOD = """\
### Q01 A title
- seat: head-of-cloud
- topic: strategy
- level: both
- question: Why?
- strong answer contains:
  - a reason
- red flags:
  - no reason
- follow-ups:
  - and then?
- source: https://example.org/x (retrieved 2026-09-23)
"""


def test_the_bundled_bank_is_valid():
    """The real file, not a fixture: this is the check that matters."""
    assert check_bank.main([]) == 0


def test_the_bundled_bank_covers_both_seats():
    blocks = check_bank.parse(check_bank.DEFAULT.read_text())
    assert {b["seat"] for b in blocks.values()} == check_bank.SEATS


# The terms this skill must never contain are the user's own: a candidate, an employer, a
# requisition. Listing them here would publish the very names the check exists to keep out,
# so they live in a local file outside the repo, one per line. With no file the test skips
# and says so; it cannot pass on an empty list.
PRIVATE_TERMS = Path.home() / ".config" / "interview-panel" / "private-terms.txt"


def test_no_private_term_appears_anywhere_in_the_skill():
    if not PRIVATE_TERMS.exists():
        pytest.skip(f"no {PRIVATE_TERMS}; private-term check not run")
    terms = [t.strip() for t in PRIVATE_TERMS.read_text().splitlines() if t.strip()]
    assert terms, "private-terms file is empty"
    skill = Path(__file__).parent.parent
    hits = [f"{f.relative_to(skill)}: {t}"
            for f in skill.rglob("*") if f.is_file() and "__pycache__" not in f.parts
            for t in terms if t.lower() in f.read_text(errors="ignore").lower()]
    assert hits == []


def test_a_complete_block_passes():
    assert check_bank.problems(check_bank.parse(GOOD)) == []


def test_a_block_with_no_source_fails():
    text = GOOD.replace("- source: https://example.org/x (retrieved 2026-09-23)\n", "")
    assert any("'source'" in p for p in check_bank.problems(check_bank.parse(text)))


def test_a_source_without_a_retrieval_date_fails():
    text = GOOD.replace(" (retrieved 2026-09-23)", "")
    assert any("retrieved" in p for p in check_bank.problems(check_bank.parse(text)))


def test_an_empty_list_field_fails():
    text = GOOD.replace("  - no reason\n", "")
    assert any("red flags" in p for p in check_bank.problems(check_bank.parse(text)))


def test_an_unknown_seat_fails():
    text = GOOD.replace("head-of-cloud", "head-of-sales")
    assert any("unknown seat" in p for p in check_bank.problems(check_bank.parse(text)))


def test_a_duplicate_id_fails():
    assert any("duplicate" in p for p in check_bank.problems(check_bank.parse(GOOD + GOOD)))


def test_an_empty_file_fails_rather_than_passing():
    """A pass over nothing is not evidence."""
    assert check_bank.problems(check_bank.parse("")) == ["no question blocks found"]
