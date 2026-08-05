#!/usr/bin/env python3
"""job-feeds — aggregate sanctioned public job feeds into one deduplicated
local database, match against your career lanes, and render an HTML report.

Every source is a documented JSON API or RSS feed the publisher offers.
This is not a scraper: it does not parse HTML, follow sitemaps, or work
around a 403. Sources that refuse an honestly-identified client are
dropped rather than circumvented.

stdout is data; stderr is human.
Exit: 0 clean, 1 one or more sources failed, 2 config or usage error.

Supported platforms: macOS and Linux. Standard library only — no jq, no
third-party packages, so `python3` is a supported runner alongside `uv`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "job-feeds"
CONFIG_DEFAULT = CONFIG_DIR / "config.json"
DB_DEFAULT = CONFIG_DIR / "jobs.db"
RATELIMIT_DEFAULT = CONFIG_DIR / "ratelimit.json"

STAMP = "%Y-%m-%dT%H:%M:%SZ"


class ConfigError(Exception):
    """Unusable input. Reported to stderr, exits 2."""


class RateLimiter:
    """Fetch-state for sources that document a polling limit.

    Stored OUTSIDE jobs.db deliberately: deleting or rebuilding the
    database must never make the tool forget it already polled. Jobicy
    documents 1 poll/hour fair use, and violating a documented limit risks
    losing the source permanently.

    Every ambiguous state fails CLOSED — missing file for a known source,
    unreadable file, unparseable timestamp. Refusing a poll costs a stale
    run; wrongly allowing one can cost the feed.
    """

    def __init__(self, path=RATELIMIT_DEFAULT):
        self.path = Path(path)

    def _load(self):
        """(state, problem). problem is None, 'missing' or 'unreadable'."""
        try:
            return json.loads(self.path.read_text(encoding="utf-8")), None
        except FileNotFoundError:
            return {}, "missing"
        except (json.JSONDecodeError, OSError, ValueError):
            return {}, "unreadable"

    def allows(self, source, now=None, seen=False):
        """(allowed, reason).

        `seen` means this source appears in the store, so it has been
        polled at least once — which makes an absent state file lost
        state rather than a first run.
        """
        if not source.rate_limit_seconds:
            return True, ""
        now = now or datetime.now(timezone.utc)
        state, problem = self._load()

        if problem == "unreadable":
            return False, f"rate-limit state unreadable at {self.path} — refusing to poll"
        if problem == "missing":
            if seen:
                return False, (f"no rate-limit state at {self.path} but {source.name} has "
                               f"been polled before — refusing to poll (failing closed)")
            return True, ""

        last = state.get(source.name)
        if not last:
            return True, ""
        try:
            when = datetime.strptime(last, STAMP).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return False, (f"unparseable last-poll time for {source.name} "
                           f"({last!r}) — refusing to poll")
        following = when + timedelta(seconds=source.rate_limit_seconds)
        if now < following:
            return False, f"next poll {following.strftime('%H:%M')} (documented fair use)"
        return True, ""

    def record(self, source, now=None):
        """No-op for sources with no declared limit, so a fresh install
        does not accumulate empty state files."""
        if not source.rate_limit_seconds:
            return
        now = now or datetime.now(timezone.utc)
        state, _ = self._load()
        state[source.name] = now.strftime(STAMP)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------
# Storage.
# --------------------------------------------------------------------------

import sqlite3  # noqa: E402

from sources import dedupe_key  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  dedupe_key TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT,
  remote INTEGER, posted_at TEXT, url TEXT, source TEXT, description TEXT,
  tags TEXT, salary TEXT, first_seen TEXT, last_seen TEXT, also_seen_on TEXT);
CREATE TABLE IF NOT EXISTS sources (
  name TEXT PRIMARY KEY, last_fetch TEXT, status TEXT, reason TEXT,
  row_count INTEGER, pages INTEGER);
CREATE INDEX IF NOT EXISTS jobs_posted_at ON jobs(posted_at);
"""


class Store:
    """SQLite-backed job store.

    SQLite is load-bearing rather than convenient. `first_seen` per job is
    the only way to answer "what is new since I last looked": the feeds
    return a rolling window with no stable notion of newness, so a flat
    file would make every re-fetch look like a fresh result set.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def upsert(self, jobs, now=None):
        """Insert unseen jobs, refresh last_seen on known ones. -> (new, seen).

        first_seen is never overwritten. When the same posting arrives from
        a second source its name is appended to also_seen_on rather than
        replacing the original, because the other listing may be the one
        worth applying through.
        """
        stamp = (now or datetime.now(timezone.utc)).strftime(STAMP)
        new = seen = 0
        for entry in jobs:
            key = dedupe_key(entry.get("company"), entry.get("title"), entry.get("location"))
            existing = self.conn.execute(
                "SELECT source, also_seen_on FROM jobs WHERE dedupe_key = ?",
                (key,)).fetchone()
            if existing:
                others = {s for s in (existing["also_seen_on"] or "").split(",") if s}
                if entry.get("source") and entry["source"] != existing["source"]:
                    others.add(entry["source"])
                self.conn.execute(
                    "UPDATE jobs SET last_seen = ?, also_seen_on = ? WHERE dedupe_key = ?",
                    (stamp, ",".join(sorted(others)), key))
                seen += 1
            else:
                self.conn.execute(
                    "INSERT INTO jobs (dedupe_key, title, company, location, remote,"
                    " posted_at, url, source, description, tags, salary, first_seen,"
                    " last_seen, also_seen_on) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'')",
                    (key, entry.get("title"), entry.get("company"), entry.get("location"),
                     None if entry.get("remote") is None else int(bool(entry["remote"])),
                     entry.get("posted_at"), entry.get("url"), entry.get("source"),
                     entry.get("description"), ",".join(entry.get("tags") or []),
                     entry.get("salary"), stamp, stamp))
                new += 1
        self.conn.commit()
        return new, seen

    def select(self, window_days, now=None, remote_only=False):
        """In-window plus undated rows, newest first, undated last.

        Undated rows are deliberately NOT excluded: python.org carries no
        dates at all, so a naive date filter would delete that entire
        source without saying so.
        """
        now = now or datetime.now(timezone.utc)
        cutoff = (now - timedelta(days=window_days)).strftime(STAMP)
        sql = "SELECT * FROM jobs WHERE (posted_at IS NULL OR posted_at >= ?)"
        params = [cutoff]
        if remote_only:
            sql += " AND remote = 1"
        # `posted_at IS NULL` first: measured redundant on SQLite, which
        # already sorts NULL last under DESC, so removing it changes nothing
        # here and no test can distinguish the two. Kept because it states
        # the intent explicitly and the default is not universal -- Postgres
        # sorts NULLS FIRST under DESC, which would silently float every
        # undated python.org row to the top of the report.
        sql += " ORDER BY posted_at IS NULL, posted_at DESC"
        return [dict(row) for row in self.conn.execute(sql, params)]

    def known_sources(self):
        return {row["name"] for row in self.conn.execute("SELECT name FROM sources")}

    def record_source(self, name, status, reason, row_count, pages, now=None):
        stamp = (now or datetime.now(timezone.utc)).strftime(STAMP)
        self.conn.execute(
            "INSERT INTO sources (name, last_fetch, status, reason, row_count, pages)"
            " VALUES (?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET"
            " last_fetch=excluded.last_fetch, status=excluded.status,"
            " reason=excluded.reason, row_count=excluded.row_count, pages=excluded.pages",
            (name, stamp, status, reason, row_count, pages))
        self.conn.commit()

    def source_states(self):
        return [dict(row) for row in
                self.conn.execute("SELECT * FROM sources ORDER BY name")]
