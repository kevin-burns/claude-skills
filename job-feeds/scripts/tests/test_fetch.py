"""Fetch layer. Every request goes through a fake opener -- no network."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from job_feeds import RateLimiter, Store, fetch_all  # noqa: E402
from sources import SOURCES  # noqa: E402

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
ARB = SOURCES["arbeitnow"].url


class FakeOpener:
    """Records every request so politeness and conditional-GET behaviour can
    be asserted. A source that should not be contacted must leave no call."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, url, headers):
        self.calls.append((url, dict(headers)))
        item = self.responses.get(url)
        if item is None:
            raise OSError(f"unexpected url {url}")
        if isinstance(item, Exception):
            raise item
        return item


def arb_row(index, created=1785930923):
    return {"slug": f"s{index}", "title": f"Engineer {index}", "company_name": "Acme",
            "location": "Berlin", "remote": True, "created_at": created,
            "url": f"https://arbeitnow.com/{index}"}


def arb_payload(rows, next_url=None):
    return json.dumps({"data": rows, "links": {"next": next_url},
                       "meta": {"current_page": 1}}).encode()


class FetchCase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.store = Store(tmp / "jobs.db")
        self.limiter = RateLimiter(tmp / "ratelimit.json")

    def run_one(self, name, responses, **kwargs):
        opener = FakeOpener(responses)
        results = fetch_all([SOURCES[name]], opener, self.limiter, self.store,
                            kwargs.pop("now", NOW), **kwargs)
        return results[0], opener


class TestFetchAll(FetchCase):

    def test_a_healthy_source_returns_ok_with_its_jobs(self):
        result, _ = self.run_one("arbeitnow", {ARB: (200, arb_payload([arb_row(1)]), {})})
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0]["source"], "arbeitnow")

    def test_one_dead_source_does_not_kill_the_others(self):
        """Per-source isolation. A single unreachable feed must not cost you
        the seven that answered."""
        opener = FakeOpener({ARB: OSError("connection reset"),
                             SOURCES["nomads"].url: (200, b"[]", {})})
        results = fetch_all([SOURCES["arbeitnow"], SOURCES["nomads"]],
                            opener, self.limiter, self.store, NOW)
        by_name = {r.name: r for r in results}
        self.assertEqual(by_name["arbeitnow"].status, "failed")
        self.assertIn("connection reset", by_name["arbeitnow"].reason)
        self.assertEqual(by_name["nomads"].status, "ok")

    def test_unparseable_json_is_a_failure_not_a_crash(self):
        result, _ = self.run_one("arbeitnow", {ARB: (200, b"<html>502</html>", {})})
        self.assertEqual(result.status, "failed")

    def test_schema_drift_marks_the_source_degraded_and_emits_no_jobs(self):
        broken = [dict(arb_row(1))]
        del broken[0]["created_at"]
        result, _ = self.run_one("arbeitnow", {ARB: (200, arb_payload(broken), {})})
        self.assertEqual(result.status, "degraded")
        self.assertIn("created_at", result.reason)
        self.assertEqual(result.jobs, [])

    def test_a_rate_limited_source_is_skipped_without_a_request(self):
        """Not merely discarded after the fact -- no call may be made."""
        self.limiter.record(SOURCES["jobicy"], NOW)
        opener = FakeOpener({})
        results = fetch_all([SOURCES["jobicy"]], opener, self.limiter, self.store,
                            NOW + timedelta(minutes=5))
        self.assertEqual(results[0].status, "throttled")
        self.assertEqual(opener.calls, [], "a throttled source must make NO request")

    def test_every_request_identifies_the_tool(self):
        _, opener = self.run_one("arbeitnow", {ARB: (200, arb_payload([arb_row(1)]), {})})
        self.assertIn("job-feeds", opener.calls[0][1]["User-Agent"])


class TestPagination(FetchCase):
    """Only Arbeitnow paginates. Measured 2026-08-05: the board ends at page
    40, links.last is always null so the total is unknowable, and page size
    varies (175, 100, 64)."""

    def test_pagination_follows_next_until_it_is_null(self):
        result, _ = self.run_one("arbeitnow", {
            ARB: (200, arb_payload([arb_row(1)], ARB + "?page=2"), {}),
            ARB + "?page=2": (200, arb_payload([arb_row(2)], None), {})})
        self.assertEqual(result.pages, 2)
        self.assertEqual(len(result.jobs), 2)

    def test_pagination_stops_at_the_page_cap_when_next_never_ends(self):
        """links.last is always null, so a broken next-chain would loop
        until the process died."""
        responses = {ARB: (200, arb_payload([arb_row(0)], f"{ARB}?page=1"), {})}
        for i in range(1, 60):
            responses[f"{ARB}?page={i}"] = (
                200, arb_payload([arb_row(i)], f"{ARB}?page={i + 1}"), {})
        opener = FakeOpener(responses)
        results = fetch_all([SOURCES["arbeitnow"]], opener, self.limiter,
                            self.store, NOW, max_pages=5)
        self.assertEqual(results[0].pages, 5)

    def test_pagination_stops_once_a_page_predates_the_cutoff(self):
        """The whole board is ~7 days deep; walking all 40 pages to collect
        rows the window will discard is 39 wasted requests."""
        old = int((NOW - timedelta(days=400)).timestamp())
        result, _ = self.run_one("arbeitnow", {
            ARB: (200, arb_payload([arb_row(1)], ARB + "?page=2"), {}),
            ARB + "?page=2": (200, arb_payload([arb_row(2, created=old)],
                                               ARB + "?page=3"), {}),
            ARB + "?page=3": (200, arb_payload([arb_row(3)], None), {})})
        self.assertEqual(result.pages, 2, "must not request page 3")

    def test_a_non_paginating_source_makes_exactly_one_request(self):
        _, opener = self.run_one("nomads", {SOURCES["nomads"].url: (200, b"[]", {})})
        self.assertEqual(len(opener.calls), 1)


class TestConditionalGet(FetchCase):
    """Only WWR ships an ETag; Arbeitnow and Jobicy expose Last-Modified but
    mark responses private/no-store. So this is opportunistic, and its
    absence must never look like a failure."""

    def test_a_304_response_is_unchanged_not_an_error(self):
        result, _ = self.run_one("arbeitnow", {ARB: (304, b"", {})})
        self.assertEqual(result.status, "unchanged")
        self.assertEqual(result.jobs, [])

    def test_a_stored_validator_is_sent_back(self):
        self.store.record_source("arbeitnow", "ok", 'etag:W/"abc"', 1, 1, NOW)
        _, opener = self.run_one("arbeitnow", {ARB: (304, b"", {})})
        self.assertEqual(opener.calls[0][1].get("If-None-Match"), 'W/"abc"')

    def test_no_validator_means_no_conditional_header(self):
        _, opener = self.run_one("arbeitnow", {ARB: (200, arb_payload([arb_row(1)]), {})})
        self.assertNotIn("If-None-Match", opener.calls[0][1])

    def test_the_validator_is_only_sent_on_the_first_page(self):
        """Page 2 is a different resource; a page-1 ETag would wrongly 304
        it and silently truncate the crawl."""
        self.store.record_source("arbeitnow", "ok", 'etag:W/"abc"', 1, 1, NOW)
        _, opener = self.run_one("arbeitnow", {
            ARB: (200, arb_payload([arb_row(1)], ARB + "?page=2"), {}),
            ARB + "?page=2": (200, arb_payload([arb_row(2)], None), {})})
        self.assertIn("If-None-Match", opener.calls[0][1])
        self.assertNotIn("If-None-Match", opener.calls[1][1])

    def test_a_returned_etag_is_captured_for_next_time(self):
        result, _ = self.run_one(
            "arbeitnow", {ARB: (200, arb_payload([arb_row(1)]), {"ETag": 'W/"xyz"'})})
        self.assertEqual(result.etag, 'W/"xyz"')


if __name__ == "__main__":
    unittest.main()
