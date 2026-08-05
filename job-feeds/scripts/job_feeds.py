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
import threading
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
        # record() is a read-modify-write on one file, called from the
        # fetch worker threads. Without this, two limited sources finishing
        # together lose one of the two poll times, and the lost source
        # becomes pollable again inside its own window -- silently.
        self._lock = threading.Lock()

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
        with self._lock:
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


# --------------------------------------------------------------------------
# Fetch layer -- the only code in this project that touches HTTP.
#
# ThreadPoolExecutor, not asyncio. Measured across all eight live feeds on
# 2026-08-05: threads complete in 0.91s, exactly equal to the slowest single
# source, with no measurable overhead. That is the theoretical floor, so an
# event loop cannot beat it, and staying stdlib preserves the python3
# fallback CONTRIBUTING.md prescribes for a publicly installed skill.
#
# fetch_all is one isolated seam: it returns plain job dicts, so nothing
# downstream knows HTTP happened. If per-job detail fetching ever lands
# (hundreds of requests, where an event loop does win), this is the only
# function that changes.
# --------------------------------------------------------------------------

import urllib.error  # noqa: E402
import urllib.request  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402
from collections import namedtuple  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

from sources import SOURCES, to_utc, validate_schema  # noqa: E402

FetchResult = namedtuple("FetchResult", "name status reason jobs pages etag")

USER_AGENT = ("job-feeds/0.1 (personal job-search aggregator; "
              "+https://github.com/kevin-burns/claude-skills)")

RSS_SOURCES = ("wwr", "pythonorg")


def http_open(url, headers):
    """(status, body, response_headers).

    304 is returned rather than raised: an unchanged resource is a normal,
    successful outcome of a conditional request, not an error.
    """
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.getcode(), response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return 304, b"", dict(exc.headers or {})
        raise


def _parse(source, body):
    return ET.fromstring(body) if source.name in RSS_SOURCES else json.loads(body)


def _oldest_on_page(rows):
    """Oldest UTC stamp on this page, or None when the page carries no
    usable dates (an RSS page, or one whose rows are all undated)."""
    stamps = [to_utc(r.get("created_at")) for r in rows if isinstance(r, dict)]
    stamps = [s for s in stamps if s]
    return min(stamps) if stamps else None


def _fetch_one(source, opener, limiter, now, max_pages, window_days,
               seen_before=False, stored_reason=""):
    """Fetch one source. Takes plain values, never a Store.

    sqlite3 connections are bound to the thread that created them, so a
    worker touching the store raises ProgrammingError. Reading what this
    needs once, on the main thread, is both the fix and the better shape:
    the fetch layer now has no storage dependency at all.
    """
    allowed, refusal = limiter.allows(source, now, seen=seen_before)
    if not allowed:
        return FetchResult(source.name, "throttled", refusal, [], 0, None)

    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    if stored_reason.startswith("etag:"):
        headers["If-None-Match"] = stored_reason[len("etag:"):]

    cutoff = (now - timedelta(days=window_days)).strftime(STAMP)
    url, pages, raw_rows, etag = source.url, 0, [], None

    try:
        while url and pages < max_pages:
            status, body, response_headers = opener(url, headers)
            if status == 304:
                limiter.record(source, now)
                return FetchResult(source.name, "unchanged",
                                   "not modified since last fetch", [], pages,
                                   headers.get("If-None-Match"))
            payload = _parse(source, body)
            page_rows = list(source.rows(payload))
            raw_rows.extend(page_rows)
            pages += 1
            etag = response_headers.get("ETag") or etag
            # Only valid for page 1 -- page 2 is a different resource, and
            # reusing the validator would 304 it and truncate the crawl.
            headers.pop("If-None-Match", None)

            url = None
            if source.paginates and isinstance(payload, dict):
                url = (payload.get("links") or {}).get("next")
                oldest = _oldest_on_page(page_rows)
                if url and oldest and oldest < cutoff:
                    url = None   # everything below here is outside the window
    except (OSError, ValueError, ET.ParseError) as exc:
        limiter.record(source, now)
        return FetchResult(source.name, "failed", f"{type(exc).__name__}: {exc}",
                           [], pages, None)

    limiter.record(source, now)
    accepted, drift = validate_schema(source, raw_rows)
    if drift:
        return FetchResult(source.name, "degraded", drift, [], pages, etag)

    jobs = []
    for raw in accepted:
        entry = source.normalise(raw)
        if entry["title"] and entry["url"]:
            entry["source"] = source.name
            jobs.append(entry)
    return FetchResult(source.name, "ok", "", jobs, pages, etag)


def fetch_all(sources, opener=http_open, limiter=None, store=None, now=None,
              max_pages=50, window_days=30):
    """Fetch every source concurrently, isolating failures per source.

    A source that raises never propagates: it becomes a `failed` result so
    the seven feeds that answered still reach the store.
    """
    now = now or datetime.now(timezone.utc)
    limiter = limiter if limiter is not None else RateLimiter()
    store = store if store is not None else Store(DB_DEFAULT)
    sources = list(sources)
    if not sources:
        return []
    # Read everything the workers need HERE, on the main thread -- sqlite3
    # connections cannot cross threads.
    known = store.known_sources()
    reasons = {state["name"]: (state["reason"] or "") for state in store.source_states()}
    with ThreadPoolExecutor(max_workers=min(8, len(sources))) as pool:
        futures = [pool.submit(_fetch_one, s, opener, limiter, now, max_pages,
                               window_days, s.name in known, reasons.get(s.name, ""))
                   for s in sources]
        return [f.result() for f in futures]
