"""Normaliser tests, driven by trimmed real payloads captured 2026-08-05.

Fixtures keep the upstreams' real field names deliberately -- that is the
entire point. A normaliser tested against invented data proves only that
it agrees with the invention.
"""

import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import RSS_SOURCES, SOURCES, clean_text, strip_contacts, validate_schema  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name):
    source = SOURCES[name]
    path = FIXTURES / (name + (".xml" if name in RSS_SOURCES else ".json"))
    raw = path.read_bytes()
    payload = ET.fromstring(raw) if path.suffix == ".xml" else json.loads(raw)
    return source, payload


class TestEveryNormaliser(unittest.TestCase):
    """One assertion set applied to every source. A normaliser returning a dict
    of Nones is the failure mode that matters: it reads as "no new jobs"
    rather than as an error."""

    def test_every_source_has_a_fixture(self):
        self.assertEqual(len(SOURCES), 9)
        for name in SOURCES:
            with self.subTest(source=name):
                self.assertTrue((FIXTURES / (name + (".xml" if name in RSS_SOURCES
                                                     else ".json"))).exists())

    def test_every_source_yields_title_company_and_url(self):
        for name in SOURCES:
            with self.subTest(source=name):
                source, payload = load(name)
                rows = source.rows(payload)
                self.assertTrue(rows, f"{name}: no rows extracted from fixture")
                for raw in rows:
                    job = source.normalise(raw)
                    self.assertTrue(job["title"], f"{name}: empty title")
                    self.assertTrue(job["company"], f"{name}: empty company")
                    self.assertTrue(job["url"], f"{name}: empty url")

    def test_dates_are_utc_stamped_or_explicitly_absent(self):
        for name in SOURCES:
            with self.subTest(source=name):
                source, payload = load(name)
                for raw in source.rows(payload):
                    posted = source.normalise(raw)["posted_at"]
                    if posted is not None:
                        self.assertRegex(posted, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_pythonorg_carries_no_dates_at_all(self):
        """Verified 2026-08-05: python.org RSS <item>s have only title, link,
        description and guid -- no pubDate element exists. That is a real
        property of the feed, so it is asserted rather than worked around."""
        source, payload = load("pythonorg")
        self.assertTrue(all(source.normalise(r)["posted_at"] is None
                            for r in source.rows(payload)))


class TestSourceSpecificTraps(unittest.TestCase):
    """Each of these was found by running the normaliser against a real
    payload, not by reading documentation."""

    def test_remoteok_tos_object_is_not_emitted_as_a_job(self):
        source, payload = load("remoteok")
        self.assertIn("legal", payload[0], "fixture must retain the ToS object")
        self.assertNotIn(payload[0], source.rows(payload))

    def test_wwr_splits_company_out_of_the_title(self):
        """WWR titles are 'Company: Role'. Left unsplit every WWR company is
        empty and every title carries a prefix, so nothing dedupes."""
        source, payload = load("wwr")
        jobs = [source.normalise(r) for r in source.rows(payload)]
        self.assertTrue(all(job["company"] for job in jobs))
        self.assertFalse(any(job["title"].startswith(job["company"] + ":") for job in jobs))

    def test_pythonorg_takes_company_from_the_LAST_comma_group(self):
        """The title MUST contain two ', ' separators or this test is inert:
        with only one, partition and rpartition are identical and the guard
        cannot detect its own removal. Real feed titles observed on
        2026-08-05 all had exactly one, so this case is synthesised from the
        shape they take -- 'Senior Full-Stack Engineer [Full Time; 100%
        remote; US-only], Hive Collective' -- with a second comma added,
        which is the arrangement that actually breaks a first-comma split.
        """
        item = ET.fromstring(
            "<item><title>Senior Engineer, Platform Reliability, Hive Collective</title>"
            "<link>https://example.org/1/</link>"
            "<description>Warsaw (fully remote), Poland</description></item>")
        self.assertEqual(item.findtext("title").count(", "), 2,
                         "fixture must have two separators or the test is inert")
        job = SOURCES["pythonorg"].normalise(item)
        self.assertEqual(job["company"], "Hive Collective")
        self.assertEqual(job["title"], "Senior Engineer, Platform Reliability")

    def test_pythonorg_title_without_any_comma_keeps_the_whole_string(self):
        item = ET.fromstring(
            "<item><title>Python Developer</title><link>https://example.org/3/</link>"
            "<description>Berlin, Germany</description></item>")
        job = SOURCES["pythonorg"].normalise(item)
        self.assertEqual(job["title"], "Python Developer")
        self.assertIsNone(job["company"])

    def test_pythonorg_takes_location_from_the_description_first_line(self):
        item = ET.fromstring(
            "<item><title>Engineer, Acme</title><link>https://example.org/2/</link>"
            "<description>Warsaw (fully remote), Poland\nrest of the ad</description></item>")
        self.assertEqual(SOURCES["pythonorg"].normalise(item)["location"],
                         "Warsaw (fully remote), Poland")

    def test_4dayweek_picks_the_PRIMARY_location_not_the_first(self):
        """Synthesised, and it has to be: every real fixture row carries
        exactly ONE location, so next(is_primary) and places[0] are
        indistinguishable there and the selection is unguarded. A
        multi-location row with the primary listed second is the only shape
        that can tell them apart.
        """
        raw = {"id": "x", "title": "Platform Engineer", "url": "https://x/1",
               "posted_at": "2026-08-05T00:00:00Z", "company": {"name": "Acme"},
               "locations": [
                   {"city": "Bengaluru", "country": "India", "is_primary": False},
                   {"city": "Berlin", "country": "Germany", "is_primary": True},
               ]}
        job = SOURCES["4dayweek"].normalise(raw)
        self.assertEqual(job["location"], "Berlin, Germany")

    def test_4dayweek_falls_back_to_the_first_location_when_none_is_primary(self):
        raw = {"id": "x", "title": "Platform Engineer", "url": "https://x/1",
               "posted_at": "2026-08-05T00:00:00Z", "company": {"name": "Acme"},
               "locations": [{"city": "Lisbon", "country": "Portugal"}]}
        self.assertEqual(SOURCES["4dayweek"].normalise(raw)["location"],
                         "Lisbon, Portugal")

    def test_4dayweek_with_no_locations_at_all_is_not_a_crash(self):
        raw = {"id": "x", "title": "Platform Engineer", "url": "https://x/1",
               "posted_at": "2026-08-05T00:00:00Z", "company": {"name": "Acme"},
               "locations": []}
        self.assertIsNone(SOURCES["4dayweek"].normalise(raw)["location"])

    def test_4dayweek_reads_locations_plural_not_location(self):
        """4dayweek has no `location` key. It has `locations`, a list of
        dicts carrying an is_primary flag."""
        source, payload = load("4dayweek")
        self.assertNotIn("location", source.rows(payload)[0])
        self.assertTrue(all(source.normalise(r)["location"] for r in source.rows(payload)))

    def test_arbeitnow_remote_flag_is_a_real_boolean(self):
        source, payload = load("arbeitnow")
        for raw in source.rows(payload):
            self.assertIsInstance(source.normalise(raw)["remote"], bool)


class TestContactStripping(unittest.TestCase):
    """GDPR: job ads routinely name a recruiter and give a direct email or
    phone number. Storing those makes the operator a controller for third
    party personal data, so they are removed at ingest -- before anything
    is written -- rather than filtered at display time."""

    def test_email_addresses_are_removed(self):
        cleaned = strip_contacts("Send your CV to anna.schmidt@acme-recruiting.de today")
        self.assertNotIn("anna.schmidt@acme-recruiting.de", cleaned)
        self.assertIn("[contact removed]", cleaned)

    def test_international_phone_numbers_are_removed(self):
        for raw in ("+49 151 23456789", "+44 20 7946 0958", "0049-151-23456789"):
            with self.subTest(raw=raw):
                self.assertNotIn(raw, strip_contacts(f"Call {raw} to apply"))

    def test_ordinary_prose_survives_untouched(self):
        """Over-stripping would gut the descriptions the report shows."""
        text = ("We run 12 services on Kubernetes 1.29 and want 5+ years "
                "of experience. Salary 80,000-95,000 EUR.")
        self.assertEqual(strip_contacts(text), text)

    def test_none_and_empty_are_safe(self):
        self.assertIsNone(strip_contacts(None))
        self.assertEqual(strip_contacts(""), "")

    def test_every_normalised_description_is_stripped(self):
        """The guard has to be applied by the normalisers, not merely
        available to them."""
        for name in SOURCES:
            with self.subTest(source=name):
                source, payload = load(name)
                for raw in source.rows(payload):
                    description = source.normalise(raw)["description"] or ""
                    self.assertNotRegex(description, r"[\w.+-]+@[\w-]+\.[\w.]+")


class TestSchemaDrift(unittest.TestCase):
    """Eight upstreams, no CI in this repo, and a renamed field yields FEWER
    ROWS rather than an error -- which reads as "no new jobs today". The
    design council's red team named this the real risk, above the HTTP
    client choice. So a drifted source is rejected wholesale and reported,
    never half-parsed into rows full of silent Nones.
    """

    def healthy_row(self):
        return {"slug": "a", "title": "T", "company_name": "C", "location": "L",
                "remote": True, "created_at": 1785930923, "url": "u"}

    def test_a_healthy_payload_is_accepted_whole(self):
        accepted, reason = validate_schema(SOURCES["arbeitnow"], [self.healthy_row()])
        self.assertIsNone(reason)
        self.assertEqual(len(accepted), 1)

    def test_a_missing_required_key_rejects_every_row_and_names_the_field(self):
        row = self.healthy_row()
        del row["created_at"]
        accepted, reason = validate_schema(SOURCES["arbeitnow"], [row])
        self.assertEqual(accepted, [])
        self.assertIn("created_at", reason)
        self.assertIn("schema-drift", reason)

    def test_several_missing_keys_are_all_named_and_sorted(self):
        row = self.healthy_row()
        del row["created_at"], row["url"]
        _, reason = validate_schema(SOURCES["arbeitnow"], [row])
        self.assertIn("created_at, url", reason)

    def test_an_added_key_is_tolerated(self):
        """Upstreams add fields routinely; that is not a failure."""
        row = dict(self.healthy_row(), brand_new_field=1)
        accepted, reason = validate_schema(SOURCES["arbeitnow"], [row])
        self.assertIsNone(reason)
        self.assertEqual(len(accepted), 1)

    def test_an_empty_payload_is_not_drift(self):
        """A feed legitimately returning nothing must not be reported as
        broken -- that cries wolf on a quiet day and trains you to ignore
        the one time it matters."""
        accepted, reason = validate_schema(SOURCES["arbeitnow"], [])
        self.assertEqual(accepted, [])
        self.assertIsNone(reason)

    def test_sources_with_no_declared_keys_skip_validation(self):
        """RSS sources have no dict to inspect; their normalisers validate."""
        sentinel = object()
        accepted, reason = validate_schema(SOURCES["wwr"], [sentinel])
        self.assertIsNone(reason)
        self.assertEqual(accepted, [sentinel])

    def test_every_real_fixture_passes_its_own_declared_schema(self):
        """If a fixture failed this, the declared key set would be wrong --
        the guard would fire on healthy data and the source would look
        permanently degraded."""
        for name in SOURCES:
            with self.subTest(source=name):
                source, payload = load(name)
                _, reason = validate_schema(source, source.rows(payload))
                self.assertIsNone(reason, f"{name}: {reason}")


class TestCleanText(unittest.TestCase):
    """Two upstream data defects, both observed live on 2026-08-05 in the
    Remote OK payload, both of which reach the report as visible garbage."""

    def test_html_entities_are_decoded(self):
        """Remote OK ships HTML-escaped text: 'Food &amp; Beverage
        Positions'. Stored raw it renders as '&amp;' on the page, because
        the report escapes it a second time."""
        self.assertEqual(clean_text("Food &amp; Beverage"), "Food & Beverage")
        self.assertEqual(clean_text("Caf&eacute; &#8212; Berlin"), "Café — Berlin")

    def test_double_encoded_utf8_is_repaired(self):
        """Remote OK double-encodes non-Latin locations: UTF-8 bytes decoded
        as Latin-1 and re-encoded. Verified recoverable by round trip."""
        self.assertEqual(clean_text("Ø¯Ø¨Ù\x8a"), "دبي")
        self.assertEqual(clean_text("Launch â\x80\x94 99 Seconds"), "Launch — 99 Seconds")

    def test_legitimate_non_ascii_is_NOT_corrupted(self):
        """The guard that makes the repair safe. A blind latin-1 round trip
        would mangle Nordic and German names; these must fail it and be
        left exactly as they are."""
        for text in ("Ørsted", "Ålesund, Norway", "München, Germany", "Zürich",
                     "Café", "naïve — dash", "دبي", "東京"):
            with self.subTest(text=text):
                self.assertEqual(clean_text(text), text)

    def test_plain_ascii_is_unchanged(self):
        self.assertEqual(clean_text("San Francisco, United States"),
                         "San Francisco, United States")

    def test_none_and_empty_are_safe(self):
        self.assertIsNone(clean_text(None))
        self.assertEqual(clean_text(""), "")

    def test_entities_are_decoded_in_real_fixture_titles(self):
        """Applied by the normalisers, not merely available to them."""
        for name in SOURCES:
            with self.subTest(source=name):
                source, payload = load(name)
                for raw in source.rows(payload):
                    job = source.normalise(raw)
                    for field in ("title", "company", "location"):
                        value = job[field] or ""
                        self.assertNotIn("&amp;", value)
                        self.assertNotIn("&#", value)

    def test_no_mojibake_survives_in_real_fixtures(self):
        for name in SOURCES:
            with self.subTest(source=name):
                source, payload = load(name)
                for raw in source.rows(payload):
                    location = source.normalise(raw)["location"] or ""
                    self.assertNotIn("Ã", location)
                    self.assertNotIn("Ø¯Ø¨", location)


if __name__ == "__main__":
    unittest.main()
