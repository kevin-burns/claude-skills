"""Tests for records.py: reading an ADR directory the way people actually write one.

What matters is that the parser never invents structure (a date read as a record number, a
heading-less record treated as broken) and never loses a line's position, because every
finding the self-check reports points the author at a line.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import records as r


def write(dir_: Path, name: str, text: str) -> Path:
    path = dir_ / name
    path.write_text(text, encoding="utf-8")
    return path


def test_number_from_title_then_filename(tmp_path):
    titled = write(tmp_path, "0003-x.md", "# 7. Billing never reads the ledger\n")
    untitled = write(tmp_path, "0004-y.md", "# Billing never reads the ledger\n")
    assert r.parse_record(titled).number == 7
    assert r.parse_record(untitled).number == 4


def test_title_number_styles(tmp_path):
    styles = ["# 1. T", "# ADR-001: T", "# ADR 001 T", "# [ADR-001] T", "# 001 - T"]
    for i, title in enumerate(styles):
        path = write(tmp_path, f"note-{i}.md", title + "\n")
        assert r.parse_record(path).number == 1, title


def test_dated_filename_is_not_a_number(tmp_path):
    for name in ("2026-01-10-title.md", "20260110-title.md"):
        path = write(tmp_path, name, "# Title\n")
        assert r.parse_record(path).number is None, name


def test_status_in_five_styles(tmp_path):
    texts = [
        "# 1. T\n\nStatus: Accepted\n",
        "# 1. T\n\n**Status:** Accepted\n",
        "# 1. T\n\n| Status | Accepted |\n",
        "---\nstatus: accepted\n---\n# T\n",
        "# 1. T\n\n## Status\n\nAccepted\n",
    ]
    for i, text in enumerate(texts):
        path = write(tmp_path, f"000{i}-s.md", text)
        assert r.parse_record(path).status == "Accepted", text


def test_superseded_by_and_supersedes(tmp_path):
    old = write(tmp_path, "0001-a.md", "# 1. A\n\nStatus: Superseded by ADR-9\n")
    new = write(tmp_path, "0009-b.md", "# 9. B\n\nStatus: Accepted\nSupersedes: ADR-3, ADR-4\n")
    assert r.parse_record(old).status == "Superseded"
    assert r.parse_record(old).superseded_by == 9
    assert r.parse_record(new).supersedes == (3, 4)


def test_section_roles():
    assert r.section_role("Decision") == "decision"
    assert r.section_role("Decision Outcome") == "decision"
    assert r.section_role("Considered Options") == "options"
    assert r.section_role("Pros and Cons of the Options") == "options"
    assert r.section_role("Context and Problem Statement") == "context"
    assert r.section_role("Decision Drivers") == "context"
    assert r.section_role("Consequences") == "consequences"
    assert r.section_role("Notes") == "other"


def test_sections_keep_line_numbers(tmp_path):
    text = "# 1. T\n\n## Context\n\nWhy.\n\n## Decision\n\nUse X.\n"
    rec = r.parse_record(write(tmp_path, "0001-t.md", text))
    assert (9, "Use X.") in rec.sections["decision"]
    assert (5, "Why.") in rec.sections["context"]


def test_paragraph_only_record_parses(tmp_path):
    text = "# Use Postgres\n\nWe use Postgres because the data is relational.\n"
    rec = r.parse_record(write(tmp_path, "0001-p.md", text))
    assert set(rec.sections) == {"other"}
    assert rec.title == "Use Postgres"


def test_crlf_and_bad_bytes(tmp_path):
    path = tmp_path / "0001-c.md"
    path.write_bytes(b"# 1. T\r\n\r\n## Decision\r\nUse \xff X.\r\n")
    rec = r.parse_record(path)
    lines = rec.sections["decision"]
    assert lines[0][0] == 4
    assert "Use" in lines[0][1]


def test_load_records_skips_readme_index_template(tmp_path):
    for name in ("README.md", "index.md", "Template.md", "notes.txt"):
        write(tmp_path, name, "# x\n")
    write(tmp_path, "0001-a.md", "# 1. A\n")
    assert [rec.number for rec in r.load_records(tmp_path)] == [1]


def test_filename_scheme():
    assert r.filename_scheme(Path("0001-a.md")) == "NNNN-slug"
    assert r.filename_scheme(Path("ADR-002-b.md")) == "ADR-NNN-slug"
    assert r.filename_scheme(Path("adr_003_c.md")) == "adr_NNN_slug"
    assert r.filename_scheme(Path("2026-01-10-d.md")) == "date-slug"
    assert r.filename_scheme(Path("notes.md")) == "other"
