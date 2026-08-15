import json
import os
import subprocess
import sys
from pathlib import Path

from li_profile_check import count_chars, utf16_slice

SCRIPT = Path(__file__).parent.parent / "scripts" / "li_profile_check.py"


def test_count_chars_matches_js_string_length():
    # JS String.prototype.length counts UTF-16 code units.
    assert count_chars("abc") == 3            # plain ASCII
    assert count_chars("café") == 4           # U+00E9, one code unit
    assert count_chars("🚀") == 2             # surrogate pair, TWO in JS
    assert count_chars("\r\n") == 2           # CRLF is two characters
    assert count_chars("") == 0


def test_count_chars_differs_from_python_len_on_emoji():
    # The whole reason this function exists.
    text = "Platform Engineer 🚀"
    assert len(text) == 19
    assert count_chars(text) == 20


def test_utf16_slice_matches_js_code_unit_slicing_at_a_pair_boundary():
    text = "ab🚀cd"
    # 3 code units = "ab" plus the rocket's lone high surrogate. JS string
    # slicing is oblivious to surrogate-pair validity (it slices raw UTF-16
    # code units), so the faithful result keeps the lone surrogate rather
    # than silently dropping it -- matching JS's actual `.slice(0, 3)`.
    assert utf16_slice(text, 3) == "ab\ud83d"
    assert utf16_slice(text, 4) == "ab🚀"
    assert utf16_slice(text, 99) == text


def test_utf16_slice_and_count_chars_handle_a_genuine_lone_surrogate():
    # A lone surrogate reachable from valid JSON (e.g. {"headline": "lone
    # \ud83d surrogate"}) must not crash count_chars or utf16_slice -- both
    # need errors="surrogatepass" on their encode calls (and utf16_slice's
    # decode) rather than the default strict codec.
    text = "lone \ud83d surrogate"
    assert count_chars(text) == len(text)  # JS reports 1 per lone surrogate
    assert utf16_slice(text, 999) == text


def test_check_field_flags_over_limit():
    from li_profile_check import LIMITS, check_field
    result = check_field("headline", "x" * 225)
    assert result["ok"] is False
    assert result["count"] == 225
    assert result["limit"] == LIMITS["headline"]
    assert result["over_by"] == 5


def test_check_field_passes_under_limit():
    from li_profile_check import check_field
    result = check_field("headline", "Platform Engineer who cut AWS spend 38%")
    assert result["ok"] is True
    assert result["over_by"] == 0


def test_check_field_boundary_at_exactly_the_limit():
    # Guards the `<=` in check_field: flipping it to `<` would still pass
    # every other test in this file but wrongly reject a headline at exactly
    # the limit.
    from li_profile_check import check_field
    assert check_field("headline", "x" * 220)["ok"] is True
    assert check_field("headline", "x" * 221)["over_by"] == 1


def test_front_load_passes_when_claim_is_above_the_fold():
    from li_profile_check import FOLD, check_front_load
    about = "I cut a fintech's AWS bill by 38%. " + ("filler. " * 60)
    result = check_front_load(about, ["38%"])
    assert result["ok"] is True
    assert result["missing"] == []
    assert count_chars(result["visible"]) <= FOLD


def test_front_load_fails_when_claim_is_buried_below_the_fold():
    from li_profile_check import check_front_load
    about = ("Experienced professional. " * 20) + "I cut AWS spend 38%."
    result = check_front_load(about, ["38%"])
    assert result["ok"] is False
    assert result["missing"] == ["38%"]


def test_keyword_coverage_reports_which_field_carries_each_keyword():
    from li_profile_check import keyword_coverage
    fields = {
        "headline": "Platform Engineer",
        "about": "I run Terraform across three clouds.",
        "skills": "Kubernetes",
    }
    rows = {r["keyword"]: r for r in keyword_coverage(["Terraform", "Kubernetes", "Go"], fields)}
    assert rows["Terraform"]["fields"] == ["about"]
    assert rows["Kubernetes"]["fields"] == ["skills"]
    assert rows["Go"]["fields"] == []
    assert rows["Go"]["covered"] is False


def test_keyword_coverage_is_case_insensitive():
    from li_profile_check import keyword_coverage
    rows = keyword_coverage(["terraform"], {"about": "We use Terraform daily."})
    assert rows[0]["covered"] is True


def test_check_skills_flags_only_the_overlong_skill():
    from li_profile_check import check_skills
    results = check_skills(["Kubernetes", "x" * 85])
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False
    assert results[1]["over_by"] == 5


def test_check_profile_is_not_ok_when_any_check_fails():
    from li_profile_check import check_profile
    results = check_profile({
        "headline": "x" * 300,
        "about": "short",
        "skills": ["Kubernetes"],
        "keywords": ["Terraform"],
        "must_contain": [],
    })
    assert results["ok"] is False
    assert results["coverage"][0]["covered"] is False


def test_check_profile_is_ok_on_a_clean_draft():
    from li_profile_check import check_profile
    results = check_profile({
        "headline": "Platform Engineer who cut a fintech's AWS spend 38%",
        "about": "I cut a fintech's AWS spend 38% and own their Terraform monorepo.",
        "skills": ["Terraform", "Kubernetes"],
        "keywords": ["Terraform"],
        "must_contain": ["38%"],
    })
    assert results["ok"] is True


def test_uncovered_keyword_is_advisory_and_does_not_flip_ok():
    from li_profile_check import check_profile
    # A profile with a fully uncovered keyword but valid lengths/front-load/skills
    # should still return ok=True because coverage is advisory, not gating.
    results = check_profile({
        "headline": "Platform Engineer 🚀",
        "about": "I cut AWS spend 38%.",
        "skills": ["Terraform"],
        "keywords": ["GoLang"],  # Not present anywhere in the profile
        "must_contain": ["38%"],
    })
    assert results["ok"] is True
    # Verify the keyword is indeed uncovered in coverage results
    golang_result = [c for c in results["coverage"] if c["keyword"] == "GoLang"][0]
    assert golang_result["covered"] is False


def _run_cli(tmp_path, profile: dict, *, json_out: bool = False):
    """Run the script as a subprocess against a temp JSON file.

    Uses sys.executable and forces a C locale so the test exercises the same
    locale conditions that originally crashed the CLI on an emoji headline
    (MAJOR 3), regardless of the locale the test suite itself runs under.
    """
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    env = dict(os.environ, LC_ALL="C", LANG="C")
    args = [sys.executable, str(SCRIPT), str(profile_path)]
    if json_out:
        args.append("--json")
    return subprocess.run(args, capture_output=True, text=True, env=env, check=False)


def test_main_exits_zero_on_a_clean_emoji_profile_under_c_locale(tmp_path):
    # This is what would have caught the UnicodeDecodeError: reading the
    # profile file used the locale default encoding, which crashes under
    # LC_ALL=C on a profile containing an emoji.
    profile = {
        "headline": "Platform Engineer 🚀",
        "about": "I cut AWS spend 38%.",
        "skills": ["Terraform"],
        "keywords": [],
        "must_contain": [],
    }
    result = _run_cli(tmp_path, profile, json_out=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    headline_field = [f for f in payload["fields"] if f["field"] == "headline"][0]
    assert headline_field["count"] == 20


def test_main_exits_one_on_an_over_limit_profile(tmp_path):
    profile = {
        "headline": "x" * 300,
        "about": "short",
        "skills": ["Kubernetes"],
        "keywords": [],
        "must_contain": [],
    }
    result = _run_cli(tmp_path, profile)
    assert result.returncode == 1, result.stderr
