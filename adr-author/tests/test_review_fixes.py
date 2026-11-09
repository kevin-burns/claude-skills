"""Regression tests for the final branch review (2026-11-09) and the third eval round.

Each test reproduces a reviewer probe or a grader finding; it failed before its fix.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))

import check_record as c
import records as r

SKILL = (HERE / "SKILL.md").read_text(encoding="utf-8")
FLAT = " ".join(SKILL.split())


def make(tmp_path, files):
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def kinds(found):
    return [f.kind for f in found]


# Review 1: a '#' comment inside a code fence must not end the Decision section.
def test_hash_line_in_fence_is_not_a_heading(tmp_path):
    rec = ("# 2. X\n\nStatus: Proposed\n\n## Decision\n\n```dockerfile\n# base image\nStatus: Rejected\n```\n\n"
           "Teams should use `src/nothere_py.py`.\n")
    root = make(tmp_path, {"docs/adr/0002-x.md": rec})
    parsed = r.parse_record(root / "docs/adr/0002-x.md")
    assert parsed.status == "Proposed"
    found = kinds(c.check(root / "docs/adr/0002-x.md", root, root / "docs/adr"))
    assert "hedge" in found and "name-not-found" in found


# Review 2: the usual ways of writing a function or a location.
def test_function_and_location_forms_are_found(tmp_path):
    root = make(tmp_path, {"events/outbox.py": "class Outbox:\n    def publish(self):\n        pass\n",
                           "orders/api.py": "def place_order(order):\n    pass\n"})
    adr = root / "docs" / "adr"
    for name in ("place_order()", "Outbox.publish", "Outbox.publish()", "events/outbox.py:2",
                 "events/outbox.py#L2"):
        assert c.looks_like_name(name), name
        assert c.name_exists(name, root, adr), name
    assert not c.name_exists("Outbox.vanish", root, adr)


# Review 3: dated filenames in supersede links and titles.
def test_dated_supersede_links_resolve_by_filename(tmp_path):
    old = "# Use Postgres\n\nStatus: Superseded by 2026-03-01-use-sqlite.md\n"
    new = ("# Use SQLite\n\nStatus: Accepted\nSupersedes: 2026-01-10-use-postgres.md\n\n## Decision\n\n"
           "Orders never call billing.\n")
    root = make(tmp_path, {"docs/adr/2026-01-10-use-postgres.md": old, "docs/adr/2026-03-01-use-sqlite.md": new})
    found = c.check(root / "docs/adr/2026-03-01-use-sqlite.md", root, root / "docs/adr")
    assert "supersede-link" not in kinds(found), [f.message for f in found]
    found_old = c.check(root / "docs/adr/2026-01-10-use-postgres.md", root, root / "docs/adr")
    assert "supersede-link" not in kinds(found_old), [f.message for f in found_old]


def test_dated_title_is_not_a_number(tmp_path):
    p = make(tmp_path, {"2026-01-10-use-x.md": "# 2026-01-10 Use X\n"}) / "2026-01-10-use-x.md"
    rec = r.parse_record(p)
    assert rec.number is None
    assert rec.title == "2026-01-10 Use X"


# Review 4: the script finder must follow symlinked installs and check the usual paths first.
def test_finder_follows_symlinks_and_checks_explicit_paths():
    block = re.search(r'CHECK="\$\((.*?)\)"', SKILL, re.S).group(1)
    assert "find -L" in block
    assert "$HOME/.claude/skills/adr-author/scripts/check_record.py" in SKILL
    assert "$HOME/.agents/skills/adr-author/scripts/check_record.py" in SKILL


def test_finder_line_finds_a_symlinked_install(tmp_path):
    home = tmp_path / "home"
    (home / ".claude" / "skills").mkdir(parents=True)
    os.symlink(HERE, home / ".claude" / "skills" / "adr-author")
    line = re.search(r'^CHECK=.*$', SKILL, re.M).group(0)
    out = subprocess.run(["bash", "-c", line + '; echo "$CHECK"'], cwd=tmp_path, capture_output=True, text=True,
                         env=dict(os.environ, HOME=str(home)), check=False).stdout.strip()
    assert out.endswith("adr-author/scripts/check_record.py"), out


# Review 5: the worked example may not add facts its 'before' text never stated.
def test_worked_example_traces_added_facts_to_the_author():
    guide = (HERE / "references" / "writing-guide.md").read_text(encoding="utf-8")
    example = guide[guide.index("## Worked example"):]
    assert "The author's answers" in example
    for fact in ("Two outages", "network call"):
        assert example.count(fact) >= 2, fact


# Review 6: a figure keeps a unit only when the next word is a unit.
def test_figure_units_are_only_real_units():
    assert c.unsourced_figures("## Context\n\nIn 2025, the outage hit.\n", "In 2025 we had the outage") == []
    assert c.unsourced_figures("## Context\n\n40 of them broke.\n", "about 40 services") == []
    assert c.unsourced_figures("## Context\n\nIt took 2 hours.\n", "took 2h") == []
    assert c.unsourced_figures("## Context\n\nCache for 30 seconds.\n", "Cache 30s") == []
    assert [f.kind for f in c.unsourced_figures("## Context\n\nCache for 31 seconds.\n", "Cache 30s")] == \
        ["unsourced-figure"]


# Review 7: a headingless record is still checked.
def test_headingless_record_gets_hedge_and_name_checks(tmp_path):
    root = make(tmp_path, {"docs/adr/0001-x.md": "# Store state\n\nStatus: Proposed\n\n"
                                                 "We should store state in `src/ledgr.py`.\n"})
    found = kinds(c.check(root / "docs/adr/0001-x.md", root, root / "docs/adr"))
    assert "hedge" in found and "name-not-found" in found


# Re-graded minors: a crash on an absolute glob, and --json that does not parse.
def test_absolute_paths_are_not_names(tmp_path):
    for span in ("/etc/*", "/var/log/app/*.log", "/usr/bin/env"):
        assert not c.looks_like_name(span), span


def test_json_output_stays_parseable_when_identical(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("# 1. X\n\nStatus: Proposed\n\n## Decision\n\nOrders never call billing.\n", encoding="utf-8")
    rec = tmp_path / "0001-x.md"
    rec.write_text(draft.read_text(), encoding="utf-8")
    os.utime(draft, (1_000_000, 1_000_000))
    os.utime(rec, (2_000_000, 2_000_000))
    out = subprocess.run([sys.executable, c.__file__, str(rec), "--repo", str(tmp_path), "--against", str(draft),
                          "--json"], capture_output=True, text=True, check=False)
    json.loads(out.stdout)
    assert "identical" in out.stderr


# Grader r3: --confirmed names must be names the author actually gave.
def test_confirmed_names_must_be_in_the_authors_notes(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("# 1. X\n\nStatus: Proposed\n\n## Decision\n\nOrders never call billing.\n", encoding="utf-8")
    rec = tmp_path / "0001-x.md"
    rec.write_text(draft.read_text().replace("billing.", "billing via `billing/invoice.py`."), encoding="utf-8")
    os.utime(draft, (1_000_000, 1_000_000))
    os.utime(rec, (2_000_000, 2_000_000))
    notes = tmp_path / "notes.md"
    notes.write_text("orders never call billing", encoding="utf-8")
    out = subprocess.run([sys.executable, c.__file__, str(rec), "--repo", str(tmp_path), "--against", str(draft),
                          "--sources", str(notes), "--confirmed", "billing/invoice.py", "--json"],
                         capture_output=True, text=True, check=False)
    found = json.loads(out.stdout)
    assert "unconfirmed-name" in {f["kind"] for f in found}


# Grader r3: instruction-level gaps.
def test_draft_is_shown_before_any_write():
    assert "before the command that writes the record" in FLAT
    assert "Never say a draft was shown when it was not" in FLAT


def test_timestamps_are_never_adjusted_to_pass_a_check():
    assert "Never sleep, touch or copy files to get past a check" in FLAT


def test_reason_must_say_what_goes_wrong():
    assert "what goes wrong without the decision" in FLAT
