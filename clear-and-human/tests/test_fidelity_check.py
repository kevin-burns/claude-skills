import json
import os
import subprocess
import sys
from pathlib import Path

# clear-and-human has no pyproject.toml pythonpath config (unlike
# cv-and-human), so the scripts dir is added to sys.path here rather than
# relying on external configuration -- keeps this test file self-contained.
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SCRIPT = SCRIPTS_DIR / "fidelity_check.py"

from fidelity_check import (  # noqa: E402
    check_fidelity,
    diff_multiset,
    extract_numbers,
    extract_proper_nouns,
    extract_quotes,
    extract_tracked_spans,
    normalize_code,
    normalize_number,
    normalize_quote,
    normalize_url,
)


# ---------------------------------------------------------------------------
# Numbers: the single most important case in the whole script is "a number
# appeared in the rewrite that wasn't in the original" -- that's fabrication.
# ---------------------------------------------------------------------------

def test_extract_numbers_finds_percentages_currency_dates_and_versions():
    text = "We cut spend 20% on 2026-08-12, saving $1,234.56 in v2.3.1."
    values = extract_numbers(text)
    assert "20%" in values
    assert "2026-08-12" in values
    assert "$1234.56" in values  # comma normalised away
    assert "v2.3.1" in values


def test_extract_numbers_recognises_a_textual_date_without_mangling_it():
    # Regression: a naive whitespace-strip on every number category turned
    # "Aug 12, 2026" into the unreadable, un-matchable "Aug122026".
    values = extract_numbers("Announced Aug 12, 2026 and again 12 Aug 2026.")
    assert "Aug 12, 2026" in values
    assert "12 Aug 2026" in values
    assert "Aug122026" not in values


def test_normalize_number_trivial_variants_collapse_to_the_same_key():
    # "Do not normalise so aggressively that a real change is hidden" --
    # so this only checks the two variants the brief explicitly calls out.
    assert normalize_number("20 %", "percent") == normalize_number("20%", "percent")
    assert normalize_number("1,234", "plain") == normalize_number("1234", "plain")


def test_normalize_number_does_not_hide_a_real_value_change():
    assert normalize_number("20%", "percent") != normalize_number("25%", "percent")


def test_extract_numbers_ignores_digits_inside_code_and_urls():
    # A version number in a URL path or a code identifier is structural,
    # not a claim the prose is making -- extract_tracked_spans masks both
    # out before extract_numbers ever sees the text.
    text = "See https://example.com/v2/report and run `deploy(3)` please."
    clean = extract_tracked_spans(text)["clean"]
    assert extract_numbers(clean) == []


def test_check_fidelity_flags_a_fabricated_percentage_as_appeared():
    original = "We shipped the change and it went smoothly."
    rewrite = "We shipped the change, cutting deploy time by 42%, and it went smoothly."
    results = check_fidelity(original, rewrite)
    appeared_values = [item["value"] for item in results["numbers"]["appeared"]]
    assert "42%" in appeared_values
    assert results["numbers"]["vanished"] == []


def test_check_fidelity_flags_a_dropped_number_as_vanished():
    original = "We cut spend by 42% last quarter."
    rewrite = "We cut spend last quarter."
    results = check_fidelity(original, rewrite)
    vanished_values = [item["value"] for item in results["numbers"]["vanished"]]
    assert "42%" in vanished_values


# ---------------------------------------------------------------------------
# Proper nouns
# ---------------------------------------------------------------------------

def test_proper_noun_survives_even_when_every_mention_opens_a_sentence():
    # A name that is always the subject of its own sentence is common and
    # must not be suppressed just because it never appears mid-sentence.
    text = "Kevin wrote a post. Kevin also wrote a book."
    assert extract_proper_nouns(text) == ["Kevin", "Kevin"]


def test_ordinary_sentence_initial_words_are_not_treated_as_proper_nouns():
    text = "The dog ran fast. The cat sat still. This was fine."
    assert extract_proper_nouns(text) == []


def test_closed_class_word_is_recovered_if_it_appears_mid_sentence_too():
    # "This" is a stopword, but if it shows up somewhere other than a
    # sentence start (e.g. a quoted title), that's evidence it's not just
    # capitalisation-by-position -- the filter should let it through.
    text = "Read This Now. She called it This."
    result = extract_proper_nouns(text)
    assert "This" in result


def test_heading_like_line_is_not_treated_as_a_run_of_proper_nouns():
    text = "Quarterly Report Summary\nThis is normal text about Terraform and AWS."
    result = extract_proper_nouns(text)
    assert "Quarterly" not in result
    assert "Report" not in result
    assert "Summary" not in result
    assert "Terraform" in result
    assert "AWS" in result


def test_check_fidelity_flags_a_new_company_name_as_appeared():
    original = "Kevin said the rollout went smoothly."
    rewrite = "Kevin, who works at Acme, said the rollout went smoothly."
    results = check_fidelity(original, rewrite, names=True)
    appeared_values = [item["value"] for item in results["proper_nouns"]["appeared"]]
    assert "Acme" in appeared_values


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------

def test_extract_quotes_finds_double_quoted_spans():
    text = 'She said "move fast" during the call.'
    assert extract_quotes(text) == ["move fast"]


def test_extract_quotes_curly_and_straight_normalise_to_the_same_key():
    straight = extract_quotes('He said "ship it now".')
    curly = extract_quotes("He said “ship it now”.")
    assert straight == curly


def test_single_quote_contraction_is_not_mistaken_for_a_quoted_span():
    # Regression: a naive '...' pattern paired the apostrophe inside a
    # contraction with the next apostrophe, capturing the mangled fragment
    # "don" out of "she said 'don't stop'". Requiring internal whitespace
    # (a real quote is at least two words) rejects that fragment outright.
    text = "she said 'don't stop' and meant it"
    assert "don" not in extract_quotes(text)


def test_single_quote_multi_word_span_is_still_captured():
    text = "she called it 'a bad idea' more than once"
    assert "a bad idea" in extract_quotes(text)


def test_check_fidelity_flags_an_altered_quote_as_vanished_and_appeared():
    original = 'The README says "ship fast".'
    rewrite = 'The README says "move quickly".'
    results = check_fidelity(original, rewrite)
    assert {"value": "ship fast", "count": 1} in results["quotes"]["vanished"]
    assert {"value": "move quickly", "count": 1} in results["quotes"]["appeared"]


# ---------------------------------------------------------------------------
# URLs and code spans
# ---------------------------------------------------------------------------

def test_extract_tracked_spans_finds_a_url_and_an_inline_code_span():
    text = "See https://example.com/docs and run `deploy --prod` now."
    spans = extract_tracked_spans(text)
    assert spans["urls"] == ["https://example.com/docs"]
    assert spans["code"] == ["`deploy --prod`"]


def test_normalize_url_strips_trailing_sentence_punctuation_not_the_path():
    assert normalize_url("https://example.com/a.") == "https://example.com/a"
    assert normalize_url("https://example.com/a/") == "https://example.com/a/"


def test_normalize_code_keeps_interior_whitespace_and_case_exact():
    assert normalize_code("`deploy --prod`") == "deploy --prod"
    assert normalize_code("`Deploy`") == "Deploy"  # case is content, not noise


def test_normalize_code_strips_a_fenced_blocks_language_tag_line():
    raw = "```python\nprint('hi')\n```"
    assert normalize_code(raw) == "print('hi')"


def test_check_fidelity_flags_a_url_that_changed_target():
    original = "Docs are at https://example.com/v1/api."
    rewrite = "Docs are at https://example.com/v2/api."
    results = check_fidelity(original, rewrite)
    appeared = [item["value"] for item in results["urls"]["appeared"]]
    vanished = [item["value"] for item in results["urls"]["vanished"]]
    assert "https://example.com/v2/api" in appeared
    assert "https://example.com/v1/api" in vanished


def test_check_fidelity_flags_an_edited_code_span():
    original = "Run `deploy --env staging` first."
    rewrite = "Run `deploy --env prod` first."
    results = check_fidelity(original, rewrite)
    appeared = [item["value"] for item in results["code"]["appeared"]]
    vanished = [item["value"] for item in results["code"]["vanished"]]
    assert "deploy --env prod" in appeared
    assert "deploy --env staging" in vanished


# ---------------------------------------------------------------------------
# The diff engine itself
# ---------------------------------------------------------------------------

def test_diff_multiset_appeared_vanished_changed_and_unchanged():
    original = ["a", "a", "b", "c"]
    rewrite = ["a", "b", "b", "d"]
    result = diff_multiset(original, rewrite)
    assert {"value": "d", "count": 1} in result["appeared"]
    assert {"value": "c", "count": 1} in result["vanished"]
    assert {"value": "a", "original_count": 2, "rewrite_count": 1} in result["changed"]
    assert {"value": "b", "original_count": 1, "rewrite_count": 2} in result["changed"]
    # "unchanged" items (present, same count in both) are not reported at
    # all under any of the three buckets -- there is nothing to flag.
    all_values = (
        [i["value"] for i in result["appeared"]]
        + [i["value"] for i in result["vanished"]]
        + [i["value"] for i in result["changed"]]
    )
    assert all_values.count("a") + all_values.count("b") == 2  # only in "changed"


def test_diff_multiset_on_identical_inputs_is_empty():
    same = ["x", "y", "y"]
    result = diff_multiset(same, list(same))
    assert result == {"appeared": [], "vanished": [], "changed": []}


# ---------------------------------------------------------------------------
# The hard rule: this tool is advisory. No verdict, grade, pass/fail, or
# score anywhere in its output -- these assertions exist specifically to
# catch a future edit that adds one back in.
# ---------------------------------------------------------------------------

FORBIDDEN_KEYS = {"ok", "score", "verdict", "grade", "pass", "fail", "passed", "failed"}


def _all_dict_keys(obj) -> set:
    keys = set()
    if isinstance(obj, dict):
        keys |= set(obj.keys())
        for v in obj.values():
            keys |= _all_dict_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            keys |= _all_dict_keys(v)
    return keys


def test_results_never_carry_a_verdict_shaped_key():
    original = "Kevin cut spend 20%."
    rewrite = "Kevin, of Acme, cut spend 42% using v2.0."
    results = check_fidelity(original, rewrite)
    assert _all_dict_keys(results).isdisjoint(FORBIDDEN_KEYS)


def test_human_report_contains_no_score_out_of_language():
    from fidelity_check import _format_report
    original = "Kevin cut spend 20%."
    rewrite = "Kevin, of Acme, cut spend 42%."
    report = _format_report(check_fidelity(original, rewrite))
    lowered = report.lower()
    for phrase in ("score:", "grade:", "verdict:", "/10", "out of 10", "pass", "fail"):
        assert phrase not in lowered


# ---------------------------------------------------------------------------
# CLI: two files, file+stdin, --json, and the always-zero exit code.
# ---------------------------------------------------------------------------

def _run_cli(args, stdin_text=None):
    env = dict(os.environ, LC_ALL="C", LANG="C")
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_diffs_two_files_and_prints_the_fabrication_banner(tmp_path):
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    original.write_text("We shipped the change and it went smoothly.")
    rewrite.write_text("We shipped the change, cutting deploy time by 42%.")

    result = _run_cli([str(original), str(rewrite)])
    assert result.returncode == 0, result.stderr
    assert "FABRICATED" in result.stdout or "42%" in result.stdout
    assert "NEW NUMBER" in result.stdout


def test_cli_reads_rewrite_from_stdin_when_only_one_path_given(tmp_path):
    original = tmp_path / "original.md"
    original.write_text("We cut spend by 20%.")

    result = _run_cli([str(original)], stdin_text="We cut spend by 25%.")
    assert result.returncode == 0, result.stderr
    assert "20%" in result.stdout
    assert "25%" in result.stdout


def test_cli_json_output_is_valid_json_with_the_five_tracked_categories(tmp_path):
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    original.write_text('Kevin said "ship it" about the v1.0 release.')
    rewrite.write_text('Kevin said "ship it now" about the v2.0 release, per Acme.')

    result = _run_cli([str(original), str(rewrite), "--json"])
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"numbers", "quotes", "urls", "code"}
    for section in payload.values():
        assert set(section.keys()) == {"appeared", "vanished", "changed"}


def test_cli_exit_code_is_always_zero_even_with_findings(tmp_path):
    # Advisory: a completed run exits 0 regardless of what it found --
    # there is no pass/fail threshold to compute an exit code from.
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    original.write_text("Nothing numeric here at all.")
    rewrite.write_text("This adds a brand new 99% statistic from nowhere.")

    result = _run_cli([str(original), str(rewrite)])
    assert result.returncode == 0, result.stderr


def test_cli_no_differences_prints_a_clean_message(tmp_path):
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    text = "Plain prose with no numbers, names, quotes, urls, or code."
    original.write_text(text)
    rewrite.write_text(text)

    result = _run_cli([str(original), str(rewrite)])
    assert result.returncode == 0, result.stderr
    assert "No tracked differences" in result.stdout


def test_cli_names_flag_is_actually_wired_through(tmp_path):
    """The --names flag was accepted and silently ignored for one commit.

    Every other test calls check_fidelity() directly, so none of them touched
    the CLI's argument plumbing. A flag that parses but does nothing is worse
    than no flag: the report claims a category was checked when it was not.
    """
    original = tmp_path / "a.md"
    original.write_text("Acme shipped it. The team agreed.")
    rewrite = tmp_path / "b.md"
    rewrite.write_text("Globex shipped it. The team agreed.")

    default = _run_cli([str(original), str(rewrite), "--json"])
    with_names = _run_cli([str(original), str(rewrite), "--json", "--names"])

    assert "proper_nouns" not in json.loads(default.stdout)
    assert "proper_nouns" in json.loads(with_names.stdout), (
        "--names parsed but had no effect on the output"
    )
