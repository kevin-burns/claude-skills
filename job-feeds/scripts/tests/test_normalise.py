"""Stdlib-only tests for job-feeds normalisation. No network, no live feeds."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import dedupe_key, loc_bucket, to_utc  # noqa: E402


class TestToUtc(unittest.TestCase):
    """Every case is a real value observed in a live payload on 2026-08-05,
    except the two synthesised offset cases, which exist because the
    offset-shifting arithmetic is the part that silently corrupts ordering.
    """

    def test_real_formats_from_every_source(self):
        cases = [
            (1785930923, "2026-08-05T11:55:23Z", "arbeitnow: unix int"),
            ("2026-08-05T12:16:06Z", "2026-08-05T12:16:06Z", "4dayweek: Z suffix"),
            ("2026-08-05T10:20:02+00:00", "2026-08-05T10:20:02Z", "jobicy: explicit +00:00"),
            ("2026-08-02T20:00:46", "2026-08-02T20:00:46Z", "remotive: naive, assume UTC"),
            ("2026-07-31T15:21:46-04:00", "2026-07-31T19:21:46Z", "nomads: -0400 shifts +4h"),
            ("Wed, 22 Jul 2026 07:01:06 +0000", "2026-07-22T07:01:06Z", "wwr: RFC-2822"),
            ("Wed, 22 Jul 2026 09:01:06 +0200", "2026-07-22T07:01:06Z", "RFC-2822 +0200 -2h"),
            ("2026-08-05", "2026-08-05T00:00:00Z", "date only"),
        ]
        for raw, want, why in cases:
            with self.subTest(why=why):
                self.assertEqual(to_utc(raw), want)

    def test_unusable_input_is_none_not_a_crash(self):
        for raw in (None, "", "   ", "not a date", {}, [], object()):
            with self.subTest(raw=repr(raw)):
                self.assertIsNone(to_utc(raw))

    def test_booleans_are_not_treated_as_unix_timestamps(self):
        """bool is a subclass of int; True would otherwise become 1970."""
        self.assertIsNone(to_utc(True))
        self.assertIsNone(to_utc(False))

    def test_output_is_always_lexicographically_sortable(self):
        """The whole point. Mixed offsets sorted as raw strings misorder:
        '2026-07-31T15:21:46-04:00' < '2026-07-31T16:00:00+00:00' as text,
        but the first is LATER in real time."""
        later_in_real_time = to_utc("2026-07-31T15:21:46-04:00")   # 19:21:46Z
        earlier = to_utc("2026-07-31T16:00:00+00:00")              # 16:00:00Z
        self.assertLess("2026-07-31T15:21:46-04:00", "2026-07-31T16:00:00+00:00")
        self.assertGreater(later_in_real_time, earlier)



class TestLocationBucket(unittest.TestCase):
    """Measured against 424 live rows on 2026-08-05.

    Including the raw location in the key gave 0 cross-source merges --
    the same job on two boards carries wildly different location text
    ('Anywhere in the World' vs 'Americas, Europe, Israel'). Dropping
    location entirely gave 3 cross-source merges but destroyed 7 genuinely
    distinct roles: Grafana Labs hires the same platform engineer in the
    UK, Spain AND Ireland. Bucketing gives 3 merges and 0 false ones.
    """

    def test_anywhere_synonyms_collapse(self):
        for raw in ("Anywhere in the World", "Worldwide", "Global",
                    "Remote", "Remote, Remote", "", None):
            with self.subTest(raw=repr(raw)):
                self.assertEqual(loc_bucket(raw), "anywhere")

    def test_multi_region_spread_is_anywhere(self):
        self.assertEqual(loc_bucket("Americas, Europe, Israel"), "anywhere")
        self.assertEqual(loc_bucket("Europe, North America, Latin America, APAC"), "anywhere")

    def test_work_mode_marker_is_stripped_before_the_anywhere_test(self):
        """'Sweden - Remote' is Sweden, not anywhere. Testing for the bare
        word 'remote' BEFORE stripping merges Sweden with Japan -- two
        real, distinct Peroptyx postings observed in the same payload."""
        self.assertEqual(loc_bucket("Sweden - Remote"), "sweden")
        self.assertEqual(loc_bucket("Japan - Remote"), "japan")
        self.assertNotEqual(loc_bucket("Sweden - Remote"), loc_bucket("Japan - Remote"))

    def test_real_places_survive_verbatim(self):
        self.assertEqual(loc_bucket("Lucerne, Switzerland"), "lucerne switzerland")
        self.assertEqual(loc_bucket("United Kingdom"), "united kingdom")

    def test_a_single_region_is_not_a_spread(self):
        """One region is a place; two or more is a spread. Collapsing a
        single region would merge every Europe-only job into 'anywhere'."""
        self.assertEqual(loc_bucket("Europe"), "europe")


class TestDedupeKey(unittest.TestCase):

    def test_german_gender_markers_do_not_split_a_job(self):
        """(m/w/d) is a German job-ad convention -- maennlich/weiblich/
        divers. The same posting appears with and without it across
        boards, so leaving it in splits one job into two."""
        self.assertEqual(dedupe_key("Acme", "Cloud Engineer (m/w/d)", "Berlin"),
                         dedupe_key("Acme", "Cloud Engineer", "Berlin"))

    def test_punctuation_and_case_do_not_split_a_job(self):
        self.assertEqual(dedupe_key("Lemon.io", "Senior DevOps Engineer", "Worldwide"),
                         dedupe_key("lemon io", "senior devops engineer", "Anywhere"))

    def test_same_role_in_different_cities_stays_distinct(self):
        """Roku posts the same counsel role in Cambridge and London. These
        are two applications, not one."""
        self.assertNotEqual(dedupe_key("Roku", "Senior Counsel", "Cambridge"),
                            dedupe_key("Roku", "Senior Counsel", "London"))

    def test_the_real_cross_source_duplicate_collapses(self):
        """Observed 2026-08-05: A.Team's role on Remotive and WWR."""
        self.assertEqual(
            dedupe_key("A.Team", "Senior Independent AI Engineer", "Americas, Europe, Israel"),
            dedupe_key("A.Team", "Senior Independent AI Engineer", "Anywhere in the World"))

    def test_key_is_stable_and_short(self):
        key = dedupe_key("Acme", "Engineer", "Berlin")
        self.assertEqual(key, dedupe_key("Acme", "Engineer", "Berlin"))
        self.assertEqual(len(key), 16)

if __name__ == "__main__":
    unittest.main()
