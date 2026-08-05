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
import re
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

    def record(self, source, now=None, force=False):
        """No-op for sources with no declared limit, so a fresh install
        does not accumulate empty state files.

        `force` overrides that for backpressure: a 429 from a source with
        no standing limit still has to be remembered, or the next run
        retries immediately.
        """
        if not source.rate_limit_seconds and not force:
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


def _oldest_on_page(rows):
    """Oldest UTC stamp on this page, or None when the page carries no
    usable dates (an RSS page, or one whose rows are all undated)."""
    stamps = [to_utc(r.get("created_at")) for r in rows if isinstance(r, dict)]
    stamps = [s for s in stamps if s]
    return min(stamps) if stamps else None


def _fetch_one(source, opener, limiter, now, max_pages, window_days,
               seen_before=False, stored_reason="", user_agent=DEFAULT_USER_AGENT):
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
            if status in (429, 503):
                # Record the poll so the next run waits instead of walking
                # straight back into the same wall. Observed live on
                # 2026-08-05 when this project's own pagination probing
                # tripped Arbeitnow's limiter.
                limiter.record(source, now, force=True)
                retry_after = response_headers.get("Retry-After")
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
              max_pages=50, window_days=30, user_agent=DEFAULT_USER_AGENT):
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
                               window_days, s.name in known, reasons.get(s.name, ""),
                               user_agent)
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
    "lanes highlight exclude_companies exclude_titles window sources contact")


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
        contact=defaults.get("contact"))


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


def is_excluded(job, config):
    company = (job.get("company") or "").lower()
    title = (job.get("title") or "").lower()
    return (any(term in company for term in config.exclude_companies)
            or any(term in title for term in config.exclude_titles))


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
               for column in zip(header, *body)] if body else [len(h) for h in header])
    heading = "  ".join(h.ljust(w) for h, w in zip(header, widths))
    lines = [heading, "-" * len(heading)]
    lines += ["  ".join(str(c).ljust(w) for c, w in zip(row, widths)) for row in body]
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
                        choices=["fetch", "digest", "report", "sources", "doctor"])
    parser.add_argument("--config", default=str(CONFIG_DEFAULT))
    parser.add_argument("--db", default=str(DB_DEFAULT))
    parser.add_argument("--window", type=int, default=None)
    parser.add_argument("--only", default="")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--json", dest="as_json", action="store_true")
    parser.add_argument("--out", default=None)
    parser.add_argument("--max-pages", type=int, default=50)
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
            return 0

        store = Store(args.db)

        if args.command == "sources":
            states = store.source_states()
            if not states:
                log("job-feeds: nothing fetched yet — run 'jfeeds fetch'")
                return 0
            for state in states:
                print(f"{state['name']:<12}{state['status']:<11}"
                      f"{state['last_fetch'] or '':<22}{state['row_count'] or 0:>6} rows  "
                      f"{state['reason'] or ''}".rstrip(), file=out)
            return 0

        if args.command == "fetch":
            wanted = {n.strip() for n in args.only.split(",") if n.strip()}
            chosen = [SOURCES[n] for n in enabled if not wanted or n in wanted]
            if not chosen:
                raise ConfigError(
                    "no sources selected — check --only against config 'sources'")
            results = fetch_all(chosen, opener or http_open, RateLimiter(), store,
                                now or datetime.now(timezone.utc), args.max_pages,
                                window, build_user_agent(config.contact))
            failed = []
            for result in results:
                store.record_source(
                    result.name, result.status,
                    f"etag:{result.etag}" if result.etag else result.reason,
                    len(result.jobs), result.pages, now)
                if result.jobs:
                    store.upsert(result.jobs, now)
                if result.status in ("failed", "degraded"):
                    failed.append(result.name)
                    log(f"job-feeds: {result.name}: {result.reason}")
            log(f"job-feeds: {sum(len(r.jobs) for r in results)} row(s) "
                f"from {len(results)} source(s)")
            return 1 if failed else 0

        rows = [row for row in store.select(window, now, args.remote)
                if not is_excluded(row, config)]
        for row in rows:
            row["lanes"] = lanes_for(row, config)
            row["highlight"] = is_highlighted(row, config)
        rows = [row for row in rows if row["lanes"]]

        if args.command == "digest":
            if args.as_json:
                # [] even on the common "nothing new" outcome, so a
                # downstream jq always sees well-formed JSON.
                print(json.dumps(rows, indent=2), file=out)
            elif rows:
                print(render_table(rows), file=out)
            else:
                log(f"job-feeds: nothing matched in the last {window} day(s)")
            return 0

        if args.command == "report":
            from report import render_html
            stamp = (now or datetime.now(timezone.utc)).strftime(STAMP)
            document = render_html(rows, config, window, store.source_states(), stamp)
            if args.out:
                Path(args.out).write_text(document, encoding="utf-8")
                log(f"job-feeds: wrote {args.out} ({len(rows)} row(s))")
            else:
                print(document, file=out)
            return 0
        return 2

    except ConfigError as exc:
        log(f"job-feeds: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
