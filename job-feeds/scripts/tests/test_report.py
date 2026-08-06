"""HTML report. Job posts are user-submitted, so every field is untrusted."""

import html
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import report  # noqa: E402
from job_feeds import load_config  # noqa: E402

HOSTILE_TITLE = "<script>XT1</script>"
# BOTH quote characters, deliberately. This module writes single-quoted
# attributes, so a double quote alone cannot break out of one -- a fixture
# carrying only `"` leaves html.escape(quote=True) untestable, and dropping
# quote=True then passes the whole suite while a `'` payload escapes live.
HOSTILE_COMPANY = "\"XC2 onmouseover=\"alert(1) ' onmouseover='alert(2)"
HOSTILE_LOCATION = "<b>XL3</b>"
HOSTILE_GENERATED_AT = "<script>XG4</script>"

CONFIG_DATA = {
    "defaults": {"window": 14, "exclude_company": ["<b>XE5</b>"]},
    "lanes": [{"name": "<script>XN6</script>", "label": "<b>XA7</b>",
               "match": "xt1|engineer"}],
    "highlight": ["terragrunt"],
}


def build_config():
    tmp = tempfile.mkdtemp()
    path = Path(tmp) / "config.json"
    path.write_text(json.dumps(CONFIG_DATA), encoding="utf-8")
    return load_config(path)


CONFIG = build_config()


def hostile_row(**overrides):
    row = {"title": HOSTILE_TITLE, "company": HOSTILE_COMPANY,
           "location": HOSTILE_LOCATION, "url": "https://example.org/1",
           "posted_at": None, "source": "remoteok", "lanes": ["<b>XA7</b>"],
           "highlight": True, "also_seen_on": "wwr", "remote": 1,
           "description": "</div><img src=x onerror=alert(1)>XD8", "salary": None,
           "first_seen": "2026-08-05T12:00:00Z"}
    row.update(overrides)
    return row


class TestEscaping(unittest.TestCase):
    """This exact bug already bit li_report.py once: html.escape does NOT
    escape spaces, so an unquoted attribute accepts an injected event
    handler even though the value was 'escaped'."""

    @classmethod
    def setUpClass(cls):
        cls.doc = report.render_html([hostile_row()], CONFIG, 14, [],
                                     HOSTILE_GENERATED_AT)

    def test_no_live_script_tag_from_a_title(self):
        self.assertNotIn(HOSTILE_TITLE, self.doc)
        self.assertIn(html.escape(HOSTILE_TITLE, quote=True), self.doc)

    def test_exactly_one_script_tag_the_reports_own(self):
        self.assertEqual(self.doc.count("<script>"), 1)
        self.assertEqual(self.doc.count("<script "), 0)

    def test_company_cannot_break_out_of_a_quoted_attribute(self):
        # The single-quote form is the one that matters: this module writes
        # single-quoted attributes, so `' onmouseover='` is the live vector
        # and `" onmouseover="` is merely inert text inside them.
        self.assertNotIn("' onmouseover='", self.doc)
        self.assertNotIn('"XC2 onmouseover="', self.doc)
        self.assertIn(html.escape(HOSTILE_COMPANY, quote=True), self.doc)

    def test_the_generated_at_stamp_is_escaped(self):
        self.assertNotIn(HOSTILE_GENERATED_AT, self.doc)

    def test_a_hostile_lane_label_is_escaped(self):
        self.assertNotIn("<b>XA7</b>", self.doc)

    def test_footer_lane_names_and_exclusions_are_escaped(self):
        """Operator-controlled values from config.json. Low risk, but the
        module claims they are escaped defensively, so that claim is
        tested rather than asserted in a docstring."""
        footer = self.doc.split("<footer>", 1)[1]
        self.assertNotIn("<script>XN6</script>", footer)
        self.assertNotIn("<b>XE5</b>", footer)

    def test_every_attribute_in_the_output_is_quoted(self):
        """Guards the defect CLASS, not one instance of it.

        A naive regex is wrong here: it matches '=' inside a quoted value
        (content='width=device-width') and reports false positives. This
        walks each tag tracking quote state, so only a '=' at attribute
        position -- outside any quoted value -- is examined.
        """
        offenders = []
        for tag in re.findall(r"<([a-zA-Z][^>]*)>", self.doc):
            quote = None
            index = 0
            while index < len(tag):
                char = tag[index]
                if quote:
                    if char == quote:
                        quote = None
                elif char in "\"'":
                    quote = char
                elif char == "=":
                    following = tag[index + 1:index + 2]
                    if following not in ("\"", "'"):
                        offenders.append(tag[:60])
                        break
                index += 1
        self.assertEqual(offenders, [], f"unquoted attributes: {offenders[:3]}")

    def test_the_quoting_check_actually_detects_an_unquoted_attribute(self):
        """The check above is intricate enough to be wrong silently, so it
        is verified against a document known to contain the defect."""
        bad = "<html><body><a href=https://evil onmouseover=alert(1)>x</a></body></html>"
        offenders = []
        for tag in re.findall(r"<([a-zA-Z][^>]*)>", bad):
            quote = None
            index = 0
            while index < len(tag):
                char = tag[index]
                if quote:
                    if char == quote:
                        quote = None
                elif char in "\"'":
                    quote = char
                elif char == "=" and tag[index + 1:index + 2] not in ("\"", "'"):
                    offenders.append(tag)
                    break
                index += 1
        self.assertTrue(offenders, "the detector failed to spot an unquoted attribute")

    def test_a_row_with_no_description_still_escapes_its_title(self):
        """The title renders through two branches. Testing only the linked
        one leaves the other free to emit raw HTML."""
        doc = report.render_html([hostile_row(description=None)], CONFIG, 14, [], "x")
        self.assertNotIn(HOSTILE_TITLE, doc)


class TestAttribution(unittest.TestCase):
    """Remote OK requires attribution and a dofollow backlink as a condition
    of API access; Arbeitnow's meta.terms asks the same. These are access
    conditions, so they are asserted, not left to review."""

    def test_attribution_appears_for_a_source_that_is_present(self):
        doc = report.render_html([hostile_row(source="remoteok")], CONFIG, 14, [], "x")
        self.assertIn("remoteok.com", doc)

    def test_the_backlink_is_dofollow(self):
        doc = report.render_html([hostile_row(source="remoteok")], CONFIG, 14, [], "x")
        footer = doc.split("<footer>", 1)[1]
        self.assertIn("remoteok.com", footer)
        self.assertNotIn("nofollow", footer)

    def test_attribution_is_omitted_for_a_source_with_no_rows(self):
        doc = report.render_html([hostile_row(source="wwr", also_seen_on="")],
                                 CONFIG, 14, [], "x")
        self.assertNotIn("remoteok.com", doc)

    def test_a_source_reached_only_via_also_seen_on_is_still_credited(self):
        """The row is attributed to wwr but was also found on remoteok --
        Remote OK's terms still apply to the data shown."""
        doc = report.render_html([hostile_row(source="wwr", also_seen_on="remoteok")],
                                 CONFIG, 14, [], "x")
        self.assertIn("remoteok.com", doc)


class TestSelfContained(unittest.TestCase):

    def test_no_external_asset_references(self):
        doc = report.render_html([hostile_row()], CONFIG, 14, [], "x")
        for marker in ("cdn.", "<link rel=\"stylesheet\"", "src=\"http", "@import"):
            self.assertNotIn(marker, doc)

    def test_render_is_byte_identical_across_calls(self):
        first = report.render_html([hostile_row()], CONFIG, 14, [], "fixed")
        second = report.render_html([hostile_row()], CONFIG, 14, [], "fixed")
        self.assertEqual(first, second)

    def test_render_html_never_reads_the_clock(self):
        """Determinism has to be structural. The stamp is passed in; a
        module that also calls datetime.now would be untestable and would
        produce a different file from identical inputs."""
        class _Tripwire:
            def __getattr__(self, name):
                raise AssertionError(
                    f"render_html read the clock via datetime.{name} — the "
                    f"generated_at stamp must be passed in")

        real = report.datetime
        report.datetime = _Tripwire()
        try:
            report.render_html([hostile_row()], CONFIG, 14, [], "fixed")
        finally:
            report.datetime = real

    def test_an_empty_result_set_still_produces_a_valid_document(self):
        doc = report.render_html([], CONFIG, 14, [], "x")
        self.assertIn("<!doctype html>", doc.lower())
        self.assertIn("</html>", doc)

    def test_undated_rows_render_no_fabricated_date(self):
        doc = report.render_html([hostile_row(posted_at=None)], CONFIG, 14, [], "x")
        self.assertNotIn("1970", doc)
        self.assertNotIn("None", doc)


class TestStickyHeaderLayout(unittest.TestCase):
    """The sticky table header overlapped the first two data rows instead of
    sitting above them. Three causes, and the first is the one that
    actually broke it:

      1. `overflow:hidden` on the table -- added for rounded corners, but
         an overflow-clipped ancestor disables position:sticky on its
         descendants entirely. This is the classic trap.
      2. `th{top:3rem}` was a magic number. The controls bar is taller
         than that AND wraps on narrow screens, so no constant is correct.
      3. `th` had no z-index, so it did not reliably paint over rows.

    These are asserted on the generated CSS rather than on a rendering,
    because a screenshot cannot be diffed in CI -- but each assertion
    names the specific rule that caused the visible bug.
    """

    @classmethod
    def setUpClass(cls):
        cls.doc = report.render_html([hostile_row()], CONFIG, 14, [], "x")
        cls.css = cls.doc.split("<style>", 1)[1].split("</style>", 1)[0]

    def rule(self, selector):
        """Body of the rule whose selector list is exactly `selector`.

        Comments are stripped first and the selector list is compared
        exactly: a naive prefix match returns the `th,td` rule when asked
        for `th`, and breaks entirely once a comment precedes a rule.
        """
        css = re.sub(r"/\*.*?\*/", "", self.css, flags=re.S)
        for block in css.split("}"):
            if "{" not in block:
                continue
            head, _, body = block.partition("{")
            if [part.strip() for part in head.split(",")] == [selector]:
                return body
        return ""

    def test_the_rule_helper_finds_the_right_block(self):
        """This helper is fiddly enough to be silently wrong, which would
        make every assertion below vacuous."""
        self.assertIn("position:sticky", self.rule("th"))
        self.assertNotIn("position:sticky", self.rule("th,td"))
        self.assertEqual(self.rule("nosuchselector"), "")

    def test_the_table_does_not_clip_overflow(self):
        """An overflow-clipped ancestor silently disables sticky on the
        header inside it."""
        self.assertNotIn("overflow:hidden", self.rule("table"))

    def test_the_sticky_header_offset_is_not_a_hardcoded_length(self):
        """The controls bar wraps, so its height is not knowable at author
        time. The offset must come from a variable the page can update."""
        th = self.rule("th")
        self.assertIn("position:sticky", th)
        self.assertIn("var(--controls-h", th)

    def test_the_header_paints_below_the_controls_but_above_rows(self):
        controls_z = int(self.rule(".controls").split("z-index:")[1].split(";")[0])
        header_z = int(self.rule("th").split("z-index:")[1].split(";")[0])
        self.assertLess(header_z, controls_z, "header must not cover the filter bar")
        self.assertGreater(header_z, 0, "header must paint above table rows")

    def test_the_page_measures_the_controls_height_at_runtime(self):
        js = self.doc.split("<script>", 1)[1].split("</script>", 1)[0]
        self.assertIn("--controls-h", js)
        self.assertIn("resize", js, "a wrapping controls bar changes height on resize")

    def test_a_fallback_offset_exists_if_the_script_never_runs(self):
        """Printing, or a JS error, must not leave the header pinned at 0."""
        self.assertRegex(self.rule("th"), r"var\(--controls-h,\s*[\d.]+rem\)")


if __name__ == "__main__":
    unittest.main()


class TestUndatedRowsShowWhenWeFirstSawThem(unittest.TestCase):
    """Three sources publish no dates at all, so those rows rendered as a
    bare em-dash forever and a reader could not tell a fresh posting from a
    stale one. first_seen answers it — it is the reason SQLite is in this
    project — and it was simply never surfaced.

    It must never be presented AS a posting date. "Seen 2 days ago" is a
    fact about us; claiming it as a publication date would be inventing
    data, which this project refuses elsewhere.
    """

    def render(self, **overrides):
        return report.render_html([hostile_row(**overrides)], CONFIG, 14, [], "x")

    def test_an_undated_row_shows_how_long_ago_we_first_saw_it(self):
        doc = self.render(posted_at=None, seen_days=2)
        self.assertIn("seen 2d", doc)

    def test_it_is_labelled_seen_not_posted(self):
        """The whole safety of this feature is the label. Without it the
        column silently mixes two different facts."""
        doc = self.render(posted_at=None, seen_days=2)
        self.assertIn("seen", doc)
        self.assertIn("&mdash;", doc, "the empty posting date must still show as a dash")

    def test_today_reads_as_today_not_zero_days(self):
        doc = self.render(posted_at=None, seen_days=0)
        self.assertIn("seen today", doc)
        self.assertNotIn("seen 0d", doc)

    def test_a_dated_row_is_unaffected(self):
        """The age is a fallback, not a replacement. A row with a real
        publication date must not gain a second, competing date."""
        doc = self.render(posted_at="2026-08-01T00:00:00Z", seen_days=9)
        self.assertIn("2026-08-01", doc)
        self.assertNotIn("seen 9d", doc)

    def test_an_undated_row_with_no_first_seen_still_renders_a_dash(self):
        """Belt and braces: a row from before this field existed, or one
        whose first_seen failed to parse, must not crash or print None."""
        doc = self.render(posted_at=None, seen_days=None)
        self.assertIn("&mdash;", doc)
        self.assertNotIn("None", doc)
        self.assertNotIn("seen", doc.split("<tbody>")[1].split("</tbody>")[0])
