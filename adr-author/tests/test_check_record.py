"""Tests for check_record.py: the self-check an author reads.

Each finding is something a person decides on, so the tests pin two things: the check finds
what it claims to (a hedge, a name the repo does not have, a broken supersede link), and it
does not cry wolf (a flag like `--force` is not a missing name; a hedge in Context is fine).
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_record as c

TOOL_WORDS = ("obligation", "anchor", "verdict")


def repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def record(text: str) -> str:
    return "# 2. Orders publish events\n\nStatus: Proposed\n\n" + text


def kinds(findings):
    return [f.kind for f in findings]


def run(tmp_path, files, rel="docs/adr/0002-x.md", **kw):
    root = repo(tmp_path, files)
    return c.check(root / rel, root, (root / rel).parent, **kw)


def test_hedge_in_decision_is_raised_as_question(tmp_path):
    found = run(tmp_path, {"docs/adr/0002-x.md": record("## Decision\n\nServices should prefer async.\n")})
    hedges = [f for f in found if f.kind == "hedge"]
    assert len(hedges) == 1
    assert "Services should prefer async." in hedges[0].message
    assert "?" in hedges[0].message


def test_hedge_in_context_is_ignored(tmp_path):
    text = record("## Context\n\nWe should probably fix this.\n\n## Decision\n\nOrders never call billing.\n")
    assert "hedge" not in kinds(run(tmp_path, {"docs/adr/0002-x.md": text}))


def test_missing_name_found(tmp_path):
    text = record("## Decision\n\nOrders publish through `events/outbox.py`.\n")
    found = run(tmp_path, {"docs/adr/0002-x.md": text})
    assert kinds(found) == ["name-not-found"]
    assert "events/outbox.py" in found[0].message


def test_intended_name_is_not_reported(tmp_path):
    text = record("## Decision\n\nOrders publish through `events/outbox.py`.\n")
    found = run(tmp_path, {"docs/adr/0002-x.md": text}, intended=frozenset({"events/outbox.py"}))
    assert "name-not-found" not in kinds(found)


def test_name_present_as_path_or_identifier(tmp_path):
    files = {
        "ledger/api.py": "class Ledger:\n    pass\n",
        "docs/adr/0002-x.md": record("## Decision\n\nBilling uses `Ledger` in `ledger/api.py`.\n"),
    }
    assert "name-not-found" not in kinds(run(tmp_path, files))


def test_name_only_in_the_adr_dir_does_not_count(tmp_path):
    files = {
        "docs/adr/0001-a.md": "# 1. A\n\nStatus: Accepted\n\nMentions OrderBus here.\n",
        "docs/adr/0002-x.md": record("## Decision\n\nOrders go through `OrderBus`.\n"),
    }
    assert "name-not-found" in kinds(run(tmp_path, files))


def test_non_names_are_not_looked_up():
    for span in ("true", "--force", "200ms", "GET", "5"):
        assert not c.looks_like_name(span), span
    for span in ("ledger/api.py", "Ledger", "ledger.db", "get_total", "billing::Invoice", "services/*/api"):
        assert c.looks_like_name(span), span


def test_search_skips_big_and_binary_files(tmp_path):
    root = repo(tmp_path, {})
    (root / "big.py").write_text("x = 1\n" * 200_000 + "OrderBus\n", encoding="utf-8")
    (root / "blob.bin").write_bytes(b"\xff\xfe" + b"OrderBus" + b"\x00" * 10)
    assert not c.name_exists("OrderBus", root, root / "docs" / "adr")


def test_search_works_without_git(tmp_path):
    root = repo(tmp_path, {"src/bus.py": "class OrderBus: ...\n", ".venv/lib/x.py": "OtherBus\n"})
    assert c.name_exists("OrderBus", root, root / "docs" / "adr")
    assert not c.name_exists("OtherBus", root, root / "docs" / "adr")


def test_no_status(tmp_path):
    text = "# 2. X\n\n## Decision\n\nOrders never call billing.\n"
    assert "no-status" in kinds(run(tmp_path, {"docs/adr/0002-x.md": text}))


def test_no_decision_note_for_paragraph_record(tmp_path):
    text = "# 2. Use Postgres\n\nStatus: Accepted\n\nWe use Postgres because the data is relational.\n"
    found = run(tmp_path, {"docs/adr/0002-x.md": text})
    assert kinds(found) == ["no-decision"]


def test_number_taken_and_not_next(tmp_path):
    base = {f"docs/adr/000{n}-a{n}.md": f"# {n}. A\n\nStatus: Accepted\n" for n in (1, 2, 3)}
    taken = dict(base, **{"docs/adr/0002-new.md": record("## Decision\n\nOrders never call billing.\n")})
    assert "number-taken" in kinds(run(tmp_path / "t", taken, rel="docs/adr/0002-new.md"))
    late = dict(base, **{"docs/adr/0005-new.md": "# 5. N\n\nStatus: Proposed\n\n## Decision\n\nNever X.\n"})
    assert "number-not-next" in kinds(run(tmp_path / "l", late, rel="docs/adr/0005-new.md"))


def test_supersede_link(tmp_path):
    new = "# 4. New\n\nStatus: Accepted\nSupersedes: ADR-1\n\n## Decision\n\nOrders never call billing.\n"
    stale = {"docs/adr/0001-a.md": "# 1. A\n\nStatus: Accepted\n", "docs/adr/0004-n.md": new}
    assert "supersede-link" in kinds(run(tmp_path / "s", stale, rel="docs/adr/0004-n.md"))
    fixed = dict(stale, **{"docs/adr/0001-a.md": "# 1. A\n\nStatus: Superseded by ADR-4\n"})
    assert "supersede-link" not in kinds(run(tmp_path / "f", fixed, rel="docs/adr/0004-n.md"))


def test_superseded_without_successor(tmp_path):
    text = "# 2. X\n\nStatus: Superseded\n\n## Decision\n\nOrders never call billing.\n"
    assert "supersede-link" in kinds(run(tmp_path, {"docs/adr/0002-x.md": text}))


def test_decision_language_in_options(tmp_path):
    text = record("## Considered Options\n\nWe will use Kafka.\n\n## Decision\n\nOrders never call billing.\n")
    assert "decision-outside-decision" in kinds(run(tmp_path, {"docs/adr/0002-x.md": text}))


def test_scheme_conflict(tmp_path):
    files = {
        "docs/adr/0001-a.md": "# 1. A\n\nStatus: Accepted\n",
        "docs/adr/ADR-002-x.md": record("## Decision\n\nOrders never call billing.\n"),
    }
    assert "scheme-conflict" in kinds(run(tmp_path, files, rel="docs/adr/ADR-002-x.md"))


def test_messages_use_no_tool_vocabulary(tmp_path):
    text = (
        "# 2. X\n\nStatus: Superseded\nSupersedes: ADR-9\n\n## Considered Options\n\nWe will use Kafka.\n\n"
        "## Decision\n\nServices should use `events/outbox.py`.\n"
    )
    files = {"docs/adr/0001-a.md": "# 1. A\n", "docs/adr/ADR-002-x.md": text}
    found = run(tmp_path, files, rel="docs/adr/ADR-002-x.md")
    assert len(found) >= 5
    for f in found:
        assert not any(word in f.message.lower() for word in TOOL_WORDS), f.message


def test_cli_exit_codes_and_json(tmp_path):
    script = Path(c.__file__)
    clean = repo(tmp_path / "c", {"docs/adr/0002-x.md": record("## Decision\n\nOrders never call billing.\n")})
    dirty = repo(tmp_path / "d", {"docs/adr/0002-x.md": record("## Decision\n\nWe should use async.\n")})

    def cli(root, *args):
        return subprocess.run([sys.executable, str(script), str(root / "docs/adr/0002-x.md"),
                               "--repo", str(root), *args], capture_output=True, text=True, check=False)

    assert cli(clean).returncode == 0
    result = cli(dirty, "--json")
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload[0]["kind"] == "hedge"
    assert set(payload[0]) == {"kind", "line", "message"}
    missing = subprocess.run([sys.executable, str(script), str(tmp_path / "nope.md")],
                             capture_output=True, text=True, check=False)
    assert missing.returncode == 2
