"""Config, lane matching and the CLI contract. No network."""

import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from job_feeds import (  # noqa: E402
    ConfigError, Store, is_excluded, is_highlighted, lanes_for, load_config, main)

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


if __name__ == "__main__":
    unittest.main()
