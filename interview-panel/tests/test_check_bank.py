import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import check_bank  # noqa: E402

SEATS = {"head-of-cloud", "head-of-hr"}

GOOD = """\
### HC01 A title
- seat: head-of-cloud
- topic: strategy
- type: strategic
- level: both
- question: Why?
- strong answer contains:
  - a reason
- red flags:
  - no reason
- follow-ups:
  - and then?
- source: https://example.org/x (retrieved 2026-09-24)
- source-type: answer
- evidence: "a sentence that is on the page"
"""


def problems(text):
    return check_bank.problems(check_bank.parse(text), SEATS)


def test_the_bundled_banks_are_valid():
    """The real files, not a fixture: this is the check that matters."""
    assert check_bank.main([]) == 0


def test_every_persona_has_a_bank_and_every_bank_seat_a_persona():
    seats = check_bank.seats_defined()
    banked = set()
    for f in check_bank.BANKS.glob("*.md"):
        banked |= {b["seat"] for b in check_bank.parse(f.read_text()).values()}
    assert seats and seats == banked


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
    assert problems(GOOD) == []


def test_a_url_source_without_an_evidence_quote_fails():
    """Presence is not support: the rule the first bank broke 20 times."""
    text = GOOD.replace('- evidence: "a sentence that is on the page"\n', "")
    assert any("evidence quote" in p for p in problems(text))


def test_an_unsourced_rubric_is_allowed_when_it_says_so():
    text = (GOOD.replace("https://example.org/x (retrieved 2026-09-24)", "none (common practice)")
                .replace("source-type: answer", "source-type: none")
                .replace('- evidence: "a sentence that is on the page"\n', ""))
    assert problems(text) == []


def test_source_none_with_a_real_source_type_fails():
    text = GOOD.replace("https://example.org/x (retrieved 2026-09-24)", "none (common practice)")
    assert any("source is none" in p for p in problems(text))


def test_a_source_without_a_retrieval_date_fails():
    assert any("retrieved" in p for p in problems(GOOD.replace(" (retrieved 2026-09-24)", "")))


def test_an_empty_list_field_fails():
    assert any("red flags" in p for p in problems(GOOD.replace("  - no reason\n", "")))


def test_a_seat_with_no_persona_fails():
    assert any("no persona" in p for p in problems(GOOD.replace("head-of-cloud", "head-of-sales")))


def test_an_unknown_type_fails():
    assert any("unknown type" in p for p in problems(GOOD.replace("type: strategic", "type: vibes")))


def test_a_duplicate_id_fails():
    assert any("duplicate" in p for p in problems(GOOD + GOOD))


def test_an_empty_file_fails_rather_than_passing():
    """A pass over nothing is not evidence."""
    assert problems("") == ["no question blocks found"]


def test_verify_finds_a_quote_and_rejects_a_missing_one():
    cache = {"https://example.org/x": check_bank._norm("Intro. A sentence that is on the page. End.")}
    blocks = check_bank.parse(GOOD)
    assert check_bank.verify(blocks, cache) == ([], [])
    blocks["HC01"]["evidence"] = '"a sentence the page never says"'
    assert check_bank.verify(blocks, cache)[1] == ["HC01: quote not found on https://example.org/x"]


def test_verify_reports_an_unreachable_page_apart_from_a_verdict():
    cache = {"https://example.org/x": OSError("blocked")}
    unreachable, unsupported = check_bank.verify(check_bank.parse(GOOD), cache)
    assert unreachable and not unsupported


def test_verify_normalises_curly_quotes_and_dashes():
    cache = {"https://example.org/x": check_bank._norm("It’s a sentence — on the page")}
    blocks = check_bank.parse(GOOD.replace("a sentence that is on the page", "It's a sentence - on the page"))
    assert check_bank.verify(blocks, cache) == ([], [])
