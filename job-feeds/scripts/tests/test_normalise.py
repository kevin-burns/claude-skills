"""Stdlib-only tests for job-feeds normalisation. No network, no live feeds."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import to_utc  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
