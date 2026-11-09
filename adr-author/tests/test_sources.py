"""Tests for the figure check: every number in a record must come from somewhere.

A record is evidence for the team. A number nobody said ("p99 under 200ms", "two outages",
"saves 30%") reads as measured fact, so each one must appear in the author's own words.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_record as c

RECORD = (
    "# 4. Checkout calls billing asynchronously\n\nDate: 2026-11-09\nStatus: Proposed\n\n"
    "## Context\n\nThree outages last quarter came from slow billing calls, costing 40% of checkouts.\n\n"
    "## Decision\n\nCheckout never calls billing synchronously; replies arrive within 200ms. See ADR-2.\n"
)


def figures_of(text, sources):
    return sorted(f.message.split("'")[1] for f in c.unsourced_figures(text, sources))


def test_figures_missing_from_sources_are_reported():
    assert figures_of(RECORD, "billing calls were slow") == ["200ms", "40%", "three outages"]


def test_figures_in_sources_pass():
    sources = "We had three outages; 40% of checkouts failed; the target is 200ms."
    assert figures_of(RECORD, sources) == []


def test_digit_and_word_forms_match():
    assert figures_of("## Context\n\nWe had 3 outages.\n", "three outages") == []
    assert figures_of("## Context\n\nWe had three outages.\n", "3 outages") == []


def test_date_line_title_and_record_refs_are_exempt():
    text = "# 7. Title\n\nDate: 2026-01-03\nStatus: Accepted\n\n## Decision\n\nSee ADR-2 and record 5.\n"
    assert figures_of(text, "") == []


def test_compare_reports_new_figure():
    found = c.compare("## Decision\n\nReplies arrive quickly.\n", "## Decision\n\nReplies arrive within 200ms.\n")
    assert [f.kind for f in found] == ["new-figure"]


def test_cli_sources_flag(tmp_path):
    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    rec = adr / "0004-x.md"
    rec.write_text(RECORD, encoding="utf-8")
    notes = tmp_path / "notes.md"
    notes.write_text("billing calls were slow", encoding="utf-8")
    out = subprocess.run([sys.executable, c.__file__, str(rec), "--repo", str(tmp_path), "--sources", str(notes),
                          "--json"], capture_output=True, text=True, check=False)
    assert {f["kind"] for f in json.loads(out.stdout)} >= {"unsourced-figure"}


def test_amended_line_date_is_exempt():
    assert figures_of("Status: Accepted\nAmended: 2026-11-09. Batch jobs may read.\n", "") == []
