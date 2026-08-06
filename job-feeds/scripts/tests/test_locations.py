"""The location breakdown: where the fetched rows actually are. No network.

Guards claude-skills-atj. A Spain-based test install fetched 1,321 rows of
which two mentioned Spain, neither a data role -- and nothing in the output
said so. The digest looked like it had worked. These tests exist because the
fix is a REPORTING feature, and a reporting feature that quietly omits rows
reproduces the defect it was written to expose.
"""

import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from job_feeds import (  # noqa: E402
    LOC_LIMIT, Store, location_counts, main)

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)

CONFIG = {
    "defaults": {"window": 14},
    "lanes": [{"name": "platform", "label": "Platform", "match": "platform|sre"}],
    "highlight": [],
    "sources": {},
}


class LocationCase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def write(self, data=None, name="config.json"):
        path = self.tmp / name
        path.write_text(json.dumps(data or CONFIG), encoding="utf-8")
        return path

    def seed(self, db, rows, source="arbeitnow"):
        """rows: (location, title) or (location, title, remote) tuples.

        Its own seeder, deliberately. test_cli.py's hardcodes
        location=f"City{i}" and remote=True, and cannot express the None
        location, the duplicate spellings, or the NULL remote flag that the
        tests below turn on. An earlier version of this one hardcoded
        remote=True too, which made the --remote test pass whether or not
        the flag was honoured -- it could not fail, so it proved nothing.
        """
        store = Store(db)
        entries = []
        for i, row in enumerate(rows):
            location, title = row[0], row[1]
            remote = row[2] if len(row) > 2 else True
            entries.append({"title": title, "company": f"Co{i}",
                            "location": location, "remote": remote,
                            "posted_at": "2026-08-04T00:00:00Z",
                            "url": f"https://x/{source}{i}",
                            "description": "", "tags": [], "salary": None,
                            "source": source})
        store.upsert(entries, NOW)
        return db

    def run_cli(self, *argv, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), out=out, err=err, now=NOW, **kwargs)
        return code, out.getvalue(), err.getvalue()

    def locations(self, db, *extra):
        return self.run_cli("locations", "--config", str(self.write()),
                            "--db", str(db), *extra)


def rows_with(*locations):
    return [{"location": value} for value in locations]


class TestCounting(LocationCase):

    def test_two_spellings_of_the_same_string_are_ONE_line(self):
        """Measured: 'remote' is 48 rows on the live corpus. Reporting the
        two casings apart splits the largest non-city group into 33 and 15,
        pushing both out of the top five and hiding the fact that a
        meaningful slice of the corpus states no place at all."""
        counts = dict(location_counts(rows_with("Remote", "Remote", "Remote",
                                                "remote", "remote")))
        self.assertEqual(counts, {"Remote": 5})

    def test_the_displayed_spelling_does_not_depend_on_row_order(self):
        """Two rows each way, so frequency cannot break the tie. Without the
        lexicographic tie-break the label follows dict insertion order, which
        follows ORDER BY posted_at DESC -- and the same corpus renders a
        different word on the next run."""
        first = location_counts(rows_with("Berlin", "Berlin", "berlin", "berlin"))
        second = location_counts(rows_with("berlin", "berlin", "Berlin", "Berlin"))
        self.assertEqual(first, second)
        self.assertEqual(first[0][0], "Berlin")

    def test_a_missing_location_is_its_own_line_and_is_never_called_anywhere(self):
        """None, '' and '   ' are the same fact: this row states no place.
        Calling loc_bucket on the display path would label all three
        'anywhere' -- an inference the data does not support, and one that
        would silently absorb the 12 unplaced rows on the live corpus."""
        counts = dict(location_counts(rows_with(None, "", "   ")))
        self.assertEqual(counts, {"(none)": 3})
        self.assertNotIn("anywhere", counts)

    def test_the_breakdown_shows_the_STORED_string_not_the_dedupe_bucket(self):
        """The tripwire against a future tidy-up that reuses loc_bucket:
        loc_bucket('Remote job') == 'job', because the work-mode regex strips
        'remote' and leaves the noise word. Eight real rows say 'Remote job'.
        A bucket literally named 'job' is proof that function was never meant
        to carry geographic meaning."""
        counts = dict(location_counts(rows_with("Remote job", "Remote job")))
        self.assertEqual(counts, {"Remote job": 2})
        self.assertNotIn("job", counts)

    def test_ordering_is_by_count_then_label(self):
        counts = location_counts(rows_with("Berlin", "Berlin", "Aachen", "Zurich"))
        self.assertEqual(counts, [("Berlin", 2), ("Aachen", 1), ("Zurich", 1)])


class TestTheCommand(LocationCase):

    def test_the_counts_and_the_tail_line_sum_to_the_row_count(self):
        """Measured: the top 20 is 58.4% of the corpus and the tail carries
        550 rows. A truncated list with no tail line loses 42% of the data
        while looking complete."""
        db = self.tmp / "j.db"
        pairs = [(f"Place{i:02d}", "Platform Engineer") for i in range(LOC_LIMIT + 5)]
        self.seed(db, pairs + [(None, "SRE"), (None, "SRE Two")])
        code, out, _ = self.locations(db)
        self.assertEqual(code, 0)
        self.assertIn(f"{len(pairs) + 2} row(s)", out)
        self.assertIn("other value(s)", out)
        shown = sum(int(line.split()[-2]) for line in out.splitlines()
                    if line.startswith("  ") and "%" in line)
        self.assertEqual(shown, len(pairs) + 2,
                         "head + tail must reconcile to the row count")

    def test_json_is_complete_and_untruncated(self):
        """The only surface on which a rare location is reachable. On the
        live corpus the two Spain rows sit in a 326-entry tail; applying
        LOC_LIMIT here would hide them and pass every other test in this
        file."""
        db = self.tmp / "j.db"
        pairs = [(f"Place{i:02d}", "Platform Engineer") for i in range(LOC_LIMIT + 5)]
        self.seed(db, pairs + [(None, "SRE")])
        code, out, _ = self.locations(db, "--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(len(payload), LOC_LIMIT + 6)
        self.assertIn(None, [entry["location"] for entry in payload],
                      "an unplaced row must serialise as JSON null, not '(none)'")

    def test_locations_warns_and_ignores_remote_rather_than_honouring_it(self):
        """--remote is `AND remote = 1` in raw SQL, and NULL = 1 is NULL,
        which is falsy -- so it silently discards every row with no flag (20
        of 1,323, all python.org). A completeness report must not inherit a
        filter that loses a whole source. Warn, do not refuse: ignoring the
        flag silently would be the same defect class we are fixing."""
        db = self.tmp / "j.db"
        # The third row carries a NULL remote flag -- 20 real rows do, all
        # python.org. Honouring --remote drops it, because `AND remote = 1`
        # yields NULL for NULL and NULL is falsy in SQL. Seeding every row
        # remote=True (as an earlier version of this test did) makes the
        # assertion pass whether or not the flag is honoured.
        self.seed(db, [("Berlin", "Platform Engineer", True),
                       ("Madrid", "SRE", False),
                       ("Lisbon", "Platform Lead", None)])
        code, out, err = self.locations(db, "--remote")
        self.assertEqual(code, 0)
        self.assertIn("--remote", err)
        for place in ("Berlin", "Madrid", "Lisbon"):
            self.assertIn(place, out, "no row may be dropped by a flag we ignore")

    def test_locations_states_the_window_it_is_reporting_on(self):
        """A user told they are seeing 'what was fetched', while actually
        seeing a time-filtered subset, is the same confident-wrong shape as
        the original bug."""
        db = self.tmp / "j.db"
        self.seed(db, [("Berlin", "Platform Engineer")])
        _, out, _ = self.locations(db)
        self.assertIn("day(s) window", out.replace("-day window", " day(s) window"))

    def test_an_empty_store_says_so_and_exits_0(self):
        db = self.tmp / "j.db"
        Store(db)
        code, out, err = self.locations(db)
        self.assertEqual(code, 0)
        self.assertEqual(out, "", "no table for an empty store")
        self.assertIn("nothing fetched yet", err)

    def test_the_per_source_line_shows_which_feed_dominates(self):
        """The corpus is German because ONE source is 78% of it. Without the
        split, 'lots of Berlin' looks like a market fact rather than a
        sourcing artefact."""
        db = self.tmp / "j.db"
        self.seed(db, [("Berlin", "Platform Engineer"), ("Berlin", "SRE")])
        self.seed(db, [("London", "Platform Lead")], source="wwr")
        _, out, _ = self.locations(db)
        self.assertIn("arbeitnow 2", out)
        self.assertIn("wwr 1", out)

    def test_the_locations_command_is_registered_and_documented(self):
        """TestDocDrift only scans `--flag` tokens, so a bare subcommand that
        is documented but unregistered -- or registered but undocumented --
        passes every other check. That is the shape of the `location_filter`
        defect, one level up."""
        code, _, _ = self.run_cli("locations", "--config", str(self.write()),
                                  "--db", str(self.tmp / "absent.db"))
        self.assertEqual(code, 0, "'locations' must be a registered command")
        skill = (Path(__file__).resolve().parents[2] / "SKILL.md").read_text()
        self.assertIn("jfeeds locations", skill)


class TestTheDigestOneLiner(LocationCase):

    def test_the_digest_names_where_its_rows_are_including_under_json(self):
        """Always on and short, because a visibility feature you must
        remember to request does not fix a defect whose signature is that it
        looked like it worked. stderr, so `digest --json | jq` still parses
        -- and --json is precisely the surface carrying no aggregate today."""
        db = self.tmp / "j.db"
        self.seed(db, [("Berlin", "Platform Engineer"), ("Berlin", "SRE"),
                       ("Madrid", "Platform Lead")])
        for extra in ([], ["--json"]):
            with self.subTest(mode=extra or ["table"]):
                _, out, err = self.run_cli("digest", "--config", str(self.write()),
                                           "--db", str(db), *extra)
                self.assertIn("where:", err)
                self.assertIn("Berlin (2)", err)
                if extra:
                    json.loads(out)  # stdout must stay machine-readable

    def test_the_one_liner_counts_shown_rows_not_fetched_rows(self):
        """Placed after the lane drop on purpose. Before it, the line would
        describe rows the user is never going to see -- on the live corpus
        that is 1,145 of 1,323, which would make the summary actively
        misleading rather than merely noisy."""
        db = self.tmp / "j.db"
        self.seed(db, [("Berlin", "Platform Engineer"),
                       ("Reykjavik", "Chief Financial Officer")])
        _, _, err = self.run_cli("digest", "--config", str(self.write()),
                                 "--db", str(db))
        # claude-skills-302 added the denominators. The numerator is still
        # the shown-row count, which is what this test exists to hold: "1 of
        # 2" must not drift into "2 of 2" by counting the corpus twice.
        self.assertIn("1 of 2 row(s)", err)
        self.assertIn("where: Berlin (1)", err)
        self.assertNotIn("Reykjavik", err)

    def test_an_empty_digest_points_at_the_breakdown_instead_of_dead_ending(self):
        """The literal end state for a user outside the German market with
        tight lanes: rows in the store, none matching. Without this they are
        told 'nothing matched' and have no next move."""
        db = self.tmp / "j.db"
        self.seed(db, [("Madrid", "Chief Financial Officer")])
        _, _, err = self.run_cli("digest", "--config", str(self.write()),
                                 "--db", str(db))
        self.assertIn("nothing matched", err)
        self.assertIn("jfeeds locations", err)
        self.assertIn("1 row(s) in the window", err)

    def test_no_where_line_when_there_is_nothing_to_describe(self):
        db = self.tmp / "j.db"
        self.seed(db, [("Madrid", "Chief Financial Officer")])
        _, _, err = self.run_cli("digest", "--config", str(self.write()),
                                 "--db", str(db))
        self.assertNotIn("where:", err)


if __name__ == "__main__":
    unittest.main()
