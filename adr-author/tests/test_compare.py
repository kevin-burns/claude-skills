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


def _git(repo, *args):
    import os
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@example.invalid")
    subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=env, check=True,
                   capture_output=True)


def _committed_record(tmp_path):
    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    rec = adr / "0001-x.md"
    rec.write_text("# 1. X\n\nStatus: Accepted\n\n## Context\n\nTwo outages.\n\n" + DRAFT, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "x")
    return rec


def _cli(*args):
    return subprocess.run([sys.executable, c.__file__, *map(str, args)], capture_output=True, text=True,
                          check=False)


def test_baseline_reads_committed_record(tmp_path):
    rec = _committed_record(tmp_path)
    rec.write_text(rec.read_text().replace("never calls", "may call"), encoding="utf-8")
    result = _cli(rec, "--repo", tmp_path, "--baseline", "--json")
    found = json.loads(result.stdout)
    changed = [f for f in found if f["kind"] == "claim-word-changed"]
    assert changed and "committed record" in changed[0]["message"]


def test_baseline_counts_committed_text_as_a_source(tmp_path):
    rec = _committed_record(tmp_path)
    notes = tmp_path / "notes.md"
    notes.write_text("batch jobs may read", encoding="utf-8")
    result = _cli(rec, "--repo", tmp_path, "--baseline", "--sources", notes, "--json")
    assert "unsourced-figure" not in {f["kind"] for f in json.loads(result.stdout)}


def test_baseline_on_untracked_record_exits_2(tmp_path):
    rec = _committed_record(tmp_path)
    new = rec.parent / "0002-y.md"
    new.write_text("# 2. Y\n\nStatus: Proposed\n", encoding="utf-8")
    result = _cli(new, "--repo", tmp_path, "--baseline")
    assert result.returncode == 2
    assert "--against" in result.stderr


def test_against_refuses_newer_draft(tmp_path):
    import os

    rec = tmp_path / "0001-x.md"
    rec.write_text("# 1. X\n\nStatus: Proposed\n\n" + DRAFT, encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text(rec.read_text(), encoding="utf-8")
    os.utime(rec, (1_000_000, 1_000_000))
    os.utime(draft, (2_000_000, 2_000_000))
    result = _cli(rec, "--repo", tmp_path, "--against", draft)
    assert result.returncode == 2
    assert "newer than the record" in result.stderr


def test_against_identical_says_so(tmp_path):
    import os

    draft = tmp_path / "draft.md"
    draft.write_text("# 1. X\n\nStatus: Proposed\n\n" + DRAFT.replace("`200ms`", "200 ms"), encoding="utf-8")
    rec = tmp_path / "0001-x.md"
    rec.write_text(draft.read_text(), encoding="utf-8")
    os.utime(draft, (1_000_000, 1_000_000))
    os.utime(rec, (2_000_000, 2_000_000))
    result = _cli(rec, "--repo", tmp_path, "--against", draft)
    assert "identical to the approved draft" in result.stdout
