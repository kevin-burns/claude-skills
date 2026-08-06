"""Config, lane matching and the CLI contract. No network."""

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import SOURCES  # noqa: E402
from job_feeds import (  # noqa: E402
    ConfigError, Store, attach_seen_age, is_excluded, is_highlighted,
    lanes_for, load_config, main)

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)

GOOD_CONFIG = {
    "defaults": {"window": 14, "exclude_company": ["randstad"],
                 "exclude_title": ["recruiter", "werkstudent"]},
    "lanes": [{"name": "platform", "label": "Platform",
               "match": "platform|terraform|kubernetes"},
              {"name": "em", "label": "EM", "match": "engineering manager|tech lead"}],
    "highlight": ["terragrunt", "finops"],
    "sources": {"arbeitnow": {"enabled": True}, "jobicy": {"enabled": False}},
}


class ConfigCase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def write(self, data, name="config.json"):
        path = self.tmp / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path


class TestLoadConfig(ConfigCase):

    def test_a_valid_config_loads(self):
        config = load_config(self.write(GOOD_CONFIG))
        self.assertEqual([lane.name for lane in config.lanes], ["platform", "em"])
        self.assertEqual(config.window, 14)
        self.assertEqual(config.exclude_companies, ("randstad",))

    def test_a_missing_file_names_the_path(self):
        with self.assertRaises(ConfigError) as caught:
            load_config(self.tmp / "nope.json")
        self.assertIn("nope.json", str(caught.exception))

    def test_invalid_json_names_the_path(self):
        path = self.tmp / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ConfigError) as caught:
            load_config(path)
        self.assertIn("bad.json", str(caught.exception))

    def test_an_invalid_regex_names_the_lane(self):
        """Without the lane name you get a bare 're.error: missing )' and no
        idea which of eight lanes to fix."""
        bad = json.loads(json.dumps(GOOD_CONFIG))
        bad["lanes"][0]["match"] = "([unclosed"
        with self.assertRaises(ConfigError) as caught:
            load_config(self.write(bad))
        self.assertIn("platform", str(caught.exception))

    def test_no_lanes_is_a_config_error(self):
        bad = json.loads(json.dumps(GOOD_CONFIG))
        bad["lanes"] = []
        with self.assertRaises(ConfigError):
            load_config(self.write(bad))

    def test_duplicate_lane_names_are_rejected(self):
        bad = json.loads(json.dumps(GOOD_CONFIG))
        bad["lanes"].append(dict(bad["lanes"][0]))
        with self.assertRaises(ConfigError) as caught:
            load_config(self.write(bad))
        self.assertIn("platform", str(caught.exception))

    def test_a_lane_missing_a_field_is_rejected(self):
        for field in ("name", "label", "match"):
            with self.subTest(field=field):
                bad = json.loads(json.dumps(GOOD_CONFIG))
                del bad["lanes"][0][field]
                with self.assertRaises(ConfigError):
                    load_config(self.write(bad))


class TestMatching(ConfigCase):

    def setUp(self):
        super().setUp()
        self.config = load_config(self.write(GOOD_CONFIG))

    def test_a_job_can_match_several_lanes(self):
        job = {"title": "Engineering Manager, Platform", "description": ""}
        self.assertEqual(sorted(lanes_for(job, self.config)), ["EM", "Platform"])

    def test_a_job_matching_nothing_returns_no_lanes(self):
        self.assertEqual(lanes_for({"title": "Chef", "description": ""}, self.config), [])

    def test_the_description_is_searched_as_well_as_the_title(self):
        job = {"title": "Infrastructure Engineer", "description": "You will own Terraform."}
        self.assertEqual(lanes_for(job, self.config), ["Platform"])

    def test_excluded_company_is_case_insensitive(self):
        self.assertTrue(is_excluded(
            {"company": "Randstad Deutschland", "title": "Platform Engineer"}, self.config))

    def test_excluded_title_is_case_insensitive(self):
        self.assertTrue(is_excluded(
            {"company": "Acme", "title": "Technical Recruiter"}, self.config))

    def test_a_wanted_job_is_not_excluded(self):
        self.assertFalse(is_excluded(
            {"company": "Acme", "title": "Platform Engineer"}, self.config))

    def test_highlight_terms_are_matched_case_insensitively(self):
        self.assertTrue(is_highlighted(
            {"title": "Engineer", "description": "We use Terragrunt heavily"}, self.config))
        self.assertFalse(is_highlighted(
            {"title": "Engineer", "description": "We use Ansible"}, self.config))

    def test_missing_fields_do_not_crash_the_matchers(self):
        for job in ({}, {"title": None, "description": None}, {"company": None}):
            with self.subTest(job=job):
                self.assertEqual(lanes_for(job, self.config), [])
                self.assertFalse(is_excluded(job, self.config))


class TestCliContract(ConfigCase):
    """stdout is data, stderr is human, and main always returns an int --
    argparse must never let SystemExit escape."""

    def run_cli(self, *argv, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), out=out, err=err, now=NOW, **kwargs)
        return code, out.getvalue(), err.getvalue()

    def test_unknown_command_exits_2_with_nothing_on_stdout(self):
        code, out, _ = self.run_cli("nonsense")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_help_exits_0(self):
        code, _, _ = self.run_cli("--help")
        self.assertEqual(code, 0)

    def test_no_arguments_exits_2(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_a_missing_config_exits_2_and_says_so_on_stderr(self):
        code, out, err = self.run_cli("digest", "--config", str(self.tmp / "nope.json"))
        self.assertEqual(code, 2)
        self.assertIn("not readable", err)
        self.assertEqual(out, "")

    def test_a_negative_window_exits_2(self):
        code, _, err = self.run_cli("digest", "--config", str(self.write(GOOD_CONFIG)),
                                    "--db", str(self.tmp / "j.db"), "--window", "-1")
        self.assertEqual(code, 2)
        self.assertIn("window", err)

    def test_doctor_reports_config_and_source_counts(self):
        code, out, _ = self.run_cli("doctor", "--config", str(self.write(GOOD_CONFIG)),
                                    "--db", str(self.tmp / "j.db"))
        self.assertEqual(code, 0)
        self.assertIn("2 lane", out)
        self.assertIn("7 enabled", out, "jobicy is disabled in GOOD_CONFIG")

    def test_digest_on_an_empty_store_says_so_on_stderr_not_stdout(self):
        """A bare newline on stdout is indistinguishable from a bug."""
        code, out, err = self.run_cli("digest", "--config", str(self.write(GOOD_CONFIG)),
                                      "--db", str(self.tmp / "j.db"))
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("nothing", err)

    def test_digest_json_always_emits_valid_json_even_when_empty(self):
        """A downstream `| jq` must never receive an empty stdin."""
        code, out, _ = self.run_cli("digest", "--json",
                                    "--config", str(self.write(GOOD_CONFIG)),
                                    "--db", str(self.tmp / "j.db"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [])

    def test_digest_renders_matching_rows_and_hides_the_rest(self):
        db = self.tmp / "j.db"
        store = Store(db)
        store.upsert([
            {"title": "Platform Engineer", "company": "Acme", "location": "Berlin",
             "remote": True, "posted_at": "2026-08-04T00:00:00Z", "url": "https://a",
             "description": "", "tags": [], "salary": None, "source": "arbeitnow"},
            {"title": "Pastry Chef", "company": "Acme", "location": "Berlin",
             "remote": True, "posted_at": "2026-08-04T00:00:00Z", "url": "https://b",
             "description": "", "tags": [], "salary": None, "source": "arbeitnow"},
            {"title": "Platform Engineer", "company": "Randstad", "location": "Berlin",
             "remote": True, "posted_at": "2026-08-04T00:00:00Z", "url": "https://c",
             "description": "", "tags": [], "salary": None, "source": "arbeitnow"},
        ], NOW)
        code, out, _ = self.run_cli("digest", "--config", str(self.write(GOOD_CONFIG)),
                                    "--db", str(db))
        self.assertEqual(code, 0)
        self.assertIn("Platform Engineer", out)
        self.assertNotIn("Pastry Chef", out, "no lane matched")
        self.assertNotIn("Randstad", out, "excluded company")

    def test_sources_prints_the_reason_column(self):
        db = self.tmp / "j.db"
        Store(db).record_source("remotive", "degraded",
                                "schema-drift: missing publication_date", 0, 0, NOW)
        code, out, _ = self.run_cli("sources", "--config", str(self.write(GOOD_CONFIG)),
                                    "--db", str(db))
        self.assertEqual(code, 0)
        self.assertIn("degraded", out)
        self.assertIn("publication_date", out)


class TestDocDrift(unittest.TestCase):
    """Every flag documented in a jfeeds fence in SKILL.md must exist in the
    parser. Documentation that lies about the interface is worse than none,
    because the model follows it and then improvises when it fails."""

    def test_documented_flags_all_exist(self):
        import re

        from job_feeds import build_parser
        skill = Path(__file__).resolve().parents[2] / "SKILL.md"
        if not skill.exists():
            self.skipTest("SKILL.md not written yet")
        known = set()
        for action in build_parser()._actions:
            known.update(action.option_strings)
        documented = set()
        for fence in re.findall(r"```bash\n(.*?)```", skill.read_text(), re.S):
            for line in fence.splitlines():
                if "jfeeds " in line:
                    documented.update(re.findall(r"(--[a-z][a-z-]+)", line))
        self.assertTrue(documented, "no jfeeds invocations found in SKILL.md")
        self.assertEqual(documented - known, set())


class TestLaneMatchScope(unittest.TestCase):
    """Measured on 229 live rows, 2026-08-05: of twelve Platform-lane hits,
    all four TITLE matches were correct and all eight DESCRIPTION matches
    were wrong -- Lemon.io boilerplate listing every discipline, a "Finance,
    Project Management, DevOps, Data" services blurb, an "e.g., Systems
    Engineer" aside, a section heading. Two rounds of regex tightening did
    not fix it, because the problem is not the pattern: role identity lives
    in the title, while descriptions list everything a candidate might ever
    touch.

    So a lane can declare its match scope. Default stays title+description
    -- some lanes genuinely want it, e.g. spotting Terragrunt in the body
    of an otherwise generic "Senior Engineer" ad.
    """

    def config_with(self, **lane_extra):
        data = json.loads(json.dumps(GOOD_CONFIG))
        data["lanes"] = [dict({"name": "platform", "label": "Platform",
                               "match": "devops"}, **lane_extra)]
        return load_config(self.write(data))

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def write(self, data, name="c.json"):
        path = self.tmp / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    JOB = {"title": "C++ Developer",
           "description": "We work across Finance, Project Management, DevOps, Data."}

    def test_default_scope_still_searches_the_description(self):
        self.assertEqual(lanes_for(self.JOB, self.config_with()), ["Platform"])

    def test_title_only_scope_ignores_the_description(self):
        config = self.config_with(match_in="title")
        self.assertEqual(lanes_for(self.JOB, config), [])

    def test_title_only_still_matches_a_real_title(self):
        config = self.config_with(match_in="title")
        job = {"title": "Senior DevOps Engineer", "description": "nothing relevant"}
        self.assertEqual(lanes_for(job, config), ["Platform"])

    def test_an_unknown_match_in_value_is_a_config_error(self):
        """Silently falling back would make a typo look like a lane that
        simply stopped matching."""
        with self.assertRaises(ConfigError) as caught:
            self.config_with(match_in="titel")
        self.assertIn("titel", str(caught.exception))
        self.assertIn("platform", str(caught.exception))

    def test_scope_is_per_lane_not_global(self):
        data = json.loads(json.dumps(GOOD_CONFIG))
        data["lanes"] = [
            {"name": "a", "label": "TitleOnly", "match": "devops", "match_in": "title"},
            {"name": "b", "label": "Both", "match": "devops"},
        ]
        self.assertEqual(lanes_for(self.JOB, load_config(self.write(data))), ["Both"])


class TestFirstRunExperience(ConfigCase):
    """The first command a new user runs is `jfeeds doctor`, and until now
    it answered a missing config with `config not readable: <path>` and
    exit 2. That is accurate and useless: it names the file but not the
    fact that the file is supposed to be created, nor how.

    This skill is installed by strangers whose careers are nothing like
    the example's, so the setup path has to be part of the tool rather
    than a paragraph in the docs someone may not read.
    """

    def run_cli(self, *argv, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), out=out, err=err, now=NOW, **kwargs)
        return code, out.getvalue(), err.getvalue()

    def test_doctor_without_a_config_explains_how_to_create_one(self):
        code, out, err = self.run_cli("doctor", "--config", str(self.tmp / "absent.json"),
                                      "--db", str(self.tmp / "j.db"))
        combined = out + err
        self.assertEqual(code, 2, "a missing config is still an error")
        self.assertIn("absent.json", combined, "must name the path it looked at")
        self.assertIn("no config yet", combined.lower())
        self.assertIn("lanes", combined.lower(),
                      "must say what the file is FOR, not just that it is missing")

    def test_doctor_without_a_config_does_not_traceback(self):
        code, _, err = self.run_cli("doctor", "--config", str(self.tmp / "absent.json"),
                                    "--db", str(self.tmp / "j.db"))
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)

    def test_other_commands_still_get_the_plain_config_error(self):
        """Only doctor offers setup help. `jfeeds digest` explaining how to
        write a config would be noise in a pipeline."""
        code, _, err = self.run_cli("digest", "--config", str(self.tmp / "absent.json"),
                                    "--db", str(self.tmp / "j.db"))
        self.assertEqual(code, 2)
        self.assertIn("not readable", err)
        self.assertNotIn("no config yet", err.lower())

    def test_doctor_with_a_malformed_config_does_not_claim_it_is_missing(self):
        """A broken config and an absent one need different advice --
        telling someone to create a file they already have wastes their
        time looking in the wrong place."""
        path = self.tmp / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        code, out, err = self.run_cli("doctor", "--config", str(path),
                                      "--db", str(self.tmp / "j.db"))
        combined = (out + err).lower()
        self.assertEqual(code, 2)
        self.assertNotIn("no config yet", combined)
        self.assertIn("not valid json", combined)

    def test_doctor_with_a_valid_config_is_unchanged(self):
        code, out, _ = self.run_cli("doctor", "--config", str(self.write(GOOD_CONFIG)),
                                    "--db", str(self.tmp / "j.db"))
        self.assertEqual(code, 0)
        self.assertIn("2 lane", out)


class TestDocumentedExampleActuallyWorks(unittest.TestCase):
    """SKILL.md shows a worked lane and tells the reader what it catches.
    A documented example that has quietly stopped behaving as described is
    worse than none: the reader copies it and blames their own config.

    The example is READ FROM SKILL.md rather than duplicated here, so the
    two cannot drift apart.
    """

    @classmethod
    def setUpClass(cls):
        import re
        skill = Path(__file__).resolve().parents[2] / "SKILL.md"
        blocks = [b for b in re.findall(r"```json\n(.*?)```", skill.read_text(), re.S)
                  if '"name": "platform"' in b]
        assert blocks, "the worked platform-lane example is missing from SKILL.md"
        cls._tmp = tempfile.TemporaryDirectory()
        path = Path(cls._tmp.name) / "example.json"
        path.write_text(blocks[0], encoding="utf-8")
        cls.config = load_config(path)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_it_matches_the_roles_the_docs_claim(self):
        for title in ("Senior Platform Engineer", "Site Reliability Engineer",
                      "Cloud Architect", "SRE Lead", "DevOps Engineer"):
            with self.subTest(title=title):
                self.assertTrue(lanes_for({"title": title, "description": ""}, self.config))

    def test_it_rejects_roles_that_merely_mention_the_tech(self):
        """The failure that motivated match_in: these all name Kubernetes or
        DevOps in the body while being something else entirely."""
        body = "You will work with Kubernetes, Terraform and our DevOps team."
        for title in ("Senior Graphic Designer", "Backend Developer", "C++ Developer"):
            with self.subTest(title=title):
                self.assertFalse(lanes_for({"title": title, "description": body},
                                           self.config))

    def test_the_example_declares_title_only_matching(self):
        self.assertTrue(all(lane.title_only for lane in self.config.lanes),
                        "the documented example must model the rule the docs give")


class TestUnknownConfigKeysAreReported(ConfigCase):
    """A new-user test caught this: doctor answered a config containing a
    field that does not exist, a typo'd exclusion list and a key named
    `totally_made_up_key` with "ok, 1 lane(s)" and exit 0.

    Silently ignoring unknown keys is how a documented-but-unimplemented
    option survives. It did: SKILL.md told the agent to write
    `location_filter`, nothing read it, and doctor -- the one validation
    step the docs prescribe -- confirmed the file was fine. The user's
    primary constraint was dropped without a word.
    """

    def run_cli(self, *argv, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), out=out, err=err, now=NOW, **kwargs)
        return code, out.getvalue(), err.getvalue()

    def doctor_on(self, data):
        return self.run_cli("doctor", "--config", str(self.write(data)),
                            "--db", str(self.tmp / "j.db"))

    def test_an_unknown_default_is_named(self):
        data = json.loads(json.dumps(GOOD_CONFIG))
        data["defaults"]["location_filter"] = "spain|remote"
        code, out, err = self.doctor_on(data)
        combined = out + err
        self.assertIn("location_filter", combined)
        self.assertIn("not recognised", combined.lower())

    def test_a_typo_in_a_known_key_is_named(self):
        """exclude_titel silently does nothing, and the user believes their
        exclusions are applied."""
        data = json.loads(json.dumps(GOOD_CONFIG))
        data["defaults"]["exclude_titel"] = ["recruiter"]
        _, out, err = self.doctor_on(data)
        self.assertIn("exclude_titel", out + err)

    def test_an_unknown_top_level_key_is_named(self):
        data = json.loads(json.dumps(GOOD_CONFIG))
        data["archetypes"] = []
        _, out, err = self.doctor_on(data)
        self.assertIn("archetypes", out + err)

    def test_an_unknown_lane_key_is_named(self):
        data = json.loads(json.dumps(GOOD_CONFIG))
        data["lanes"][0]["match_on"] = "title"
        _, out, err = self.doctor_on(data)
        self.assertIn("match_on", out + err)

    def test_unknown_keys_warn_rather_than_fail(self):
        """A warning, not an error: an unknown key may be a comment or a
        field from a newer version, and refusing to run would be worse
        than saying so."""
        data = json.loads(json.dumps(GOOD_CONFIG))
        data["defaults"]["location_filter"] = "spain"
        code, _, _ = self.doctor_on(data)
        self.assertEqual(code, 0)

    def test_a_clean_config_reports_nothing(self):
        code, out, err = self.doctor_on(GOOD_CONFIG)
        self.assertEqual(code, 0)
        self.assertNotIn("not recognised", (out + err).lower())


class TestExclusionsAreVisible(ConfigCase):
    """Exclusions used to happen in silence, which is the actual defect
    behind "the agency filter does not work".

    Measured on 1,276 live rows, no automatic signal separates an
    intermediary from a direct employer: "our client" appears in 7% of
    known-agency ads and 4% of everything else, and posting volume is
    dominated by genuine employers hiring hard. So the mechanism stays a
    name list -- and the real fix is that you can SEE it working, spot a
    name you should add, and notice when it eats something it should not.
    """

    def run_cli(self, *argv, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), out=out, err=err, now=NOW, **kwargs)
        return code, out.getvalue(), err.getvalue()

    def seed(self, db, rows):
        """rows: (company, title) pairs."""
        store = Store(db)
        store.upsert([{"title": title, "company": company,
                       "location": f"City{i}", "remote": True,
                       "posted_at": "2026-08-04T00:00:00Z", "url": f"https://x/{i}",
                       "description": "", "tags": [], "salary": None,
                       "source": "arbeitnow"}
                      for i, (company, title) in enumerate(rows)], NOW)

    def test_digest_reports_how_many_rows_were_excluded_and_by_which_rule(self):
        """Both rules, because a summary that only ever names one of them
        would look right while hiding the other."""
        db = self.tmp / "j.db"
        self.seed(db, [("Acme", "Platform Engineer"),
                       ("Randstad Deutschland", "Platform Engineer"),
                       ("Acme", "Technical Recruiter, Platform")])
        _, out, err = self.run_cli("digest", "--config", str(self.write(GOOD_CONFIG)),
                                   "--db", str(db))
        self.assertIn("Acme", out)
        self.assertNotIn("Randstad", out)
        self.assertIn("2 row(s) excluded", err)
        self.assertIn("company", err.lower())
        self.assertIn("title", err.lower())
        self.assertIn("recruiter", err.lower())

    def test_it_names_which_rules_fired_so_an_over_broad_term_is_findable(self):
        """A term that quietly eats half the results is the failure mode
        worth catching -- naming the rule makes it obvious which one."""
        db = self.tmp / "j.db"
        self.seed(db, [("Acme", "Platform Engineer"),
                       ("Randstad Deutschland", "Platform Engineer")])
        _, _, err = self.run_cli("digest", "--config", str(self.write(GOOD_CONFIG)),
                                 "--db", str(db))
        self.assertIn("randstad", err.lower())

    def test_nothing_is_said_when_nothing_is_excluded(self):
        db = self.tmp / "j.db"
        self.seed(db, [("Acme", "Platform Engineer")])
        _, _, err = self.run_cli("digest", "--config", str(self.write(GOOD_CONFIG)),
                                 "--db", str(db))
        self.assertNotIn("excluded", err.lower())

    def test_the_shipped_example_excludes_nothing(self):
        """A fresh install must show what the feeds contain before it hides
        any of it. An earlier version shipped 27 company names -- one
        person's accumulated annoyance -- so a stranger pre-filtered 27
        firms before seeing a single job, including firms a contractor
        would actively want. Exclusions are a reaction to results, so
        there is nothing to react to yet on install."""
        example = json.loads(
            (Path(__file__).resolve().parents[1] / "config.example.json").read_text())
        defaults = example["defaults"]
        self.assertEqual(defaults["exclude_company"], [],
                         "the example must not pre-filter employers")
        self.assertEqual(defaults["exclude_title"], [],
                         "seniority is a preference too -- ask, do not assume")

    def test_the_intermediary_names_survive_as_documentation(self):
        """The paired half of the test above, and the reason they are
        separate: emptying the config is only correct if the knowledge
        moves rather than dies. You cannot exclude names you have not met,
        and these firms post under their OWN brand, so no pattern finds
        them. Deleting the reference list would leave the empty default
        looking like an oversight."""
        skill = (Path(__file__).resolve().parents[2] / "SKILL.md").read_text()
        for name in ("proxify", "turing", "toptal", "lemon.io", "zartis", "randstad"):
            with self.subTest(company=name):
                self.assertIn(name, skill.lower())
        self.assertIn("reference list, not a default", skill,
                      "the list must be framed as optional, or it is a default again")


if __name__ == "__main__":
    unittest.main()


class TestSourcesShowsEverySource(ConfigCase):
    """A fresh-install test caught this. After the documented smoke test
    (`fetch --only pythonorg`), `doctor` reported "8 enabled of 8" while
    `sources` printed one green ok line — seven eighths of the corpus
    missing, with nothing saying so.

    The tester's conclusion is the point: the results looked like a quiet
    fortnight for their field rather than "you have barely fetched
    anything", and the ONE command documented to stop you guessing whether
    a quiet day is real went silent exactly when it mattered.
    """

    def run_cli(self, *argv, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), out=out, err=err, now=NOW, **kwargs)
        return code, out.getvalue(), err.getvalue()

    def seeded(self, config=None):
        db = self.tmp / "j.db"
        store = Store(db)
        store.record_source("pythonorg", "ok", "", 20, 1, NOW)
        _, out, err = self.run_cli("sources", "--config",
                                   str(self.write(config or GOOD_CONFIG)),
                                   "--db", str(db))
        return out, err

    def test_a_source_that_was_never_polled_is_listed(self):
        out, _ = self.seeded()
        self.assertIn("arbeitnow", out,
                      "an unpolled source must not be invisible — that is the bug")
        self.assertIn("never polled", out)

    def test_the_polled_source_still_shows_its_real_state(self):
        out, _ = self.seeded()
        self.assertIn("pythonorg", out)
        self.assertIn("20 rows", out)

    def test_every_configured_source_appears_exactly_once(self):
        """Reconciles with doctor, which counts enabled sources. The two
        disagreeing (8 vs 1) was how the omission stayed invisible."""
        out, _ = self.seeded()
        for name in SOURCES:
            self.assertEqual(out.count(f"\n{name} ") + out.startswith(f"{name} "), 1,
                             f"{name} should appear on exactly one line")

    def test_a_source_disabled_in_config_says_so_rather_than_vanishing(self):
        """Absence is ambiguous: a reader cannot tell 'you turned this off'
        from 'this silently failed'."""
        config = json.loads(json.dumps(GOOD_CONFIG))
        config["sources"] = {"arbeitnow": {"enabled": False}}
        out, _ = self.seeded(config)
        self.assertIn("disabled", out)
        line = [ln for ln in out.splitlines() if ln.startswith("arbeitnow")][0]
        self.assertIn("disabled", line)

    def test_an_empty_store_still_lists_the_sources_it_would_poll(self):
        """The old code returned early with only a hint, so a user who had
        not fetched saw nothing at all about what they were about to get."""
        db = self.tmp / "j.db"
        Store(db)
        _, out, err = self.run_cli("sources", "--config", str(self.write(GOOD_CONFIG)),
                                   "--db", str(db))
        self.assertIn("never polled", out)
        self.assertIn("nothing fetched yet", err, "the hint is still useful")


class TestSeenAgeIsComputedNotInvented(ConfigCase):
    """attach_seen_age lives in the CLI, not in report.py, because
    render_html is a pure function of its inputs and a tripwire test blocks
    any clock access inside it. So the age has to arrive pre-computed."""

    def test_whole_days_since_first_seen(self):
        rows = [{"first_seen": "2026-08-03T12:00:00Z"}]
        attach_seen_age(rows, NOW)          # NOW is 2026-08-05T12:00:00Z
        self.assertEqual(rows[0]["seen_days"], 2)

    def test_a_missing_first_seen_yields_None_not_a_guess(self):
        rows = [{"first_seen": None}, {}]
        attach_seen_age(rows, NOW)
        self.assertEqual([r["seen_days"] for r in rows], [None, None])

    def test_an_unparseable_stamp_yields_None_rather_than_crashing(self):
        """A store written by an older version, or a corrupted value, must
        not take down a report that would otherwise be fine."""
        rows = [{"first_seen": "not-a-date"}]
        attach_seen_age(rows, NOW)
        self.assertIsNone(rows[0]["seen_days"])

    def test_a_future_first_seen_clamps_to_zero_rather_than_going_negative(self):
        """Clock skew between machines, or a hand-edited store. 'seen -1d'
        is nonsense a reader would rightly distrust."""
        rows = [{"first_seen": "2026-08-09T12:00:00Z"}]
        attach_seen_age(rows, NOW)
        self.assertEqual(rows[0]["seen_days"], 0)


class TestFirstRunFriction(ConfigCase):
    """claude-skills-302. Friction found by the fresh-install test -- none of
    these were wrong output, which is why they survived the four defects
    fixed in 2b36f72. They were output that told the truth and still left a
    new user with the wrong idea.
    """

    def run_cli(self, *argv, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), out=out, err=err, now=NOW, **kwargs)
        return code, out.getvalue(), err.getvalue()

    def seed(self, db, count, source="arbeitnow", dated=True, title="Platform Engineer"):
        """Its own seeder: the ones above hardcode a posted_at and a single
        source, and these tests turn exactly those two things on and off."""
        store = Store(db)
        store.upsert([{"title": title, "company": f"Co{i}",
                       "location": "Berlin", "remote": True,
                       "posted_at": "2026-08-04T00:00:00Z" if dated else None,
                       "url": f"https://x/{source}/{i}",
                       "description": "", "tags": [], "salary": None,
                       "source": source}
                      for i in range(count)], NOW)

    # --- the digest line names what it drew from -------------------------

    def test_the_digest_line_gives_the_row_denominator(self):
        """'2 row(s)' cannot distinguish 'my lanes are too narrow' from
        'I have only polled one feed'. The denominator is the difference."""
        db = self.tmp / "j.db"
        self.seed(db, 2, title="Platform Engineer")
        self.seed(db, 18, title="Pastry Chef")
        _, _, err = self.run_cli("digest", "--config", str(self.write(GOOD_CONFIG)),
                                 "--db", str(db))
        self.assertIn("2 of 20 row(s)", err)

    def test_the_digest_line_gives_the_source_denominator(self):
        """The tester's corpus came from one source of eight and nothing
        said so, which is what made two rows look like a broken tool."""
        db = self.tmp / "j.db"
        self.seed(db, 3)
        _, _, err = self.run_cli("digest", "--config", str(self.write(GOOD_CONFIG)),
                                 "--db", str(db))
        self.assertIn(f"1 of {len(SOURCES)} sources", err)

    def test_the_source_denominator_counts_distinct_sources_not_rows(self):
        """A guard against len(selected) sneaking into the numerator: with
        two sources the count must be 2, not the row total."""
        db = self.tmp / "j.db"
        self.seed(db, 3, source="arbeitnow")
        self.seed(db, 4, source="jobicy")
        _, _, err = self.run_cli("digest", "--config", str(self.write(GOOD_CONFIG)),
                                 "--db", str(db))
        self.assertIn(f"2 of {len(SOURCES)} sources", err)

    # --- undated rows are explained, not disclaimed ----------------------

    def test_locations_counts_undated_rows_and_names_the_cause(self):
        """An all-undated corpus made the tester think date parsing had
        broken. Saying how many and why is the fix."""
        db = self.tmp / "j.db"
        self.seed(db, 3, dated=False)
        _, out, _ = self.run_cli("locations", "--config", str(self.write(GOOD_CONFIG)),
                                 "--db", str(db))
        self.assertIn("3 carry no date", out)
        self.assertIn("publish none", out,
                      "must name the cause, or it reads as a disclaimer about a bug")

    def test_locations_is_silent_about_dates_when_every_row_has_one(self):
        """The old text was constant, so it warned about a condition that
        was not present -- which is how a note becomes noise."""
        db = self.tmp / "j.db"
        self.seed(db, 3, dated=True)
        _, out, _ = self.run_cli("locations", "--config", str(self.write(GOOD_CONFIG)),
                                 "--db", str(db))
        self.assertNotIn("carry no date", out)

    # --- doctor's starter config is real -------------------------------

    def test_doctor_offers_a_config_that_is_itself_valid(self):
        """The strongest guard here. doctor's help text is only worth
        anything if what it prints actually loads -- so this parses the JSON
        out of the printed heredoc, writes it, and runs doctor on it."""
        missing = self.tmp / "absent.json"
        _, _, err = self.run_cli("doctor", "--config", str(missing),
                                 "--db", str(self.tmp / "j.db"))
        body = err.split("<<'JSON'", 1)[1].split("\nJSON", 1)[0]
        parsed = json.loads(body)
        real = self.tmp / "made.json"
        real.write_text(json.dumps(parsed), encoding="utf-8")
        code, out, _ = self.run_cli("doctor", "--config", str(real),
                                    "--db", str(self.tmp / "j.db"))
        self.assertEqual(code, 0, "the config doctor prints must load")
        self.assertIn("1 lane", out)

    def test_the_starter_lane_regex_is_narrow_enough_to_teach_the_point(self):
        """A starter matching everything would teach the opposite of the
        docs' own advice that lanes should start narrow."""
        missing = self.tmp / "absent.json"
        _, _, err = self.run_cli("doctor", "--config", str(missing),
                                 "--db", str(self.tmp / "j.db"))
        body = err.split("<<'JSON'", 1)[1].split("\nJSON", 1)[0]
        config = load_config_from_dict(json.loads(body), self.tmp)
        self.assertTrue(lanes_for({"title": "Platform Engineer"}, config))
        self.assertFalse(lanes_for({"title": "Pastry Chef"}, config),
                         "a starter lane that matches anything is not a starter")

    def test_doctor_still_recommends_claude_first(self):
        """The starter must not displace the recommended path -- lanes are
        regexes and Claude writing them is still the better route."""
        _, _, err = self.run_cli("doctor", "--config", str(self.tmp / "absent.json"),
                                 "--db", str(self.tmp / "j.db"))
        self.assertLess(err.lower().index("ask claude"), err.index("<<'JSON'"),
                        "Claude must be offered before the manual fallback")


def load_config_from_dict(data, tmp):
    path = tmp / "_tmp_starter.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_config(path)


class TestReportLocation(ConfigCase):
    """Where the report lands. Both job-search tools resolved a relative
    --out against the working directory, so the same command put its output
    in a project folder one day and $HOME the next. That is not a default,
    it is an accident, and the user has to hunt for the file either way.
    """

    def run_cli(self, *argv, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        code = main(list(argv), out=out, err=err, now=NOW, **kwargs)
        return code, out.getvalue(), err.getvalue()

    def seed(self, db):
        Store(db).upsert([{"title": "Platform Engineer", "company": "Acme",
                           "location": "Berlin", "remote": True,
                           "posted_at": "2026-08-04T00:00:00Z", "url": "https://x/1",
                           "description": "", "tags": [], "salary": None,
                           "source": "arbeitnow"}], NOW)

    def config_with(self, report_dir=None):
        data = json.loads(json.dumps(GOOD_CONFIG))
        if report_dir is not None:
            data["defaults"]["report_dir"] = str(report_dir)
        return str(self.write(data))

    def test_a_relative_out_lands_in_the_configured_report_dir(self):
        db = self.tmp / "j.db"
        self.seed(db)
        dest = self.tmp / "job-search"
        self.run_cli("report", "--out", "jobs.html", "--db", str(db),
                     "--config", self.config_with(dest))
        self.assertTrue((dest / "jobs.html").exists(),
                        "a bare name must land in report_dir, not the cwd")

    def test_an_absolute_out_always_wins(self):
        """Someone who typed a full path meant it. Relocating it would be
        worse than any tidiness gained."""
        db = self.tmp / "j.db"
        self.seed(db)
        elsewhere = self.tmp / "explicit.html"
        self.run_cli("report", "--out", str(elsewhere), "--db", str(db),
                     "--config", self.config_with(self.tmp / "job-search"))
        self.assertTrue(elsewhere.exists())
        self.assertFalse((self.tmp / "job-search" / "explicit.html").exists())

    def test_without_report_dir_a_relative_name_still_lands_in_the_cwd(self):
        """Existing installs configure nothing, so nothing may change.

        This MUST use a relative --out. An earlier version passed an
        absolute path, which returns before report_dir is ever consulted --
        so it exercised none of the branch it claimed to guard and could not
        fail when that branch was broken.
        """
        db = self.tmp / "j.db"
        self.seed(db)
        workdir = self.tmp / "cwd"
        workdir.mkdir()
        here = os.getcwd()
        os.chdir(workdir)
        try:
            code, _, _ = self.run_cli("report", "--out", "plain.html", "--db", str(db),
                                      "--config", self.config_with(None))
        finally:
            os.chdir(here)
        self.assertEqual(code, 0)
        self.assertTrue((workdir / "plain.html").exists(),
                        "with no report_dir the cwd must still be the target")

    def test_a_missing_report_dir_is_created_not_an_error(self):
        """Otherwise the first run after configuring it fails, which is the
        one run where the user is least able to diagnose it."""
        db = self.tmp / "j.db"
        self.seed(db)
        dest = self.tmp / "does" / "not" / "exist"
        code, _, _ = self.run_cli("report", "--out", "jobs.html", "--db", str(db),
                                  "--config", self.config_with(dest))
        self.assertEqual(code, 0)
        self.assertTrue((dest / "jobs.html").exists())

    def test_the_written_path_is_reported_absolute(self):
        """'wrote jobs.html' leaves the reader hunting. The report is the
        deliverable; say where it is."""
        db = self.tmp / "j.db"
        self.seed(db)
        dest = self.tmp / "job-search"
        _, _, err = self.run_cli("report", "--out", "jobs.html", "--db", str(db),
                                 "--config", self.config_with(dest))
        self.assertIn(str(dest / "jobs.html"), err)

    def test_report_dir_is_a_recognised_key(self):
        """It must not show up in doctor's unknown-key report -- that list
        exists to catch options nothing reads, and a false entry there
        teaches users to ignore it."""
        code, out, err = self.run_cli("doctor", "--config",
                                      self.config_with(self.tmp / "job-search"),
                                      "--db", str(self.tmp / "j.db"))
        self.assertEqual(code, 0)
        self.assertNotIn("report_dir", out + err)
