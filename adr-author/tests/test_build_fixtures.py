"""Tests for the eval fixture builder.

The fixtures are what every eval case runs against, so two properties matter: they rebuild
identically (or a changed result could be the fixture, not the skill), and each one really has
the shape its case relies on (the overtaken repo must actually contradict its record).
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "evals"))
sys.path.insert(0, str(HERE / "scripts"))

import build_fixtures as b
import records


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def test_builds_four_repos(tmp_path):
    repos = b.build(tmp_path)
    assert set(repos) == {"nygard", "madr", "two-schemes", "overtaken"}
    for path in repos.values():
        assert (path / ".git").is_dir()


def test_commit_dates_are_fixed(tmp_path):
    repos = b.build(tmp_path)
    dates = git(repos["nygard"], "log", "--format=%aI").splitlines()
    assert dates and all(d.startswith("2026-01-0") for d in dates)


def test_rebuild_is_identical(tmp_path):
    first = b.build(tmp_path / "one")
    second = b.build(tmp_path / "two")
    for key in first:
        assert git(first[key], "rev-parse", "HEAD") == git(second[key], "rev-parse", "HEAD"), key


def test_fixture_records_parse(tmp_path):
    repos = b.build(tmp_path)
    assert [r.number for r in records.load_records(repos["nygard"] / "docs" / "adr")] == [1, 2]
    madr = records.load_records(repos["madr"] / "docs" / "decisions")
    assert all(r.status == "Accepted" for r in madr)
    schemes = {records.filename_scheme(r.path) for r in records.load_records(repos["two-schemes"] / "docs" / "adr")}
    assert schemes == {"NNNN-slug", "ADR-NNN-slug"}


def test_overtaken_repo_contradicts_its_record(tmp_path):
    repo = b.build(tmp_path)["overtaken"]
    record = (repo / "docs" / "adr" / "0003-billing-reads-the-ledger-through-its-api.md").read_text()
    assert "never imports `ledger.db`" in record
    assert "from ledger import db" in (repo / "billing" / "invoice.py").read_text()
