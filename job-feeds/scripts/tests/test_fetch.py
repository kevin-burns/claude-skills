"""Fetch layer. Every request goes through a fake opener -- no network."""

import io
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from job_feeds import (  # noqa: E402
    BACKOFF_CEILING_SECONDS,
    RateLimiter,
    Store,
    fetch_all,
    main,
    parse_xml,
)
from sources import SOURCES  # noqa: E402

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
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
        self.tmp = Path(self._tmp.name)
        tmp = self.tmp
        self.store = Store(tmp / "jobs.db")
        self.limiter = RateLimiter(tmp / "ratelimit.json")

    def run_one(self, name, responses, **kwargs):
        """Never sleeps unless a test asks to observe pacing.

        Real pacing is 1s per extra page, which took the suite from 0.2s to
        18s once it was added. A suite slow enough to skip is a suite that
        stops catching things, so the delay is injected here and only the
        pacing tests pass a recorder.
        """
        opener = FakeOpener(responses)
        kwargs.setdefault("sleep", lambda _seconds: None)
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
                            opener, self.limiter, self.store, NOW, sleep=lambda _s: None)
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
                            NOW + timedelta(minutes=5), sleep=lambda _s: None)
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
                            self.store, NOW, max_pages=5, sleep=lambda _s: None)
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
        self.store.record_source("arbeitnow", "ok", "", 1, 1, NOW,
                                 etag='W/"abc"', etag_url=ARB)
        _, opener = self.run_one("arbeitnow", {ARB: (304, b"", {})})
        self.assertEqual(opener.calls[0][1].get("If-None-Match"), 'W/"abc"')

    def test_no_validator_means_no_conditional_header(self):
        _, opener = self.run_one("arbeitnow", {ARB: (200, arb_payload([arb_row(1)]), {})})
        self.assertNotIn("If-None-Match", opener.calls[0][1])

    def test_the_validator_is_only_sent_on_the_first_page(self):
        """Page 2 is a different resource; a page-1 ETag would wrongly 304
        it and silently truncate the crawl."""
        self.store.record_source("arbeitnow", "ok", "", 1, 1, NOW,
                                 etag='W/"abc"', etag_url=ARB)
        _, opener = self.run_one("arbeitnow", {
            ARB: (200, arb_payload([arb_row(1)], ARB + "?page=2"), {}),
            ARB + "?page=2": (200, arb_payload([arb_row(2)], None), {})})
        self.assertIn("If-None-Match", opener.calls[0][1])
        self.assertNotIn("If-None-Match", opener.calls[1][1])

    def test_a_returned_etag_is_captured_for_next_time(self):
        result, _ = self.run_one(
            "arbeitnow", {ARB: (200, arb_payload([arb_row(1)]), {"ETag": 'W/"xyz"'})})
        self.assertEqual(result.etag, 'W/"xyz"')


class TestBackpressure(FetchCase):
    """A 429 is the server asking us to slow down, which is different from a
    failure: retrying it is actively harmful, and reporting it as `failed`
    invites exactly that. Observed live on 2026-08-05 after this project's
    own pagination probing tripped Arbeitnow's limiter."""

    def test_a_429_is_throttled_not_failed(self):
        result, _ = self.run_one("arbeitnow", {ARB: (429, b"", {})})
        self.assertEqual(result.status, "throttled")
        self.assertIn("429", result.reason)

    def test_a_429_records_a_backoff_so_the_next_run_waits(self):
        """Without this the next `jfeeds fetch` hits the same wall
        immediately, which is how a soft limit becomes a hard block.

        Asserted on the state FILE, not via allows(): a missing file
        already fails closed for a seen source, so an allows()-based check
        passes whether or not the backoff was ever written -- it cannot
        distinguish "recorded" from "never existed".
        """
        self.limiter.record(SOURCES["jobicy"], NOW)      # file now exists
        self.assertNotIn("arbeitnow",
                         json.loads(self.limiter.path.read_text(encoding="utf-8")))
        self.run_one("arbeitnow", {ARB: (429, b"", {})})
        written = json.loads(self.limiter.path.read_text(encoding="utf-8"))
        self.assertIn("arbeitnow", written,
                      "a 429 must be remembered even though arbeitnow declares "
                      "no standing rate limit")

    def test_retry_after_is_honoured_when_the_server_sends_one(self):
        result, _ = self.run_one("arbeitnow", {ARB: (429, b"", {"Retry-After": "120"})})
        self.assertIn("120", result.reason)

    def test_a_503_is_also_treated_as_backpressure(self):
        result, _ = self.run_one("arbeitnow", {ARB: (503, b"", {})})
        self.assertEqual(result.status, "throttled")

    def test_an_ordinary_error_status_is_still_a_failure(self):
        result, _ = self.run_one("arbeitnow", {ARB: (500, b"", {})})
        self.assertEqual(result.status, "failed")


class TestHttpOpenStatusMapping(unittest.TestCase):
    """http_open is the real network function. Every other test injects a
    fake opener, so without this its status handling is entirely unguarded
    -- and it is the piece that decides whether a 429 becomes backpressure
    or a crash."""

    def _open(self, code):
        import urllib.error

        import job_feeds

        def boom(request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, code, "nope", {}, None)

        real = job_feeds.urllib.request.urlopen
        job_feeds.urllib.request.urlopen = boom
        try:
            return job_feeds.http_open("https://example.org", {})
        finally:
            job_feeds.urllib.request.urlopen = real

    def test_304_429_and_503_are_returned_not_raised(self):
        for code in (304, 429, 503):
            with self.subTest(code=code):
                status, body, _ = self._open(code)
                self.assertEqual(status, code)
                self.assertEqual(body, b"")

    def test_other_error_statuses_still_raise(self):
        import urllib.error
        for code in (404, 418, 500):
            with self.subTest(code=code), self.assertRaises(urllib.error.HTTPError):
                self._open(code)


class TestUserAgentCarriesNoPersonalData(unittest.TestCase):
    """This skill is installed by other people. A User-Agent naming the
    AUTHOR means every downstream user's traffic is attributed to them --
    so an operator investigating abuse finds the wrong person, and the
    author's identity is broadcast from machines they have never touched.

    Identify the TOOL. Let each operator opt in to their own contact.
    """

    def test_the_default_names_no_person_or_account(self):
        from job_feeds import DEFAULT_USER_AGENT
        lowered = DEFAULT_USER_AGENT.lower()
        for leak in ("kevin", "burns", "github.com/", "@", "mailto:"):
            with self.subTest(leak=leak):
                self.assertNotIn(leak, lowered,
                                 f"default User-Agent leaks {leak!r}: {DEFAULT_USER_AGENT}")

    def test_the_default_still_identifies_the_tool_and_version(self):
        """Anonymous is not the goal -- unattributable is. An operator must
        still be able to tell what is calling them."""
        from job_feeds import DEFAULT_USER_AGENT
        self.assertTrue(DEFAULT_USER_AGENT.startswith("job-feeds/"))
        self.assertRegex(DEFAULT_USER_AGENT, r"job-feeds/\d+\.\d+")

    def test_an_operator_can_add_their_own_contact(self):
        from job_feeds import build_user_agent
        agent = build_user_agent("mailto:someone@example.org")
        self.assertIn("job-feeds/", agent)
        self.assertIn("someone@example.org", agent)

    def test_no_contact_configured_means_no_contact_fragment(self):
        from job_feeds import DEFAULT_USER_AGENT, build_user_agent
        self.assertEqual(build_user_agent(None), DEFAULT_USER_AGENT)
        self.assertEqual(build_user_agent(""), DEFAULT_USER_AGENT)
        self.assertEqual(build_user_agent("   "), DEFAULT_USER_AGENT)

    def test_a_contact_cannot_inject_extra_headers(self):
        """CRLF in a header value is header injection. The contact comes
        from a config file, and config files get copied and pasted.

        The invariant is that the result is a SINGLE LINE with no control
        characters. Residual text like 'X-Injected: yes' surviving as inert
        content inside the User-Agent is not a defect: once the CRLF is
        gone it is a string, not a header. Asserting its absence would also
        be wrong, since a legitimate contact contains a colon --
        'mailto:you@example.org' is the primary use case.
        """
        from job_feeds import build_user_agent
        # A NUL is included deliberately: the \s+ collapse further down
        # already eats \r and \n, so a CRLF-only payload cannot detect
        # _HEADER_UNSAFE being removed. NUL is not whitespace, so it can.
        agent = build_user_agent("me@x.org\r\nX-Injected: yes\x00\x07")
        self.assertNotIn("\r", agent)
        self.assertNotIn("\n", agent)
        self.assertEqual(len(agent.splitlines()), 1)
        self.assertFalse(any(ord(c) < 32 or ord(c) == 127 for c in agent))

    def test_a_normal_mailto_contact_survives_intact(self):
        """Pins the sanitiser to control characters only. A colon is legal
        and load-bearing here."""
        from job_feeds import build_user_agent
        self.assertIn("mailto:you@example.org",
                      build_user_agent("mailto:you@example.org"))

    def test_an_overlong_contact_is_truncated(self):
        from job_feeds import build_user_agent
        self.assertLess(len(build_user_agent("x" * 5000)), 200)

    def test_the_configured_agent_is_what_actually_goes_on_the_wire(self):
        """A build_user_agent nobody wires up is decoration."""
        opener = FakeOpener({ARB: (200, arb_payload([arb_row(1)]), {})})
        with tempfile.TemporaryDirectory() as tmp:
            fetch_all([SOURCES["arbeitnow"]], opener,
                      RateLimiter(Path(tmp) / "r.json"), Store(Path(tmp) / "j.db"),
                      NOW, user_agent="job-feeds/9.9 (probe)", sleep=lambda _s: None)
        self.assertEqual(opener.calls[0][1]["User-Agent"], "job-feeds/9.9 (probe)")


class TestConfiguredContactReachesTheWire(unittest.TestCase):
    """build_user_agent is only useful if main() actually wires it up.
    Passing user_agent= directly to fetch_all proves the parameter works,
    not that the config path does -- those are different claims."""

    def _run(self, defaults):
        import io

        from job_feeds import main
        opener = FakeOpener({ARB: (200, arb_payload([arb_row(1)]), {})})
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps({
                "defaults": defaults,
                "lanes": [{"name": "p", "label": "P", "match": "engineer"}],
                "sources": {name: {"enabled": name == "arbeitnow"} for name in SOURCES},
            }), encoding="utf-8")
            main(["fetch", "--config", str(config), "--db", str(Path(tmp) / "j.db")],
                 out=io.StringIO(), err=io.StringIO(), now=NOW, opener=opener)
        return opener.calls[0][1]["User-Agent"]

    def test_a_configured_contact_appears_on_the_wire(self):
        self.assertIn("mailto:you@example.org",
                      self._run({"contact": "mailto:you@example.org"}))

    def test_no_configured_contact_sends_the_bare_default(self):
        from job_feeds import DEFAULT_USER_AGENT
        self.assertEqual(self._run({}), DEFAULT_USER_AGENT)


class TestRateLimitBudget(FetchCase):
    """Arbeitnow publishes its budget in every response:

        x-ratelimit-limit: 50
        x-ratelimit-remaining: 49

    We were ignoring it and paginating up to 50 pages -- at or above their
    entire allowance. That is what produced the 429 during development,
    and no amount of backing off afterwards is as good as not spending the
    budget in the first place. The header is the source of truth; guessing
    a safe page count is not.
    """

    def paged(self, count, remaining_by_page):
        """count pages, each reporting the given remaining budget."""
        responses = {}
        for i in range(count):
            url = ARB if i == 0 else f"{ARB}?page={i}"
            nxt = f"{ARB}?page={i + 1}"
            headers = {}
            if i < len(remaining_by_page) and remaining_by_page[i] is not None:
                headers["X-RateLimit-Remaining"] = str(remaining_by_page[i])
            responses[url] = (200, arb_payload([arb_row(i)], nxt), headers)
        return responses

    def test_pagination_stops_when_the_published_budget_runs_low(self):
        result, opener = self.run_one(
            "arbeitnow", self.paged(20, [40, 30, 20, 10, 4, 3, 2, 1]), max_pages=20)
        self.assertLessEqual(result.pages, 5,
                             "must stop once remaining drops to the reserve")
        self.assertEqual(result.status, "ok", "a budget stop is not a failure")

    def test_a_healthy_budget_does_not_stop_pagination(self):
        result, _ = self.run_one(
            "arbeitnow", self.paged(4, [49, 48, 47, 46]), max_pages=3)
        self.assertEqual(result.pages, 3)

    def test_a_missing_budget_header_does_not_stop_pagination(self):
        """Seven of the eight sources publish no such header. Treating its
        absence as exhaustion would silently truncate every one of them."""
        result, _ = self.run_one("arbeitnow", self.paged(4, [None] * 4), max_pages=3)
        self.assertEqual(result.pages, 3)

    def test_an_unparseable_budget_header_is_ignored(self):
        result, _ = self.run_one(
            "arbeitnow", self.paged(4, ["lots", "many", "?", "-"]), max_pages=3)
        self.assertEqual(result.pages, 3)

    def test_the_stop_is_reported_rather_than_silent(self):
        """A truncated crawl that says nothing looks like a board that
        simply ran out of jobs."""
        result, _ = self.run_one("arbeitnow", self.paged(20, [10, 3]), max_pages=20)
        self.assertIn("budget", result.reason.lower())


class TestDefaultPageCapRespectsPublishedBudgets(unittest.TestCase):
    """The default page cap was 50 -- Arbeitnow's ENTIRE advertised request
    budget (x-ratelimit-limit: 50). Walking it in one run is what produced
    the 429 repeatedly; a single deep crawl could exhaust the allowance for
    everything else sharing the IP.

    Measured 2026-08-05: page 10 of Arbeitnow reaches ~1.7 days back, so a
    cap of 10 still covers a daily delta comfortably, and the
    older-than-cutoff rule usually stops earlier still. A deliberate first
    crawl can pass --max-pages explicitly.
    """

    def test_the_default_cap_is_well_below_the_smallest_known_budget(self):
        import inspect

        from job_feeds import fetch_all
        default = inspect.signature(fetch_all).parameters["max_pages"].default
        self.assertLessEqual(default, 25,
                             "default must leave headroom in a 50-request budget")

    def test_the_cli_default_matches(self):
        from job_feeds import build_parser
        parser = build_parser()
        action = next(a for a in parser._actions if "--max-pages" in a.option_strings)
        self.assertLessEqual(action.default, 25)


class TestPagePacing(FetchCase):
    """Capping pages was not enough. Measured live 2026-08-05: ten uncached
    page requests in ~1s succeeded from a rested budget, but a second run
    moments later was refused -- Arbeitnow's limiter is burst-sensitive,
    tighter than its advertised 50-per-window suggests.

    Sequential requests to ONE host should be paced. This costs a few
    seconds on a job run twice a day and is the difference between being a
    welcome client and a blocked one.
    """

    def test_pages_after_the_first_are_paced(self):
        slept = []
        result, _ = self.run_one(
            "arbeitnow",
            {ARB: (200, arb_payload([arb_row(1)], ARB + "?page=2"), {}),
             ARB + "?page=2": (200, arb_payload([arb_row(2)], ARB + "?page=3"), {}),
             ARB + "?page=3": (200, arb_payload([arb_row(3)], None), {})},
            max_pages=5, sleep=slept.append)
        self.assertEqual(result.pages, 3)
        self.assertEqual(len(slept), 2, "one pause before each page after the first")
        self.assertTrue(all(d > 0 for d in slept))

    def test_the_first_request_is_not_delayed(self):
        slept = []
        self.run_one("arbeitnow", {ARB: (200, arb_payload([arb_row(1)], None), {})},
                     sleep=slept.append)
        self.assertEqual(slept, [], "a single-page fetch must not pause at all")

    def test_a_non_paginating_source_never_pauses(self):
        slept = []
        self.run_one("nomads", {SOURCES["nomads"].url: (200, b"[]", {})},
                     sleep=slept.append)
        self.assertEqual(slept, [])

    def test_the_default_pace_is_a_real_delay(self):
        """A default of zero would make the guard decorative."""
        from job_feeds import PAGE_DELAY_SECONDS
        self.assertGreaterEqual(PAGE_DELAY_SECONDS, 0.5)


if __name__ == "__main__":
    unittest.main()


class TestBackoffEscalates(FetchCase):
    """A flat backoff means a persistently unhappy source gets poked once an
    hour, forever. That is politer than retrying immediately and less polite
    than it should be — and Arbeitnow's live 429 on 2026-08-05 was our own
    doing, so the escalation is a guard against ourselves.

    These read and write the state file directly rather than driving eight
    real fetches, because the property under test is the curve, not the HTTP.
    """

    def strikes_of(self, name):
        """0 when the key is absent: a recovered source with no standing
        limit has its entry dropped entirely, returning the file to the
        shape a fresh install has."""
        state = json.loads(self.limiter.path.read_text(encoding="utf-8"))
        entry = state.get(name)
        return entry.get("strikes", 0) if isinstance(entry, dict) else 0

    def throttle(self, name, retry_after=None):
        source = SOURCES[name]
        backoff = self.limiter.next_backoff(source, retry_after)
        self.limiter.record(source, NOW, force=True, backoff_seconds=backoff)
        return backoff

    def test_consecutive_throttles_double_the_wait(self):
        self.assertEqual(self.throttle("arbeitnow"), 3600)
        self.assertEqual(self.throttle("arbeitnow"), 7200)
        self.assertEqual(self.throttle("arbeitnow"), 14400)

    def test_escalation_stops_at_the_ceiling(self):
        """Unbounded doubling parks a source for years after a bad week."""
        for _ in range(12):
            applied = self.throttle("arbeitnow")
        self.assertEqual(applied, BACKOFF_CEILING_SECONDS)

    def test_a_clean_poll_clears_the_history(self):
        """One bad afternoon must not keep punishing a source for days."""
        self.throttle("arbeitnow")
        self.throttle("arbeitnow")
        self.assertEqual(self.strikes_of("arbeitnow"), 2)
        self.limiter.record(SOURCES["arbeitnow"], NOW, force=True, healthy=True)
        self.assertEqual(self.strikes_of("arbeitnow"), 0)
        self.assertEqual(self.throttle("arbeitnow"), 3600,
                         "after a healthy poll the curve restarts at the bottom")

    def test_a_successful_fetch_clears_the_history_end_to_end(self):
        """The unit above proves the limiter resets; this proves fetch_all
        actually calls it that way. Without the healthy=True at the success
        site, a source that recovers keeps its strikes and the next hiccup
        jumps straight to hours."""
        self.throttle("arbeitnow")
        self.throttle("arbeitnow")
        # Past the 7200s backoff the second throttle just wrote — inside it,
        # allows() correctly refuses and the fetch never happens, so this
        # would assert on a poll that was never made.
        later = NOW + timedelta(seconds=7201)
        self.run_one("arbeitnow", {ARB: (200, arb_payload([arb_row(1)]), {})},
                     now=later)
        self.assertEqual(self.strikes_of("arbeitnow"), 0)

    def test_a_network_error_does_NOT_clear_the_history(self):
        """A socket timeout says nothing about whether the source has stopped
        throttling us. Treating it as recovery would let a flapping source
        reset the curve every other run and never escalate at all."""
        self.throttle("arbeitnow")
        self.throttle("arbeitnow")

        def boom(_url, _headers):
            raise OSError("connection reset")

        # Past the backoff, or allows() refuses and the error path never
        # runs -- which made an earlier version of this test pass whether
        # or not a network error cleared the strikes.
        later = NOW + timedelta(seconds=7201)
        fetch_all([SOURCES["arbeitnow"]], boom, self.limiter, self.store, later,
                  sleep=lambda _s: None)
        self.assertEqual(self.strikes_of("arbeitnow"), 2)

    def test_retry_after_beats_the_escalation_in_both_directions(self):
        """The server stating its own terms outranks our curve — including
        when its number is SMALLER than where we had escalated to. Second-
        guessing that would be the opposite of the politeness this is for."""
        for _ in range(4):
            self.throttle("arbeitnow")          # escalated well past an hour
        self.assertEqual(self.limiter.next_backoff(SOURCES["arbeitnow"], "120"), 120)
        self.assertEqual(self.limiter.next_backoff(SOURCES["arbeitnow"], "99999"),
                         BACKOFF_CEILING_SECONDS, "a hostile value is still clamped")
        self.assertEqual(self.limiter.next_backoff(SOURCES["arbeitnow"], "5"), 60,
                         "and an absurdly small one is floored")

    def test_a_legacy_state_file_starts_the_curve_from_the_bottom(self):
        """Upgrading must not crash on the old flat-timestamp form, and must
        not invent a strike history that was never recorded."""
        self.limiter.path.write_text(json.dumps({"arbeitnow": "2026-08-05T10:00:00Z"}),
                                     encoding="utf-8")
        self.assertEqual(self.limiter.next_backoff(SOURCES["arbeitnow"]), 3600)

    def test_an_unreadable_state_file_does_not_escalate_wildly(self):
        """Failing closed is about refusing to POLL. It must not also produce
        a garbage backoff — allows() already blocks, and a nonsense number
        written on top would outlive the corruption."""
        self.limiter.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.limiter.next_backoff(SOURCES["arbeitnow"]), 3600)


class TestTheValidatorSurvivesFailure(FetchCase):
    """The ETag used to share the `reason` column with human prose, so any
    fetch that returned no validator overwrote it — a 429, a 500, a socket
    error, a schema drift. The next run then re-downloaded everything.

    Worst exactly when it hurts most: a hiccup is when a conditional request
    is most valuable, and Arbeitnow is ~1MB per full crawl.
    """

    def stored(self, name="arbeitnow"):
        return {s["name"]: s for s in self.store.source_states()}.get(name, {})

    def fetch_via_cli(self, responses, name="arbeitnow"):
        """Run the real `fetch` command against a fake opener, then read the
        row back. This is the only path that exercises record_source."""
        config = self.tmp / "config.json"
        config.write_text(json.dumps({
            "defaults": {"window": 14},
            "lanes": [{"name": "l", "label": "L", "match": "engineer"}],
            "highlight": [], "sources": {name: {"enabled": True}}}), encoding="utf-8")
        main(["fetch", "--only", name, "--config", str(config),
              "--db", str(self.store.path)],
             out=io.StringIO(), err=io.StringIO(), now=NOW,
             opener=FakeOpener(responses))
        return self.stored(name)

    def seed_validator(self, url=ARB):
        self.store.record_source("arbeitnow", "ok", "", 1, 1, NOW,
                                 etag='W/"keep-me"', etag_url=url)

    def test_a_throttled_fetch_does_not_discard_the_validator(self):
        self.seed_validator()
        self.store.record_source("arbeitnow", "throttled", "HTTP 429 — backing off",
                                 0, 0, NOW)
        self.assertEqual(self.stored()["etag"], 'W/"keep-me"')

    def test_a_failed_fetch_does_not_discard_the_validator(self):
        self.seed_validator()
        self.store.record_source("arbeitnow", "failed", "OSError: connection reset",
                                 0, 0, NOW)
        self.assertEqual(self.stored()["etag"], 'W/"keep-me"')

    def test_a_schema_drift_does_not_discard_the_validator(self):
        self.seed_validator()
        self.store.record_source("arbeitnow", "degraded",
                                 "schema-drift: missing created_at", 0, 0, NOW)
        self.assertEqual(self.stored()["etag"], 'W/"keep-me"')

    def test_reason_is_prose_again_not_a_cache_key(self):
        """Drives `jfeeds fetch` itself, because record_source is called from
        the CLI and not from fetch_all -- a Store-level assertion here would
        only prove that record_source stores what it is handed, which is
        trivially true and was never the bug."""
        state = self.fetch_via_cli({ARB: (200, arb_payload([arb_row(1)]),
                                          {"ETag": 'W/"abc"'})})
        self.assertNotIn("etag:", state["reason"] or "",
                         "the validator must not be smuggled into the prose column")
        self.assertEqual(state["etag"], 'W/"abc"')
        self.assertEqual(state["etag_url"], ARB,
                         "the URL must be recorded or the validator can never be used")

    def test_a_new_validator_still_replaces_the_old_one(self):
        """Preservation must not become stickiness — COALESCE keeps the old
        value only when the new one is absent."""
        self.seed_validator()
        self.store.record_source("arbeitnow", "ok", "", 1, 1, NOW,
                                 etag='W/"fresh"', etag_url=ARB)
        self.assertEqual(self.stored()["etag"], 'W/"fresh"')

    def test_the_validator_survives_a_failure_end_to_end(self):
        """The unit tests above prove the SQL. This proves fetch_all actually
        routes it that way, and that the surviving etag is still sent."""
        self.fetch_via_cli({ARB: (200, arb_payload([arb_row(1)]),
                                  {"ETag": 'W/"keep-me"'})})
        self.assertEqual(self.stored()["etag"], 'W/"keep-me"')
        self.fetch_via_cli({ARB: (500, b"", {})})       # a failure, mid-life
        self.assertEqual(self.stored()["etag"], 'W/"keep-me"',
                         "a 500 must not cost us the validator")
        _, opener = self.run_one("arbeitnow", {ARB: (304, b"", {})})
        self.assertEqual(opener.calls[0][1].get("If-None-Match"), 'W/"keep-me"',
                         "and the surviving validator must still be sent")


class TestTheValidatorIsBoundToItsUrl(FetchCase):
    """An ETag validates ONE resource. Replaying it against a changed URL can
    return 304 with zero rows while `jfeeds sources` reports `unchanged` —
    silent, and it looks like it worked. Found while spiking a per-source geo
    parameter for jobicy."""

    def test_a_validator_captured_from_a_different_url_is_not_replayed(self):
        self.store.record_source("arbeitnow", "ok", "", 1, 1, NOW,
                                 etag='W/"old"', etag_url=ARB + "?geo=europe")
        _, opener = self.run_one("arbeitnow", {ARB: (200, arb_payload([arb_row(1)]), {})})
        self.assertNotIn("If-None-Match", opener.calls[0][1],
                         "changing a source URL must drop the stale validator")

    def test_a_validator_captured_from_the_same_url_is_replayed(self):
        """The paired half: without it, the test above passes trivially if
        the validator is never sent at all."""
        self.store.record_source("arbeitnow", "ok", "", 1, 1, NOW,
                                 etag='W/"same"', etag_url=ARB)
        _, opener = self.run_one("arbeitnow", {ARB: (304, b"", {})})
        self.assertEqual(opener.calls[0][1].get("If-None-Match"), 'W/"same"')

    def test_a_stored_etag_with_no_url_is_not_replayed(self):
        """The pre-migration shape. Nothing recorded which URL it came from,
        so it cannot be shown safe and must not be used."""
        self.store.record_source("arbeitnow", "ok", "", 1, 1, NOW)
        self.store.conn.execute("UPDATE sources SET etag='W/\"orphan\"' WHERE name=?",
                                ("arbeitnow",))
        self.store.conn.commit()
        _, opener = self.run_one("arbeitnow", {ARB: (200, arb_payload([arb_row(1)]), {})})
        self.assertNotIn("If-None-Match", opener.calls[0][1])


class TestStoreMigration(unittest.TestCase):
    """CREATE TABLE IF NOT EXISTS does nothing to a table that already
    exists, so a store built before the etag columns must be upgraded or
    every query against it breaks."""

    def test_an_old_store_gains_the_columns_and_keeps_its_rows(self):
        tmp = Path(tempfile.mkdtemp()) / "old.db"
        conn = sqlite3.connect(str(tmp))
        conn.execute("CREATE TABLE sources (name TEXT PRIMARY KEY, last_fetch TEXT,"
                     " status TEXT, reason TEXT, row_count INTEGER, pages INTEGER)")
        conn.execute("INSERT INTO sources VALUES ('arbeitnow','2026-08-05T10:00:00Z',"
                     "'ok','etag:W/\"legacy\"',5,1)")
        conn.commit()
        conn.close()

        store = Store(tmp)                      # must not raise
        state = {s["name"]: s for s in store.source_states()}["arbeitnow"]
        self.assertIn("etag", state)
        self.assertEqual(state["row_count"], 5, "existing rows must survive")
        self.assertEqual(state["reason"], "",
                         "the old etag: prefix is cleared, not left as prose")
        self.assertIsNone(state["etag"],
                          "a legacy etag has no recorded URL, so it is not carried over")


class TestRateLimitStateIsWrittenAtomically(unittest.TestCase):
    """write_text() opens with 'w', which truncates before writing. An
    interrupted write — or a second jfeeds process — left a truncated file,
    and the limiter then classified it unreadable and refused every poll.
    That fails safe, but it also discards any recorded backoff and looks
    exactly like a real problem.

    Matters more with several people running this than it did with one.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.limiter = RateLimiter(self.tmp / "ratelimit.json")
        self.source = SOURCES["jobicy"]          # declares a standing limit

    def partial_write(self):
        """Patch Path.write_text to truncate-and-die, which is exactly what a
        full disk or a killed process does.

        The failure must land INSIDE the write, not before it. An earlier
        version of this test raised from json.dumps — evaluated as an
        argument, so it fired before the file was ever opened, and passed
        whether the write was atomic or not.
        """
        real = Path.write_text

        def die_halfway(self_path, data, **kwargs):
            real(self_path, data[: len(data) // 2], **kwargs)   # truncated
            raise RuntimeError("disk full")

        Path.write_text = die_halfway
        self.addCleanup(lambda: setattr(Path, "write_text", real))

    def test_a_crash_mid_write_leaves_the_previous_state_intact(self):
        self.limiter.record(self.source, NOW)
        before = self.limiter.path.read_text(encoding="utf-8")

        self.partial_write()
        with self.assertRaises(RuntimeError):
            self.limiter.record(self.source, NOW + timedelta(hours=2))
        Path.write_text = Path.write_text.__wrapped__ if hasattr(
            Path.write_text, "__wrapped__") else Path.write_text

        self.assertEqual(self.limiter.path.read_text(encoding="utf-8"), before,
                         "a half-written file must not land on the real state")
        self.assertIsNone(self.limiter._load()[1], "and it must still parse")

    def test_no_temp_fragments_survive_a_failed_write(self):
        """Checked after a FAILURE, not a success: os.replace consumes the
        temp file on the happy path, so a success-path assertion cannot fail
        and proves nothing."""
        self.limiter.record(self.source, NOW)
        self.partial_write()
        with self.assertRaises(RuntimeError):
            self.limiter.record(self.source, NOW + timedelta(hours=2))
        leftovers = [q.name for q in self.tmp.iterdir() if ".tmp" in q.name]
        self.assertEqual(leftovers, [],
                         "a crashed write must not litter the config directory")

    def test_the_written_state_is_still_correct(self):
        """Guards the guard: atomicity is worthless if the payload changed."""
        self.limiter.record(self.source, NOW)
        state = json.loads(self.limiter.path.read_text(encoding="utf-8"))
        self.assertIn("jobicy", state)


class TestFetchReportsNoveltyAndWritesStateOnce(unittest.TestCase):
    """Both guards here exist because of the same near-miss.

    `fetch` reported volume but not novelty: upsert has always returned
    (new, seen) and the CLI threw it away. Every feed hands back its whole
    rolling window on every poll, so "1370 row(s)" is the same number on
    day one and day fifty and says nothing about whether anything changed
    -- which is the only question a scheduled daily sweep asks.

    While adding that, an edit duplicated the results loop so record_source
    ran twice per fetch, and the whole suite still passed. That looked like
    a coverage gap and was not: record_source is
    INSERT .. ON CONFLICT(name) DO UPDATE, so a second identical call is
    idempotent and leaves one row with identical values. A guard was written
    for it, could not be made to fail against the real bug, and was deleted
    rather than kept -- a test that cannot fail is worse than no test,
    because it reads like cover.
    """

    def _run(self, rows, second_pass=False):
        import io
        import sqlite3

        from job_feeds import main
        payload = arb_payload([arb_row(i) for i in rows])
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps({
                "defaults": {},
                "lanes": [{"name": "p", "label": "P", "match": "engineer"}],
                "sources": {name: {"enabled": name == "arbeitnow"} for name in SOURCES},
            }), encoding="utf-8")
            db = Path(tmp) / "j.db"
            err = io.StringIO()
            calls = []

            def run():
                opener = FakeOpener({ARB: (200, payload, {})})
                main(["fetch", "--config", str(config), "--db", str(db)],
                     out=io.StringIO(), err=err, now=NOW, opener=opener)
                calls.append(opener)

            run()
            first = err.getvalue()
            second = None
            if second_pass:
                err.truncate(0), err.seek(0)
                run()
                second = err.getvalue()
            # Counted INSIDE the TemporaryDirectory: returning the path and
            # opening it afterwards fails, because the directory is already
            # gone by then.
            conn = sqlite3.connect(str(db))
            try:
                source_rows = conn.execute(
                    "SELECT COUNT(*) FROM sources WHERE name = 'arbeitnow'").fetchone()[0]
            finally:
                conn.close()
            return first, second, source_rows

    def test_fetch_reports_how_many_rows_are_new(self):
        first, _, _ = self._run([1, 2, 3])
        self.assertIn("3 new", first)

    def test_a_second_identical_fetch_reports_zero_new(self):
        """The number that matters on a daily sweep. If this said 3 again,
        a scheduled run could never distinguish a quiet day from a busy
        one -- the feeds resend everything either way."""
        first, second, _ = self._run([1, 2, 3], second_pass=True)
        self.assertIn("3 new", first)
        self.assertIn("0 new", second)
        self.assertIn("row(s)", second, "volume must still be reported")


class ParseXmlRefusesEntityExpansion(unittest.TestCase):
    """A feed body is remote and untrusted. MEASURED on 3.14.7 rather than
    assumed: ElementTree refuses external entities but expands internal ones,
    so the risk is a billion-laughs blow-up rather than XXE, and the fix is to
    refuse the DOCTYPE that is the only way to define an entity."""

    BOMB = (b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
            b'<!ENTITY lol2 "&lol;&lol;&lol;">]><lolz>&lol2;</lolz>')

    def test_a_body_defining_entities_is_refused(self):
        # Fails against the old code, which parsed this and expanded &lol2;.
        with self.assertRaises(ValueError) as caught:
            parse_xml(self.BOMB)
        self.assertIn("DOCTYPE", str(caught.exception))

    def test_the_refusal_does_not_depend_on_the_doctype_sitting_in_the_prolog(self):
        # Scanning only up to the "first element" is defeatable: a comment
        # containing a tag stops that search early.
        sneaky = b'<?xml version="1.0"?><!-- <a> --><!DOCTYPE d [<!ENTITY e "x">]><d>&e;</d>'
        with self.assertRaises(ValueError):
            parse_xml(sneaky)

    def test_an_ordinary_feed_still_parses(self):
        # The direction that matters more: the guard must not break real feeds.
        feed = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
                b'<item><title>Platform Engineer</title></item></channel></rss>')
        root = parse_xml(feed)
        self.assertEqual(root.find("./channel/item/title").text, "Platform Engineer")

    def test_a_case_variant_doctype_is_not_a_way_round_it(self):
        with self.assertRaises(ValueError):
            parse_xml(b'<?xml version="1.0"?><!doctype d []><d/>')
