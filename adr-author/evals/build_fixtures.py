#!/usr/bin/env python3
"""Build the small, invented repositories the adr-author evals run against.

Each repository is a git repo with fixed authors and dates, so a rebuild gives identical commits
and a changed eval result is the skill, not the fixture. Nothing here comes from a real project.

Usage:
    build_fixtures.py TARGET_DIR
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

AUTHOR = "Fixture <fixture@example.invalid>"

NYGARD = {
    "services/orders/api.py": "from events.outbox import Outbox\n\n\ndef place_order(order):\n"
                              "    Outbox().publish('order.placed', order)\n",
    "services/billing/api.py": "def charge(invoice):\n    return invoice\n",
    "events/outbox.py": "class Outbox:\n    def publish(self, topic, payload):\n        return topic, payload\n",
    "docs/adr/0001-record-architecture-decisions.md":
        "# 1. Record architecture decisions\n\nDate: 2026-01-01\nStatus: Accepted\n\n## Context\n\n"
        "We need to remember why the system looks the way it does.\n\n## Decision\n\n"
        "We keep architecture decision records in `docs/adr/`, one file per decision.\n\n"
        "## Consequences\n\nEvery significant decision gets a numbered record.\n",
    "docs/adr/0002-orders-publish-events.md":
        "# 2. Orders publish domain events\n\nDate: 2026-01-02\nStatus: Accepted\n\n## Context\n\n"
        "Orders and billing failed together whenever billing was slow.\n\n## Decision\n\n"
        "The orders service publishes its events through `Outbox` in `events/outbox.py`.\n\n"
        "## Consequences\n\nOrders never calls `services/billing/api.py` from a request handler.\n",
}

MADR = {
    "app/db.py": "import sqlite3\n\n\ndef connect():\n    return sqlite3.connect(':memory:')\n",
    "app/search.py": "def search(term):\n    return [term]\n",
    "docs/decisions/0001-use-postgres.md":
        "---\nstatus: accepted\ndate: 2026-01-01\n---\n\n# Use Postgres for application data\n\n"
        "## Context and Problem Statement\n\nThe data is relational and needs transactions.\n\n"
        "## Considered Options\n\n* Postgres\n* A document store\n\n## Decision Outcome\n\n"
        "Chosen option: Postgres, through `connect` in `app/db.py`.\n",
    "docs/decisions/0002-search-in-the-database.md":
        "---\nstatus: accepted\ndate: 2026-01-02\n---\n\n# Search runs in the database\n\n"
        "## Context and Problem Statement\n\nA separate search cluster is more than the team can run.\n\n"
        "## Decision Outcome\n\nChosen option: full-text search in Postgres, behind `search` in "
        "`app/search.py`.\n",
}

TWO_SCHEMES = {
    "src/cache.py": "class Cache:\n    pass\n",
    "docs/adr/0001-cache-reads.md":
        "# 1. Cache reads\n\nStatus: Accepted\n\n## Decision\n\nReads go through `Cache` in `src/cache.py`.\n",
    "docs/adr/ADR-002-cache-expiry.md":
        "# ADR-002: Cache entries expire\n\nStatus: Accepted\n\n## Decision\n\n"
        "Entries in `Cache` expire after one hour.\n",
}

OVERTAKEN = {
    "ledger/api.py": "class Ledger:\n    def entries(self, account):\n        return []\n",
    "ledger/db.py": "def rows(table):\n    return []\n",
    "billing/invoice.py": "from ledger import db\n\n\ndef backfill_invoice_ids():\n"
                          "    return db.rows('ledger_entries')\n",
    "docs/adr/0001-record-architecture-decisions.md":
        "# 1. Record architecture decisions\n\nStatus: Accepted\n\n## Decision\n\n"
        "We keep architecture decision records in `docs/adr/`.\n",
    "docs/adr/0002-billing-is-a-separate-package.md":
        "# 2. Billing is a separate package\n\nStatus: Accepted\n\n## Decision\n\n"
        "Billing code lives under `billing/`.\n",
    "docs/adr/0003-billing-reads-the-ledger-through-its-api.md":
        "# 3. Billing reads the ledger through its API\n\nDate: 2026-01-03\nStatus: Accepted\n\n"
        "## Context\n\nTwo outages came from billing holding a ledger transaction open during a network "
        "call.\n\n## Decision\n\nCode under `billing/` reads ledger entries only through `Ledger` in "
        "`ledger/api.py`. It never imports `ledger.db`.\n\n## Consequences\n\nBilling cannot tune a "
        "ledger query by hand.\n",
}

REPOS = {"nygard": NYGARD, "madr": MADR, "two-schemes": TWO_SCHEMES, "overtaken": OVERTAKEN}


def _git(repo: Path, *args: str, date: str | None = None) -> None:
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
               GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                   cwd=repo, env=env, check=True, capture_output=True)


def _build_one(repo: Path, files: dict[str, str]) -> None:
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    code = {k: v for k, v in files.items() if not k.startswith("docs/")}
    docs = {k: v for k, v in files.items() if k.startswith("docs/")}
    for day, batch in enumerate((code, docs), 1):
        for rel, text in batch.items():
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "--allow-empty", "-m", f"fixture step {day}",
             date=f"2026-01-0{day}T12:00:00+00:00")


def build(target: Path) -> dict[str, Path]:
    """Build every fixture repository under target and return them by name."""
    target.mkdir(parents=True, exist_ok=True)
    built = {}
    for name, files in REPOS.items():
        _build_one(target / name, files)
        built[name] = target / name
    return built


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    for name, path in build(Path(args[0])).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
