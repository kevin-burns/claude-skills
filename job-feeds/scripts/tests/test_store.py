"""Rate limiter and SQLite store. No network, no real ~/.config access."""

import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from job_feeds import STAMP, RateLimiter, Store  # noqa: E402
from sources import SOURCES  # noqa: E402

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)


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


def job(company="Acme", title="Cloud Engineer", location="Berlin",
        posted_at="2026-08-04T00:00:00Z", source="arbeitnow", url="https://x/1",
        description="d", remote=True):
    return {"title": title, "company": company, "location": location, "remote": remote,
            "posted_at": posted_at, "url": url, "description": description,
            "tags": [], "salary": None, "source": source}


class TestStore(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = Store(Path(self._tmp.name) / "jobs.db")

    def test_first_insert_counts_as_new(self):
        self.assertEqual(self.store.upsert([job()], NOW), (1, 0))

    def test_reinserting_the_same_job_is_seen_not_new(self):
        self.store.upsert([job()], NOW)
        self.assertEqual(self.store.upsert([job()], NOW + timedelta(days=1)), (0, 1))

    def test_first_seen_is_preserved_on_reinsert(self):
        """The reason SQLite is here at all. The feeds return a rolling
        window with no notion of newness, so first_seen is the ONLY way to
        answer "what appeared since I last looked"."""
        self.store.upsert([job()], NOW)
        self.store.upsert([job()], NOW + timedelta(days=3))
        row = self.store.select(window_days=30, now=NOW + timedelta(days=3))[0]
        self.assertEqual(row["first_seen"], NOW.strftime(STAMP))
        self.assertEqual(row["last_seen"], (NOW + timedelta(days=3)).strftime(STAMP))

    def test_the_same_job_from_two_sources_collapses_to_one_row(self):
        self.store.upsert([job(source="remotive", url="https://a"),
                           job(source="wwr", url="https://b")], NOW)
        rows = self.store.select(window_days=30, now=NOW)
        self.assertEqual(len(rows), 1)

    def test_a_cross_source_duplicate_records_where_else_it_appeared(self):
        """Surfacing "also on X" beats silently dropping the second copy --
        the other listing may be the one worth applying through."""
        self.store.upsert([job(source="remotive", url="https://a")], NOW)
        self.store.upsert([job(source="wwr", url="https://b")], NOW)
        self.assertEqual(self.store.select(30, NOW)[0]["also_seen_on"], "wwr")

    def test_rows_outside_the_window_are_excluded(self):
        self.store.upsert([job(posted_at="2026-06-01T00:00:00Z")], NOW)
        self.assertEqual(self.store.select(window_days=14, now=NOW), [])

    def test_undated_rows_are_kept_not_silently_dropped(self):
        """python.org carries no dates at all, so a naive date filter would
        delete that entire source without saying so."""
        self.store.upsert([job(posted_at=None, source="pythonorg")], NOW)
        rows = self.store.select(window_days=14, now=NOW)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["posted_at"])

    def test_remote_only_filters(self):
        self.store.upsert([job(title="A", remote=True),
                           job(title="B", remote=False)], NOW)
        rows = self.store.select(30, NOW, remote_only=True)
        self.assertEqual([r["title"] for r in rows], ["A"])

    def test_rows_are_ordered_newest_first_with_undated_last(self):
        self.store.upsert([job(title="old", posted_at="2026-08-01T00:00:00Z"),
                           job(title="undated", posted_at=None),
                           job(title="new", posted_at="2026-08-04T00:00:00Z")], NOW)
        self.assertEqual([r["title"] for r in self.store.select(30, NOW)],
                         ["new", "old", "undated"])

    def test_source_state_records_the_reason_not_just_the_status(self):
        """Two years on, "jobicy returned nothing" could be a rate limit, a
        geo filter, a schema change or a swallowed exception."""
        self.store.record_source("remotive", "degraded",
                                 "schema-drift: missing publication_date", 0, 0, NOW)
        state = {s["name"]: s for s in self.store.source_states()}["remotive"]
        self.assertEqual(state["status"], "degraded")
        self.assertIn("publication_date", state["reason"])

    def test_recording_a_source_twice_updates_rather_than_duplicates(self):
        self.store.record_source("jobicy", "ok", "", 5, 1, NOW)
        self.store.record_source("jobicy", "throttled", "fair use", 0, 0, NOW)
        states = [s for s in self.store.source_states() if s["name"] == "jobicy"]
        self.assertEqual(len(states), 1)
        self.assertEqual(states[0]["status"], "throttled")

    def test_known_sources_reports_what_has_been_polled(self):
        self.assertEqual(self.store.known_sources(), set())
        self.store.record_source("jobicy", "ok", "", 5, 1, NOW)
        self.assertEqual(self.store.known_sources(), {"jobicy"})

    def test_a_reopened_database_keeps_its_rows(self):
        path = Path(self._tmp.name) / "persist.db"
        Store(path).upsert([job()], NOW)
        self.assertEqual(len(Store(path).select(30, NOW)), 1)


class TestRateLimiterConcurrency(unittest.TestCase):
    """record() is a read-modify-write on a file shared by worker threads.
    Only Jobicy declares a limit today, so nothing collides in practice --
    but that is luck, not design, and the failure would be silent: one
    source's poll time overwrites another's, and the lost source becomes
    pollable again inside its window.
    """

    def test_concurrent_records_do_not_lose_entries(self):
        from concurrent.futures import ThreadPoolExecutor

        limited = [SOURCES["jobicy"]._replace(name=f"src{i}", rate_limit_seconds=3600)
                   for i in range(8)]
        with tempfile.TemporaryDirectory() as tmp:
            limiter = RateLimiter(Path(tmp) / "ratelimit.json")
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda src: limiter.record(src, NOW), limited))
            written = json.loads(limiter.path.read_text(encoding="utf-8"))
        self.assertEqual(sorted(written), [f"src{i}" for i in range(8)])


class TestBackoffIsActuallyHonoured(unittest.TestCase):
    """A recorded backoff that nothing reads is worse than none: it looks
    like protection while every run walks back into the same 429, which is
    exactly what turns a soft limit into a hard block.

    Caught on a live run. Jobicy recovered correctly after its documented
    hour, but Arbeitnow -- which declares NO standing limit -- sent a
    request to rediscover it was still throttled, because allows() returned
    early on `not source.rate_limit_seconds` and never consulted the
    backoff that had been written for it.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "ratelimit.json"

    def test_a_backoff_blocks_a_source_with_no_standing_limit(self):
        limiter = RateLimiter(self.path)
        limiter.record(SOURCES["arbeitnow"], NOW, force=True, backoff_seconds=3600)
        allowed, reason = RateLimiter(self.path).allows(
            SOURCES["arbeitnow"], NOW + timedelta(minutes=30), seen=True)
        self.assertFalse(allowed, "a 429 backoff must be honoured, not merely stored")
        self.assertIn("backing off", reason)

    def test_the_backoff_expires(self):
        limiter = RateLimiter(self.path)
        limiter.record(SOURCES["arbeitnow"], NOW, force=True, backoff_seconds=3600)
        allowed, _ = RateLimiter(self.path).allows(
            SOURCES["arbeitnow"], NOW + timedelta(hours=1, seconds=1), seen=True)
        self.assertTrue(allowed)

    def test_a_retry_after_value_sets_the_backoff_length(self):
        limiter = RateLimiter(self.path)
        limiter.record(SOURCES["arbeitnow"], NOW, force=True, backoff_seconds=120)
        early, _ = RateLimiter(self.path).allows(
            SOURCES["arbeitnow"], NOW + timedelta(seconds=60), seen=True)
        later, _ = RateLimiter(self.path).allows(
            SOURCES["arbeitnow"], NOW + timedelta(seconds=121), seen=True)
        self.assertFalse(early)
        self.assertTrue(later)

    def test_an_ordinary_poll_does_not_create_a_backoff(self):
        """Only a 429/503 backs off. A healthy fetch of a limitless source
        must leave it immediately pollable."""
        RateLimiter(self.path).record(SOURCES["arbeitnow"], NOW)
        allowed, _ = RateLimiter(self.path).allows(
            SOURCES["arbeitnow"], NOW + timedelta(seconds=1), seen=True)
        self.assertTrue(allowed)

    def test_a_standing_limit_still_works_alongside_backoffs(self):
        limiter = RateLimiter(self.path)
        limiter.record(SOURCES["jobicy"], NOW)
        blocked, _ = limiter.allows(SOURCES["jobicy"], NOW + timedelta(minutes=30))
        freed, _ = limiter.allows(SOURCES["jobicy"], NOW + timedelta(hours=1, seconds=1))
        self.assertFalse(blocked)
        self.assertTrue(freed)

    def test_legacy_flat_timestamp_state_is_still_readable(self):
        """The state file predates the backoff format; a stale one on disk
        must not crash or silently unblock everything."""
        self.path.write_text(json.dumps({"jobicy": NOW.strftime(STAMP)}), encoding="utf-8")
        allowed, _ = RateLimiter(self.path).allows(
            SOURCES["jobicy"], NOW + timedelta(minutes=5))
        self.assertFalse(allowed)


class TestRateLimitStateIsScopedToTheDatabase(unittest.TestCase):
    """--db must isolate everything. Before this, main() built a
    RateLimiter on the DEFAULT path, so every scratch run and every test
    read and wrote the operator's real ~/.config/job-feeds/ratelimit.json.
    A live Arbeitnow backoff leaked into the test suite and failed two
    unrelated tests, which is how it was found.

    The file still sits BESIDE the database rather than inside it, so the
    original property holds: deleting jobs.db does not lose the record of
    what has already been polled.
    """

    def test_the_path_is_derived_from_the_database_location(self):
        from job_feeds import ratelimit_path_for
        self.assertEqual(ratelimit_path_for("/tmp/x/jobs.db"),
                         Path("/tmp/x/ratelimit.json"))

    def test_a_scratch_db_does_not_touch_the_real_state_file(self):
        from job_feeds import RATELIMIT_DEFAULT, ratelimit_path_for
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotEqual(ratelimit_path_for(Path(tmp) / "jobs.db"),
                                RATELIMIT_DEFAULT)

    def test_the_default_db_still_maps_to_the_default_state_file(self):
        from job_feeds import DB_DEFAULT, RATELIMIT_DEFAULT, ratelimit_path_for
        self.assertEqual(ratelimit_path_for(DB_DEFAULT), RATELIMIT_DEFAULT)


if __name__ == "__main__":
    unittest.main()
