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

import contextlib
import json
import os
import re
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "job-feeds"
CONFIG_DEFAULT = CONFIG_DIR / "config.json"
DB_DEFAULT = CONFIG_DIR / "jobs.db"
RATELIMIT_DEFAULT = CONFIG_DIR / "ratelimit.json"


def ratelimit_path_for(db_path):
    """Rate-limit state lives BESIDE the database it accompanies.

    Scoping it to --db is what makes a scratch or test run isolated;
    a fixed default path meant every such run read and wrote the
    operator's real state. It is still a separate FILE, so the
    original property holds -- deleting jobs.db must not make the
    tool forget it already polled a source.
    """
    return Path(db_path).parent / "ratelimit.json"

STAMP = "%Y-%m-%dT%H:%M:%SZ"

# Printed by `doctor` when no config exists. Deliberately ONE lane with a
# deliberately narrow regex: the docs' own position is that lanes are what
# people get wrong, and a starter matching half the corpus would teach the
# opposite lesson. It is a complete, valid config -- a fresh install must
# have a path that works without Claude, because config.example.json
# encodes one person's career and is the wrong thing to copy unedited.
# Kept flush left so the heredoc in the help text pastes verbatim.
STARTER_CONFIG = """\
{
  "defaults": {
    "window": 14,
    "exclude_company": [],
    "exclude_title": []
  },
  "lanes": [
    {
      "name": "platform",
      "label": "Platform",
      "match": "\\\\b(platform|infrastructure|devops|sre)\\\\b",
      "match_in": "title"
    }
  ]
}"""


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
        now = now or datetime.now(UTC)
        state, problem = self._load()

        if problem == "unreadable":
            return False, f"rate-limit state unreadable at {self.path} — refusing to poll"
        if problem == "missing":
            if seen and source.rate_limit_seconds:
                return False, (f"no rate-limit state at {self.path} but {source.name} has "
                               f"been polled before — refusing to poll (failing closed)")
            return True, ""

        entry = state.get(source.name)
        if not entry:
            return True, ""
        when, backoff, _ = self._entry(entry)
        if when is None:
            return False, (f"unparseable last-poll time for {source.name} "
                           f"({entry!r}) — refusing to poll")

        # A 429/503 backoff applies even to a source with no standing limit
        # -- those are precisely the ones that get throttled, and a backoff
        # nothing reads just walks back into the same wall every run.
        if backoff:
            until = when + timedelta(seconds=backoff)
            if now < until:
                return False, f"backing off until {until.strftime('%H:%M')} (server asked)"
            return True, ""

        if not source.rate_limit_seconds:
            return True, ""
        following = when + timedelta(seconds=source.rate_limit_seconds)
        if now < following:
            return False, f"next poll {following.strftime('%H:%M')} (documented fair use)"
        return True, ""

    @staticmethod
    def _entry(value):
        """(when, backoff_seconds, strikes). Accepts the legacy flat timestamp
        and the {'at': ..., 'backoff': N} form as well as the current
        {'at': ..., 'backoff': N, 'strikes': K}, because a state file written
        by an older version must not crash or silently unblock everything.
        A missing 'strikes' reads as 0, so an upgrade starts the escalation
        from the bottom rather than inventing a history."""
        if isinstance(value, str):
            raw, backoff, strikes = value, 0, 0
        else:
            value = value or {}
            raw = value.get("at")
            backoff = value.get("backoff") or 0
            strikes = value.get("strikes") or 0
        try:
            return (datetime.strptime(raw, STAMP).replace(tzinfo=UTC),
                    int(backoff), int(strikes))
        except (TypeError, ValueError):
            return None, 0, 0

    def _strikes(self, source):
        state, problem = self._load()
        if problem:
            return 0
        return self._entry(state.get(source.name))[2]

    def next_backoff(self, source, retry_after=None, now=None):
        """Seconds to wait after being throttled, WITHOUT recording anything.

        Separated from record() so the escalation is testable on its own and
        so a caller can see what it is about to apply.

        A server-supplied Retry-After always wins: it is the source telling
        us its actual terms, and second-guessing that with our own curve
        would be the opposite of the politeness this exists for. It is still
        clamped, because a hostile or broken value should not park a source
        for a year.

        Absent that, escalate on CONSECUTIVE throttles: 1h, 2h, 4h... up to a
        day. A flat hour means a persistently unhappy source gets poked once
        an hour forever, which is politer than retrying immediately and less
        polite than it should be.
        """
        try:
            return max(60, min(int(retry_after), BACKOFF_CEILING_SECONDS))
        except (TypeError, ValueError):
            pass  # absent, or a date-form Retry-After we do not parse
        strikes = self._strikes(source)
        return min(DEFAULT_BACKOFF_SECONDS * (2 ** strikes), BACKOFF_CEILING_SECONDS)

    def record(self, source, now=None, force=False, backoff_seconds=0,
               healthy=False):
        """No-op for sources with no declared limit, so a fresh install
        does not accumulate empty state files.

        `force` overrides that for backpressure: a 429 from a source with
        no standing limit still has to be remembered, or the next run
        retries immediately.
        """
        if not source.rate_limit_seconds and not force:  # noqa: SIM102 - the comment below explains the inner check
            # ...but a recovered source must still have its strike count
            # cleared, or escalation ratchets up forever for the seven
            # sources that declare no standing limit. Caught by test:
            # two throttles then a clean fetch left strikes at 2.
            if not (healthy and self._strikes(source)):
                return
        now = now or datetime.now(UTC)
        with self._lock:
            state, _ = self._load()
            stamp = now.strftime(STAMP)
            previous = self._entry(state.get(source.name))[2]
            if backoff_seconds:
                # A throttle. Count it, so the NEXT one waits longer.
                state[source.name] = {"at": stamp, "backoff": int(backoff_seconds),
                                      "strikes": previous + 1}
            elif healthy:
                # A clean poll clears the history. Without this, one bad
                # afternoon would keep escalating a source for days.
                if source.rate_limit_seconds:
                    state[source.name] = stamp   # standing limit: remember the poll
                else:
                    # Nothing left worth remembering, and dropping the key
                    # returns the file to the shape a fresh install has.
                    state.pop(source.name, None)
            else:
                # Neither throttled nor confirmed healthy -- a network error,
                # say. Record the poll but KEEP the strike count: a socket
                # timeout is not evidence the source is well again.
                state[source.name] = ({"at": stamp, "backoff": 0,
                                       "strikes": previous} if previous else stamp)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write_atomic(json.dumps(state, indent=1))

    def _write_atomic(self, text):
        """Temp file in the same directory, then os.replace.

        write_text() opens with 'w', which TRUNCATES before writing. An
        interrupted write, or a second jfeeds process, leaves a truncated
        file -- and the limiter then classifies it as unreadable and refuses
        every poll. That fails in the safe direction, but it also discards
        any recorded backoff and looks identical to a real problem.

        os.replace is atomic on POSIX when source and destination are on the
        same filesystem, hence the temp file sitting beside the target
        rather than in /tmp. Same temp->rename pattern the azadvertizer
        skill uses for its cache.
        """
        tmp = self.path.with_name(self.path.name + f".{os.getpid()}.tmp")
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, self.path)
        finally:
            # A crash between write and replace must not litter the config
            # directory with fragments that look like real state.
            with contextlib.suppress(FileNotFoundError):
                tmp.unlink()


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
  row_count INTEGER, pages INTEGER, etag TEXT, etag_url TEXT);
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
        self._migrate()

    def _migrate(self):
        """CREATE TABLE IF NOT EXISTS silently does nothing to a table that
        already exists, so a new column has to be added explicitly or every
        store built before this version breaks on the first query.

        The etag used to live inside `reason` with an 'etag:' prefix. Those
        are cleared rather than migrated: the validator is only safe to
        replay against the URL it came from, and the old form never recorded
        one. Costs a single full re-fetch per source, once.
        """
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(sources)")}
        for column in ("etag", "etag_url"):
            if column not in columns:
                self.conn.execute(f"ALTER TABLE sources ADD COLUMN {column} TEXT")
        self.conn.execute("UPDATE sources SET reason='' WHERE reason LIKE 'etag:%'")
        self.conn.commit()

    def upsert(self, jobs, now=None):
        """Insert unseen jobs, refresh last_seen on known ones. -> (new, seen).

        first_seen is never overwritten. When the same posting arrives from
        a second source its name is appended to also_seen_on rather than
        replacing the original, because the other listing may be the one
        worth applying through.
        """
        stamp = (now or datetime.now(UTC)).strftime(STAMP)
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
        now = now or datetime.now(UTC)
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

    def record_source(self, name, status, reason, row_count, pages, now=None,
                      etag=None, etag_url=None):
        """COALESCE on the etag is the whole point: a fetch that returns no
        validator -- a 429, a 500, a socket error, a schema drift -- must
        LEAVE the stored one alone. It used to share the `reason` column, so
        any failure overwrote it with prose and the next run re-downloaded
        everything. Worst exactly when it hurts most, since a hiccup is when
        a conditional request is most valuable.

        etag_url is stored alongside so the validator can be checked against
        the URL it came from. Replaying one against a changed URL can return
        304 with zero rows while `jfeeds sources` reports `unchanged`.
        """
        stamp = (now or datetime.now(UTC)).strftime(STAMP)
        self.conn.execute(
            "INSERT INTO sources"
            " (name, last_fetch, status, reason, row_count, pages, etag, etag_url)"
            " VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET"
            " last_fetch=excluded.last_fetch, status=excluded.status,"
            " reason=excluded.reason, row_count=excluded.row_count,"
            " pages=excluded.pages,"
            " etag=COALESCE(excluded.etag, sources.etag),"
            " etag_url=COALESCE(excluded.etag_url, sources.etag_url)",
            (name, stamp, status, reason, row_count, pages, etag, etag_url))
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

# Identifies the TOOL, never its author.
#
# This skill is installed and run by other people. A User-Agent naming the
# author would attribute every downstream user's traffic to them: an
# operator investigating abuse would find the wrong person, and the
# author's account name would be broadcast from machines they have never
# touched. That is a real leak, not a stylistic preference.
#
# Anonymity is not the goal -- unattributability is. An operator can still
# see exactly what is calling them, and any user who wants to be reachable
# can set `defaults.contact` in their own config.
DEFAULT_USER_AGENT = "job-feeds/0.1 (job-search feed aggregator)"

_HEADER_UNSAFE = re.compile(r"[\r\n\x00-\x1f\x7f]")


def build_user_agent(contact=None):
    """DEFAULT_USER_AGENT, plus an operator-supplied contact if configured.

    The contact is sanitised because a config file is a file: it gets
    copied between machines and pasted from the internet, and a CRLF in a
    header value is header injection.
    """
    if not isinstance(contact, str) or not contact.strip():
        return DEFAULT_USER_AGENT
    cleaned = _HEADER_UNSAFE.sub(" ", contact).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)[:120]
    if not cleaned:
        return DEFAULT_USER_AGENT
    return f"{DEFAULT_USER_AGENT[:-1]}; +{cleaned})"

RSS_SOURCES = ("wwr", "pythonorg")

# Applied when a 429/503 arrives without a parseable Retry-After.
DEFAULT_BACKOFF_SECONDS = 3600
# A day. Also the clamp on a server-supplied Retry-After: a hostile or
# broken value must not park a source for a year.
BACKOFF_CEILING_SECONDS = 86400

# Stop paginating while this much of a published budget is left.
# Arbeitnow advertises x-ratelimit-limit: 50 and we used to walk up
# to 50 pages -- its entire allowance -- which is what produced the
# 429 during development. Leaving a reserve means the next run, and
# anything else sharing the IP, still has requests to spend.
RATELIMIT_RESERVE = 5

# Pages to walk before giving up on a paginating source.
#
# This was 50, which is Arbeitnow's ENTIRE advertised budget
# (x-ratelimit-limit: 50) -- one deep crawl could spend the whole
# allowance, and repeatedly did, producing the 429s seen during
# development. Measured 2026-08-05: page 10 reaches ~1.7 days back, so 10
# covers a daily delta comfortably and the older-than-cutoff rule usually
# stops sooner. Pass --max-pages for a deliberate first crawl.
#
# Note the published budget header cannot be relied on to stop us: every
# Arbeitnow response is a Cloudflare cache HIT, so x-ratelimit-remaining
# reports the CACHED value (a constant 49) rather than our real
# consumption. _budget_remaining still honours it where a source reports
# it truthfully, but the page cap is what actually protects the budget.
DEFAULT_MAX_PAGES = 10

# Pause between sequential pages of ONE source.
#
# Capping pages proved insufficient: ten uncached requests in ~1s
# succeeded from a rested budget, but a second run moments later was
# refused. Arbeitnow's limiter is burst-sensitive. A second between pages
# costs ~9s on a job run twice a day, and is the difference between a
# welcome client and a blocked one.
PAGE_DELAY_SECONDS = 1.0


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
        # 304 and the backpressure codes are outcomes to act on, not errors
        # to raise: 304 means unchanged, 429/503 mean "slow down". Raising
        # them would report a source as broken and invite an immediate
        # retry, which is exactly how a soft limit becomes a hard block.
        if exc.code in (304, 429, 503):
            return exc.code, b"", dict(exc.headers or {})
        raise


def _parse(source, body):
    return ET.fromstring(body) if source.name in RSS_SOURCES else json.loads(body)


def _budget_remaining(headers):
    """Requests left, from whichever budget header the source publishes.

    Only Arbeitnow ships one today. Absence must never read as exhaustion,
    or the seven sources without it would be truncated to a single page.
    """
    for name in ("X-RateLimit-Remaining", "x-ratelimit-remaining", "RateLimit-Remaining"):
        raw = headers.get(name)
        if raw is None:
            continue
        try:
            return int(str(raw).strip())
        except (TypeError, ValueError):
            return None
    return None


def _oldest_on_page(rows):
    """Oldest UTC stamp on this page, or None when the page carries no
    usable dates (an RSS page, or one whose rows are all undated)."""
    stamps = [to_utc(r.get("created_at")) for r in rows if isinstance(r, dict)]
    stamps = [s for s in stamps if s]
    return min(stamps) if stamps else None


def _fetch_one(source, opener, limiter, now, max_pages, window_days,
               seen_before=False, stored_etag="", user_agent=DEFAULT_USER_AGENT,
               sleep=time.sleep):
    """Fetch one source. Takes plain values, never a Store.

    sqlite3 connections are bound to the thread that created them, so a
    worker touching the store raises ProgrammingError. Reading what this
    needs once, on the main thread, is both the fix and the better shape:
    the fetch layer now has no storage dependency at all.
    """
    allowed, refusal = limiter.allows(source, now, seen=seen_before)
    if not allowed:
        return FetchResult(source.name, "throttled", refusal, [], 0, None)

    headers = {"User-Agent": user_agent, "Accept-Encoding": "identity"}
    if stored_etag:
        # Already checked against the URL it came from -- see fetch_all.
        headers["If-None-Match"] = stored_etag

    cutoff = (now - timedelta(days=window_days)).strftime(STAMP)
    url, pages, raw_rows, etag = source.url, 0, [], None
    budget_note = ""

    try:
        while url and pages < max_pages:
            if pages:
                sleep(PAGE_DELAY_SECONDS)   # never before the first request
            status, body, response_headers = opener(url, headers)
            if status == 304:
                limiter.record(source, now, healthy=True)
                return FetchResult(source.name, "unchanged",
                                   "not modified since last fetch", [], pages,
                                   headers.get("If-None-Match"))
            if status in (429, 503):
                # Record the poll so the next run waits instead of walking
                # straight back into the same wall. Observed live on
                # 2026-08-05 when this project's own pagination probing
                # tripped Arbeitnow's limiter.
                retry_after = response_headers.get("Retry-After")
                # The limiter owns the curve: Retry-After wins if present,
                # otherwise 1h doubling per CONSECUTIVE throttle up to a day.
                backoff = limiter.next_backoff(source, retry_after)
                limiter.record(source, now, force=True, backoff_seconds=backoff)
                detail = f", Retry-After {retry_after}s" if retry_after else ""
                return FetchResult(source.name, "throttled",
                                   f"HTTP {status} — backing off{detail}",
                                   [], pages, None)
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
                remaining = _budget_remaining(response_headers)
                if url and remaining is not None and remaining <= RATELIMIT_RESERVE:
                    # The server told us how much is left. Believe it, and
                    # say so -- a silently truncated crawl is indistinguishable
                    # from a board that simply ran out of jobs.
                    url = None
                    budget_note = (f"stopped early: {remaining} of the source's "
                                   f"published request budget left")
    except (OSError, ValueError, ET.ParseError) as exc:
        # healthy stays False: a socket timeout says nothing about whether
        # the source has stopped throttling us, so the strike count holds.
        limiter.record(source, now)
        return FetchResult(source.name, "failed", f"{type(exc).__name__}: {exc}",
                           [], pages, None)

    limiter.record(source, now, healthy=True)
    accepted, drift = validate_schema(source, raw_rows)
    if drift:
        return FetchResult(source.name, "degraded", drift, [], pages, etag)

    jobs = []
    for raw in accepted:
        entry = source.normalise(raw)
        if entry["title"] and entry["url"]:
            entry["source"] = source.name
            jobs.append(entry)
    return FetchResult(source.name, "ok", budget_note, jobs, pages, etag)


def fetch_all(sources, opener=http_open, limiter=None, store=None, now=None,
              max_pages=10, window_days=30, user_agent=DEFAULT_USER_AGENT,
              sleep=time.sleep):
    """Fetch every source concurrently, isolating failures per source.

    A source that raises never propagates: it becomes a `failed` result so
    the seven feeds that answered still reach the store.
    """
    now = now or datetime.now(UTC)
    limiter = limiter if limiter is not None else RateLimiter()
    store = store if store is not None else Store(DB_DEFAULT)
    sources = list(sources)
    if not sources:
        return []
    # Read everything the workers need HERE, on the main thread -- sqlite3
    # connections cannot cross threads.
    known = store.known_sources()
    stored = {state["name"]: state for state in store.source_states()}

    def validator_for(source):
        """The etag ONLY if it was captured from this exact URL.

        An etag is a validator for one resource. Replaying it against a
        changed URL can yield 304 with zero rows while `jfeeds sources`
        cheerfully reports `unchanged` -- silent, and it looks like it
        worked. So a URL change simply drops the validator and re-fetches.
        """
        state = stored.get(source.name) or {}
        etag = state.get("etag") or ""
        return etag if etag and state.get("etag_url") == source.url else ""

    with ThreadPoolExecutor(max_workers=min(8, len(sources))) as pool:
        futures = [pool.submit(_fetch_one, s, opener, limiter, now, max_pages,
                               window_days, s.name in known, validator_for(s),
                               user_agent, sleep)
                   for s in sources]
        return [f.result() for f in futures]


# --------------------------------------------------------------------------
# Config, matching, and the CLI.
# --------------------------------------------------------------------------

import argparse  # noqa: E402
import sys  # noqa: E402

Lane = namedtuple("Lane", "name label pattern title_only")
Config = namedtuple(
    "Config",
    "lanes highlight exclude_companies exclude_titles window sources contact "
    "report_dir")


KNOWN_TOP_LEVEL = {"defaults", "lanes", "highlight", "sources"}
KNOWN_DEFAULTS = {"window", "contact", "exclude_company", "exclude_title",
                  "report_dir"}
KNOWN_LANE = {"name", "label", "match", "match_in"}


def unknown_keys(path):
    """Keys the loader does not read, so `doctor` can say so.

    Silently ignoring them is how a documented-but-unimplemented option
    survives: SKILL.md once told the agent to write `location_filter`,
    nothing read it, and doctor confirmed the file was fine. The user's
    primary constraint was dropped without a word.

    Reported, never fatal — an unknown key may be a comment or a field
    from a newer version, and refusing to run would be worse than saying
    so. Returns a sorted list of "where: key" strings.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []          # a broken config is load_config's problem, not this one
    if not isinstance(raw, dict):
        return []

    found = [f"top level: {k}" for k in raw if k not in KNOWN_TOP_LEVEL]
    defaults = raw.get("defaults")
    if isinstance(defaults, dict):
        found += [f"defaults: {k}" for k in defaults if k not in KNOWN_DEFAULTS]
    for index, lane in enumerate(raw.get("lanes") or []):
        if isinstance(lane, dict):
            found += [f"lanes[{index}]: {k}" for k in lane if k not in KNOWN_LANE]
    return sorted(found)


def resolve_report_path(out, report_dir):
    """Where `--out` actually lands.

    An ABSOLUTE --out always wins: someone who typed a full path meant it,
    and silently relocating it would be worse than any tidiness gained.
    The `is_absolute()` test is deliberately explicit rather than
    load-bearing -- `Path("/reports") / Path("/tmp/x.html")` already yields
    `/tmp/x.html`, because joining an absolute right-hand side discards the
    left. Stating the rule beats relying on that, but do not mistake the
    line for the thing that enforces it: deleting it changes no behaviour,
    which is exactly why the guard for it mutates the join instead.
    A bare or relative name resolves against `defaults.report_dir` when one
    is configured, and against the working directory otherwise -- which is
    the behaviour every existing install already has, so setting nothing
    changes nothing.

    This exists because both job-search tools defaulted to "wherever you
    happened to be", which is not a location so much as an accident: one
    run put its report in a project folder and the next in $HOME.
    """
    target = Path(out).expanduser()
    if target.is_absolute() or not report_dir:
        return target
    return Path(report_dir).expanduser() / target


def load_config(path):
    """Parse and hard-validate the config. Raises ConfigError.

    Errors name the offending lane, because a bare `re.error: missing )`
    gives no clue which of eight lanes to fix.
    """
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        raise ConfigError(f"config not readable: {path}") from None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"config is not valid JSON: {path} ({exc})") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"config must be a JSON object: {path}")

    defaults = raw.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise ConfigError(f"config 'defaults' must be a JSON object: {path}")
    entries = raw.get("lanes") or []
    if not entries:
        raise ConfigError(f"config has no lanes: {path}")

    lanes = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ConfigError(f"lane[{index}] must be a JSON object")
        missing = [f for f in ("name", "label", "match")
                   if not isinstance(entry.get(f), str) or not entry[f].strip()]
        if missing:
            raise ConfigError(
                f"lane[{index}] missing or empty field(s): {', '.join(missing)}")
        try:
            pattern = re.compile(entry["match"], re.IGNORECASE)
        except re.error as exc:
            raise ConfigError(
                f"lane '{entry['name']}' has an invalid match regex: {exc}") from None
        scope = entry.get("match_in", "title+description")
        if scope not in ("title", "title+description"):
            # Falling back silently would make a typo look like a lane that
            # simply stopped matching -- the hardest kind of bug to notice.
            raise ConfigError(
                f"lane '{entry['name']}' has an unknown match_in {scope!r} "
                f"(expected 'title' or 'title+description')")
        lanes.append(Lane(entry["name"], entry["label"], pattern, scope == "title"))

    names = [lane.name for lane in lanes]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ConfigError(f"duplicate lane name(s): {', '.join(duplicates)}")

    try:
        window = int(defaults.get("window", 14))
    except (TypeError, ValueError):
        raise ConfigError(f"'window' must be a whole number of days: {path}") from None

    return Config(
        lanes=tuple(lanes),
        highlight=tuple(h.lower() for h in (raw.get("highlight") or [])
                        if isinstance(h, str)),
        exclude_companies=tuple(c.lower() for c in defaults.get("exclude_company", [])
                                if isinstance(c, str)),
        exclude_titles=tuple(t.lower() for t in defaults.get("exclude_title", [])
                             if isinstance(t, str)),
        window=window,
        sources=raw.get("sources") or {},
        contact=defaults.get("contact"),
        report_dir=defaults.get("report_dir"))


def _haystack(job, title_only=False):
    parts = (job.get("title"),) if title_only else (job.get("title"), job.get("description"))
    return " ".join(p for p in parts if isinstance(p, str)).lower()


def lanes_for(job, config):
    """Labels of every lane this job matches -- a job can belong to several.

    Scope is per lane. Measured on 229 live rows: of twelve Platform-lane
    hits, all four TITLE matches were right and all eight DESCRIPTION
    matches were wrong -- discipline lists, "e.g., Systems Engineer"
    asides, section headings. Role identity lives in the title; a
    description lists everything a candidate might ever touch.

    The default still searches both, because some lanes genuinely want it:
    spotting Terragrunt in the body of an otherwise generic "Senior
    Engineer" ad is exactly the catch worth having.
    """
    return [lane.label for lane in config.lanes
            if lane.pattern.search(_haystack(job, lane.title_only))]


LOC_LIMIT = 20


def location_counts(rows):
    """(label, count) per distinct location string, most common first.

    Counts the STORED string. The only normalisation is casefold, and it is
    the only one measured to matter: on the 1,323-row fetch of 2026-08-05,
    'Remote' and 'remote' are separate strings, and reporting them apart
    splits the largest non-city group (48 rows) into 33 and 15.

    Nothing else is merged. 'Berlin' (250), 'Berlin HQ' (22) and
    'Berlin, Germany' (17) stay three lines. Every grouping rule is an
    inference, and an inference about place is exactly what produced this
    defect -- the substring 'Germany' appears in 40 rows while roughly 806
    are German, because the cities arrive bare.

    Deliberately NOT loc_bucket(). That is a dedupe key, not a geography
    classifier: it maps 'Remote job' to 'job', and dedupe_key() consumes it
    as the jobs PRIMARY KEY, so changing its output would orphan every
    stored row and reset first_seen.

    A missing location is its own key. Never folded into a place, never
    folded into 'anywhere', never dropped: 12 of those 1,323 rows had none.
    """
    tally = {}
    for row in rows:
        text = row.get("location")
        stated = text.strip() if isinstance(text, str) and text.strip() else None
        key = stated.casefold() if stated is not None else None
        surface, count = tally.get(key, ({}, 0))
        if stated is not None:
            surface[stated] = surface.get(stated, 0) + 1
        tally[key] = (surface, count + 1)

    out = []
    for key, (surface, count) in tally.items():
        # Most frequent spelling, ties broken lexicographically. Without the
        # tie-break the displayed spelling flips between runs, because dict
        # order follows ORDER BY posted_at DESC.
        label = ("(none)" if key is None
                 else sorted(surface, key=lambda s: (-surface[s], s))[0])
        out.append((label, count))
    out.sort(key=lambda pair: (-pair[1], pair[0]))
    return out


def attach_seen_age(rows, now):
    """Set row['seen_days'] = whole days since we FIRST saw the posting.

    Three sources publish no dates at all, so those rows render as a bare
    em-dash forever and a reader cannot tell a fresh one from a stale one.
    first_seen answers it -- it is the reason SQLite is in this project --
    and it was simply never surfaced.

    Computed here rather than in report.py on purpose: render_html is a pure
    function of its inputs and a test tripwires any clock access inside it,
    so the age has to arrive already calculated.

    Never presented as a posting date. "Seen 2 days ago" is a fact about
    US; claiming it as a publication date would be inventing data.
    """
    for row in rows:
        row["seen_days"] = None
        stamp = row.get("first_seen")
        if not stamp:
            continue
        try:
            seen = datetime.strptime(stamp, STAMP).replace(tzinfo=UTC)
        except (TypeError, ValueError):
            continue
        row["seen_days"] = max(0, (now - seen).days)
    return rows


def where_line(rows, limit=5):
    """The one-line 'where are these actually' summary for digest/report.

    Always on, and short. A visibility feature you have to remember to ask
    for does not fix a defect whose signature is that it looks like it
    worked -- the Spain install produced a tidy digest of German jobs and
    nothing said so.
    """
    top = location_counts(rows)
    shown = "; ".join(f"{label} ({count})" for label, count in top[:limit])
    if len(top) > limit:
        shown += f"; +{len(top) - limit} more"
    return shown


def exclusion_reason(job, config):
    """(rule, matched_term) if this job is excluded, else None.

    Returns WHICH term fired, not just that something did, so an
    over-broad entry is findable instead of silently eating results.
    """
    company = (job.get("company") or "").lower()
    for term in config.exclude_companies:
        if term in company:
            return ("company", term)
    title = (job.get("title") or "").lower()
    for term in config.exclude_titles:
        if term in title:
            return ("title", term)
    return None


def is_excluded(job, config):
    return exclusion_reason(job, config) is not None


def is_highlighted(job, config):
    haystack = _haystack(job)
    return any(term in haystack for term in config.highlight)


def source_enabled(name, config):
    entry = config.sources.get(name)
    if not isinstance(entry, dict):
        return True
    return bool(entry.get("enabled", True))


def render_table(rows):
    """Plain-text table with computed widths -- a long company name must not
    silently truncate a column."""
    header = ("Posted", "Lanes", "Company", "Role", "Where")
    body = [((row["posted_at"] or "—")[:10],
             ",".join(row["lanes"]),
             (row["company"] or "")[:28],
             ("★ " if row["highlight"] else "") + (row["title"] or "")[:44],
             (row["location"] or "")[:24]) for row in rows]
    widths = ([max(len(str(cell)) for cell in column)
               for column in zip(header, *body, strict=True)] if body else [len(h) for h in header])
    heading = "  ".join(h.ljust(w) for h, w in zip(header, widths, strict=True))
    lines = [heading, "-" * len(heading)]
    lines += ["  ".join(str(c).ljust(w) for c, w in zip(row, widths, strict=True)) for row in body]
    return "\n".join(lines)


class _Parser(argparse.ArgumentParser):
    """argparse writes to the real streams and raises SystemExit. Both are
    routed through the injected streams so main() keeps its int-return
    contract and tests can capture output."""

    def __init__(self, *args, **kwargs):
        self._out = kwargs.pop("out", None) or sys.stdout
        self._err = kwargs.pop("err", None) or sys.stderr
        super().__init__(*args, **kwargs)

    def _print_message(self, message, file=None):
        if message:
            (self._err if file is sys.stderr else self._out).write(message)

    def error(self, message):
        self._err.write(f"job-feeds: {message}\n")
        raise SystemExit(2)


def build_parser(out=None, err=None):
    parser = _Parser(prog="jfeeds", out=out, err=err,
                     description="Aggregate sanctioned public job feeds.")
    parser.add_argument("command",
                        choices=["fetch", "digest", "report", "sources",
                                 "locations", "doctor"])
    parser.add_argument("--config", default=str(CONFIG_DEFAULT))
    parser.add_argument("--db", default=str(DB_DEFAULT))
    parser.add_argument("--window", type=int, default=None)
    parser.add_argument("--only", default="")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--json", dest="as_json", action="store_true")
    parser.add_argument("--out", default=None)
    parser.add_argument("--max-pages", type=int, default=10)
    return parser


def main(argv=None, out=None, err=None, now=None, opener=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = out if out is not None else sys.stdout
    err = err if err is not None else sys.stderr

    def log(message):
        print(message, file=err)

    try:
        try:
            args = build_parser(out=out, err=err).parse_args(argv)
        except SystemExit as exc:
            # --help exits 0, a usage error exits 2. Converted to a return
            # so main never lets SystemExit escape except under __main__.
            return exc.code if isinstance(exc.code, int) else 2

        if args.command == "doctor" and not Path(args.config).exists():
            # Only doctor offers setup help. `jfeeds digest` explaining how
            # to author a config would be noise in a pipeline, so every
            # other command keeps the plain error.
            log(f"job-feeds: no config yet at {args.config}")
            log("")
            log("  The config defines your LANES — a name, a label and a regex per")
            log("  career track. Nothing is shown unless it matches one, so the lanes")
            log("  are the whole of the tool's judgement and they have to be yours.")
            log("")
            log("  Ask Claude to set it up: describe the roles you want and it")
            log("  will write the file. That is the best path -- the lanes are")
            log("  regexes, and they are the part people get wrong.")
            log("")
            log("  Working alone at a shell? This is a complete, valid config.")
            log("  Edit the one regex to name the roles you actually want.")
            log("  Copy from the line below to JSON -- it is flush left so it")
            log("  pastes as-is; an indented heredoc terminator would not work:")
            log("")
            log(f"mkdir -p {Path(args.config).parent}")
            log(f"cat > {args.config} <<'JSON'")
            log(STARTER_CONFIG)
            log("JSON")
            log("")
            log("  Then run 'jfeeds doctor' again. config.example.json beside")
            log("  this script is a fuller reference, but it encodes one")
            log("  person's career and unedited it will match the wrong jobs.")
            return 2

        config = load_config(args.config)
        window = config.window if args.window is None else args.window
        if window < 0:
            raise ConfigError("--window must not be negative")

        enabled = [name for name in SOURCES if source_enabled(name, config)]

        if args.command == "doctor":
            print(f"config    {args.config}: ok, {len(config.lanes)} lane(s)", file=out)
            print(f"database  {args.db}", file=out)
            print(f"sources   {len(enabled)} enabled of {len(SOURCES)}", file=out)
            print(f"window    {window} day(s)", file=out)
            stray = unknown_keys(args.config)
            if stray:
                print("", file=out)
                print(f"{len(stray)} key(s) not recognised — these are IGNORED, so "
                      f"anything you expected them to do is not happening:", file=out)
                for item in stray:
                    print(f"  {item}", file=out)
            return 0

        store = Store(args.db)

        if args.command == "sources":
            # EVERY source, not only the ones that have been polled. A
            # new-user test caught this: after the documented smoke test
            # (--only pythonorg) `doctor` said "8 enabled of 8" while
            # `sources` printed a single green ok line, so seven eighths of
            # the corpus was missing with nothing to say so. The one command
            # whose documented job is "don't guess whether a quiet day is
            # real" went silent exactly when the results were thin.
            states = {state["name"]: state for state in store.source_states()}
            for name in SOURCES:
                state = states.get(name)
                if state:
                    status, when = state["status"], state["last_fetch"] or ""
                    rows, reason = state["row_count"] or 0, state["reason"] or ""
                elif source_enabled(name, config):
                    status, when, rows = "never polled", "", 0
                    reason = "run 'jfeeds fetch' to include it"
                else:
                    status, when, rows, reason = "disabled", "", 0, "off in config"
                print(f"{name:<12}{status:<13}{when:<22}{rows:>6} rows  "
                      f"{reason}".rstrip(), file=out)
            if not states:
                log("job-feeds: nothing fetched yet — run 'jfeeds fetch'")
            return 0

        if args.command == "locations":
            if args.remote:
                # Warn and ignore rather than refuse. `AND remote = 1` drops
                # every row whose flag is NULL -- measured, 20 of 1,323, all
                # python.org -- and a completeness report that quietly loses
                # a source is the exact bug this command exists to expose.
                # So the flag is not honoured; saying so is the point.
                log("job-feeds: ignoring --remote for locations — the remote "
                    "flag is a source selector, not a row property, and its "
                    "SQL silently drops rows that carry no flag")
            selected = store.select(window, now, False)
            if not selected:
                log("job-feeds: nothing fetched yet — run 'jfeeds fetch'")
                return 0
            counts = location_counts(selected)
            if args.as_json:
                # Complete and untruncated on purpose: the tail is where a
                # rare location lives, and a rare location is the whole
                # question a user outside the German market is asking.
                print(json.dumps(
                    [{"location": None if label == "(none)" else label,
                      "rows": count} for label, count in counts], indent=2), file=out)
                return 0
            # "Undated rows included." was constant and unexplained, which
            # read as a disclaimer about a bug. State it only when it is
            # true, count it, and name the cause -- the fresh-install tester
            # saw an all-undated corpus and concluded date parsing had
            # broken, when three sources simply publish no dates.
            undated = sum(1 for row in selected if not row.get("posted_at"))
            note = ("" if not undated else
                    f" {undated} carry no date -- some feeds publish none, "
                    f"so those are counted here, not dropped.")
            print(f"{len(selected)} row(s) in the {window}-day window, "
                  f"{len(counts)} distinct location(s).{note}", file=out)
            print("", file=out)
            width = max(len(label) for label, _ in counts[:LOC_LIMIT])
            for label, count in counts[:LOC_LIMIT]:
                print(f"  {label:<{width}}  {count:>5}  "
                      f"{100.0 * count / len(selected):>5.1f}%", file=out)
            tail = counts[LOC_LIMIT:]
            if tail:
                rest = sum(count for _, count in tail)
                print(f"  {'+ ' + str(len(tail)) + ' other value(s)':<{width}}"
                      f"  {rest:>5}  {100.0 * rest / len(selected):>5.1f}%", file=out)
            print("", file=out)
            by_source = {}
            for row in selected:
                name = row.get("source") or "?"
                by_source[name] = by_source.get(name, 0) + 1
            print("source  " + " · ".join(
                f"{name} {n}" for name, n in
                sorted(by_source.items(), key=lambda kv: (-kv[1], kv[0]))), file=out)
            return 0

        if args.command == "fetch":
            wanted = {n.strip() for n in args.only.split(",") if n.strip()}
            chosen = [SOURCES[n] for n in enabled if not wanted or n in wanted]
            if not chosen:
                raise ConfigError(
                    "no sources selected — check --only against config 'sources'")
            limiter = RateLimiter(ratelimit_path_for(args.db))
            results = fetch_all(chosen, opener or http_open, limiter, store,
                                now or datetime.now(UTC), args.max_pages,
                                window, build_user_agent(config.contact))
            failed = []
            fresh = 0
            for result in results:
                # reason is prose again; the validator has its own column,
                # so a failure no longer discards it.
                source = SOURCES.get(result.name)
                store.record_source(
                    result.name, result.status, result.reason,
                    len(result.jobs), result.pages, now,
                    etag=result.etag,
                    etag_url=source.url if (result.etag and source) else None)
                if result.jobs:
                    # upsert has always returned (new, seen) and this loop has
                    # always thrown it away, so `fetch` could report volume but
                    # not novelty -- on a scheduled daily sweep that is the only
                    # number anyone wants. Every feed hands back its whole
                    # rolling window each time, so "1370 row(s)" says nothing
                    # about whether anything changed.
                    added, _ = store.upsert(result.jobs, now)
                    fresh += added
                if result.status in ("failed", "degraded"):
                    failed.append(result.name)
                    log(f"job-feeds: {result.name}: {result.reason}")
            log(f"job-feeds: {sum(len(r.jobs) for r in results)} row(s) "
                f"from {len(results)} source(s), {fresh} new")
            return 1 if failed else 0

        selected = store.select(window, now, args.remote)
        rows, dropped = [], []
        for row in selected:
            reason = exclusion_reason(row, config)
            (dropped if reason else rows).append(reason or row)
        attach_seen_age(rows, now or datetime.now(UTC))
        for row in rows:
            row["lanes"] = lanes_for(row, config)
            row["highlight"] = is_highlighted(row, config)
        rows = [row for row in rows if row["lanes"]]

        if dropped:
            # Silent filtering is what made "the agency filter does not
            # work" hard to see: you cannot tell a term that is missing a
            # name from one that is quietly eating half your results.
            counts = {}
            for rule, term in dropped:
                counts.setdefault(rule, set()).add(term)
            summary = "; ".join(f"{rule} ({', '.join(sorted(terms))})"
                                for rule, terms in sorted(counts.items()))
            log(f"job-feeds: {len(dropped)} row(s) excluded — {summary}")

        if rows:
            # After the lane drop, not before: "where the things I am about
            # to show you actually are", not where 1,145 rows you will never
            # see happen to be. stderr, so `digest --json | jq` is
            # unaffected -- and it fires on the --json path too, which today
            # carries no aggregate at all.
            # "2 row(s)" alone reads as a broken tool. What the fresh-install
            # tester could not tell was whether 2 was 2-of-20-from-one-source
            # or 2-of-everything: the denominators are the difference between
            # "my lanes are too narrow" and "I have only polled one feed".
            # `selected` is the in-window corpus before exclusions and lanes.
            drew = len({row.get("source") or "?" for row in selected})
            log(f"job-feeds: {len(rows)} of {len(selected)} row(s), "
                f"{drew} of {len(SOURCES)} sources — where: {where_line(rows)}")

        if args.command == "digest":
            if args.as_json:
                # [] even on the common "nothing new" outcome, so a
                # downstream jq always sees well-formed JSON.
                print(json.dumps(rows, indent=2), file=out)
            elif rows:
                print(render_table(rows), file=out)
            else:
                log(f"job-feeds: nothing matched in the last {window} day(s)")
                if selected:
                    # The dead end a user outside the German market hits.
                    # `selected` is already window-filtered, so it must not
                    # be described as "in the store".
                    log(f"job-feeds: {len(selected)} row(s) in the window — "
                        f"run 'jfeeds locations' to see where they are")
            return 0

        if args.command == "report":
            from report import render_html
            stamp = (now or datetime.now(UTC)).strftime(STAMP)
            document = render_html(rows, config, window, store.source_states(), stamp)
            if args.out:
                target = resolve_report_path(args.out, config.report_dir)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(document, encoding="utf-8")
                # The absolute path, always. The report is the deliverable,
                # and a relative name leaves the reader hunting for it --
                # a report written to $HOME because that happened to be the
                # working directory is how the two job-search tools ended up
                # scattering their output across different folders.
                log(f"job-feeds: wrote {target} ({len(rows)} row(s))")
            else:
                print(document, file=out)
            return 0
        return 2

    except ConfigError as exc:
        log(f"job-feeds: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
