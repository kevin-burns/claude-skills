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
