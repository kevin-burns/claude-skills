"""Tests for compare(): did the final record keep what the author approved?

The revision round may only add names the author confirmed. Anything else that changed, a lost
number, a softened "must", a name nobody confirmed, is reported so the second approval is an
informed one.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_record as c

DRAFT = "## Decision\n\nCheckout must respond within `200ms` and never calls billing directly.\n"


def kinds(findings):
    return sorted(f.kind for f in findings)


def test_identical_text_has_no_findings():
    assert c.compare(DRAFT, DRAFT) == []


def test_vanished_number_and_span():
    final = "## Decision\n\nCheckout must respond quickly and never calls billing directly.\n"
    found = c.compare(DRAFT, final)
    assert kinds(found) == ["vanished"]
    assert "200ms" in found[0].message


def test_claim_word_changed():
    for final in (
        DRAFT.replace("must", "should"),
        DRAFT.replace("never", "rarely"),
        "## Decision\n\nOnly checkout must respond within `200ms` and never calls billing directly.\n",
    ):
        assert "claim-word-changed" in kinds(c.compare(DRAFT, final)), final


def test_confirmed_name_may_appear():
    final = DRAFT.replace("billing directly", "billing directly; it uses `ledger/api.py`")
    assert c.compare(DRAFT, final, confirmed=frozenset({"ledger/api.py"})) == []


def test_unconfirmed_name_is_reported():
    final = DRAFT.replace("billing directly", "billing directly; it uses `ledger/db.py`")
    found = c.compare(DRAFT, final)
    assert kinds(found) == ["unconfirmed-name"]
    assert "ledger/db.py" in found[0].message


def test_cli_against_reports_both_passes(tmp_path):
    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    draft = tmp_path / "draft.md"
    draft.write_text("# 1. X\n\nStatus: Proposed\n\n" + DRAFT, encoding="utf-8")
    final = adr / "0001-x.md"
    final.write_text("# 1. X\n\nStatus: Proposed\n\n" + DRAFT.replace("must", "should"), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, c.__file__, str(final), "--repo", str(tmp_path), "--against", str(draft),
         "--intended", "200ms", "--json"],
        capture_output=True, text=True, check=False,
    )
    found = {f["kind"] for f in json.loads(result.stdout)}
    assert {"hedge", "claim-word-changed"} <= found
    assert result.returncode == 1
