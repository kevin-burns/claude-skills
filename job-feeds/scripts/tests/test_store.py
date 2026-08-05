"""Rate limiter and SQLite store. No network, no real ~/.config access."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from job_feeds import STAMP, RateLimiter  # noqa: E402
from sources import SOURCES  # noqa: E402

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)


class TestRateLimiter(unittest.TestCase):
    """Jobicy documents 1 poll/hour fair use. Violating a documented limit
    risks losing the source permanently, so every ambiguous state refuses
    the poll: a stale run costs nothing, a ban costs the feed.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "ratelimit.json"

    def test_a_source_with_no_declared_limit_is_always_allowed(self):
        allowed, _ = RateLimiter(self.path).allows(SOURCES["arbeitnow"], NOW)
        self.assertTrue(allowed)

    def test_a_fresh_install_allows_the_first_poll(self):
        allowed, _ = RateLimiter(self.path).allows(SOURCES["jobicy"], NOW)
        self.assertTrue(allowed)

    def test_a_second_poll_inside_the_window_is_refused_with_the_next_time(self):
        RateLimiter(self.path).record(SOURCES["jobicy"], NOW)
        allowed, reason = RateLimiter(self.path).allows(
            SOURCES["jobicy"], NOW + timedelta(minutes=30))
        self.assertFalse(allowed)
        self.assertIn("13:00", reason)

    def test_a_poll_after_the_window_is_allowed(self):
        RateLimiter(self.path).record(SOURCES["jobicy"], NOW)
        allowed, _ = RateLimiter(self.path).allows(
            SOURCES["jobicy"], NOW + timedelta(hours=1, seconds=1))
        self.assertTrue(allowed)

    def test_a_MISSING_state_file_fails_CLOSED_for_a_known_source(self):
        """The design council's requirement. State lives outside jobs.db so
        deleting the database cannot make the tool forget it already
        polled -- but a missing file must not read as "never polled"
        either, or `rm` becomes a way to hammer a source into banning us."""
        allowed, reason = RateLimiter(self.path).allows(SOURCES["jobicy"], NOW, seen=True)
        self.assertFalse(allowed)
        self.assertIn("no rate-limit state", reason)

    def test_a_corrupt_state_file_fails_CLOSED(self):
        self.path.write_text("{not json", encoding="utf-8")
        allowed, reason = RateLimiter(self.path).allows(SOURCES["jobicy"], NOW)
        self.assertFalse(allowed)
        self.assertIn("unreadable", reason)

    def test_an_unparseable_timestamp_fails_CLOSED(self):
        self.path.write_text(json.dumps({"jobicy": "last tuesday"}), encoding="utf-8")
        allowed, reason = RateLimiter(self.path).allows(SOURCES["jobicy"], NOW)
        self.assertFalse(allowed)
        self.assertIn("unparseable", reason)

    def test_recording_is_durable_across_instances(self):
        RateLimiter(self.path).record(SOURCES["jobicy"], NOW)
        self.assertIn("jobicy", json.loads(self.path.read_text(encoding="utf-8")))

    def test_recording_a_limitless_source_writes_nothing(self):
        """No file is created for sources with no declared limit, so a
        fresh install does not accumulate empty state."""
        RateLimiter(self.path).record(SOURCES["arbeitnow"], NOW)
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
