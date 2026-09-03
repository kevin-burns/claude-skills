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
    _format_report,
    check_fidelity,
    diff_multiset,
    extract_claim_words,
    extract_numbers,
    extract_proper_nouns,
    extract_quotes,
    extract_tracked_spans,
    normalize_code,
    normalize_number,
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
# Claim words: the class of loss the four span types above cannot see. Both
# positive fixtures are the verbatim examples from blader/humanizer issue
# #212 (2026-08-09), which reported that "several style rules can remove
# information while appearing to only remove shape". Before this section
# both of these rewrites returned a clean report.
# ---------------------------------------------------------------------------

def test_deleted_ranking_superlative_is_flagged():
    """humanizer #212, first example. The superlative ranked this build
    against every other in the document; in a build-vs-buy recommendation
    the ranking WAS the recommendation, and it left with the boldface."""
    original = "The single most important new build is the Safe Completion compliance gate."
    rewrite = "The important new build is the Safe Completion compliance gate."
    vanished = [i["value"] for i in check_fidelity(original, rewrite)["claim_words"]["vanished"]]
    assert "most" in vanished
    assert "single" in vanished


def test_deleted_simultaneity_adverb_is_flagged():
    """humanizer #212, second example. Looks like rule-of-three cleanup.
    "Simultaneously" was the claim: these hold at once, not in sequence."""
    original = (
        "It is simultaneously the product's main differentiator, its legal shield, "
        "and the deciding argument for the voice architecture."
    )
    rewrite = (
        "It is the product's main differentiator, its legal shield, "
        "and the deciding argument for the voice architecture."
    )
    vanished = [i["value"] for i in check_fidelity(original, rewrite)["claim_words"]["vanished"]]
    assert "simultaneously" in vanished


def test_cut_intensifiers_are_not_flagged_as_claims():
    """The negative case named on the bead. "very" and "really" carry force,
    not content -- "very large" and "large" make the same claim. Cutting them
    is the textbook omit-needless-words edit and must stay silent here, or
    the section fires on every correct run and nobody reads it."""
    original = "This is a very robust and really quite extremely useful gate."
    rewrite = "This is a robust and useful gate."
    section = check_fidelity(original, rewrite)["claim_words"]
    assert section == {"appeared": [], "vanished": [], "changed": []}


def test_negation_dropped_by_the_positive_form_rule_is_not_flagged():
    """Deliberate omission, not an oversight: "put statements in positive
    form" is Layer 1 of this skill, so bare "not"/"no" disappear on correct
    rewrites constantly. The emphatic negations a style edit has no business
    touching are still tracked -- see the next test."""
    original = "The result is not unlike the previous run, and there is no penalty."
    rewrite = "The result resembles the previous run, and there is a penalty."
    section = check_fidelity(original, rewrite)["claim_words"]
    assert section == {"appeared": [], "vanished": [], "changed": []}


def test_emphatic_negation_is_still_tracked():
    original = "The gate never fires twice and neither queue drains."
    rewrite = "The gate fires twice and the queue drains."
    vanished = [i["value"] for i in check_fidelity(original, rewrite)["claim_words"]["vanished"]]
    assert "never" in vanished
    assert "neither" in vanished


def test_requirement_downgrade_shows_as_a_swap():
    """RFC 2119's word list, borrowed for exactly this: turning a MUST into
    a SHOULD is a change of requirement level wearing the clothes of a
    softened sentence."""
    section = check_fidelity(
        "Callers must retry the request.", "Callers should retry the request."
    )["claim_words"]
    assert "must" in [i["value"] for i in section["vanished"]]
    assert "should" in [i["value"] for i in section["appeared"]]


def test_claim_words_inside_hyphenated_compounds_are_left_alone():
    """"first-class" is not the ordinal, "all-in-one" is not the quantifier."""
    assert extract_claim_words("A first-class all-in-one single-file build") == []
    assert extract_claim_words("The first build") == ["first"]


def test_claim_words_are_lowercased_and_counted_as_a_multiset():
    words = extract_claim_words("Only the Only one. ALL of it.")
    assert words == ["only", "only", "all"]


def test_claim_words_ignore_identifiers_inside_code_spans():
    """`all()` is a builtin, not a quantifier the prose is asserting."""
    section = check_fidelity(
        "Use `all(flags)` to combine them.", "Use `any(flags)` to combine them."
    )["claim_words"]
    assert section == {"appeared": [], "vanished": [], "changed": []}


def test_claim_word_report_shows_the_sentence_the_word_sat_in():
    """A bare count ("only: was x4, now x2") is not actionable -- the reader
    has to go and grep for it. The context line is what makes the finding
    locatable, so it is asserted rather than left as a nicety."""
    original = "The gate is simultaneously a shield and a differentiator."
    rewrite = "The gate is a shield and a differentiator."
    report = _format_report(check_fidelity(original, rewrite), original, rewrite)
    assert "simultaneously" in report
    assert "[relation]" in report
    assert "The gate is simultaneously a shield and a differentiator." in report


def test_claim_word_report_survives_without_the_source_texts():
    """_format_report's text arguments are optional; a caller that passes
    only results gets the rows without contexts, not a crash."""
    original = "It is simultaneously A and B."
    report = _format_report(check_fidelity(original, "It is A and B."))
    assert "simultaneously" in report


def test_claim_words_do_not_suppress_the_nothing_to_check_warning():
    """The vacuity warning is keyed to hard spans on purpose. Claim words
    are near-ubiquitous, so counting them would silence that warning on
    exactly the numberless drafts it was added for."""
    original = "Our service reduces all costs, improves reliability, and shortens onboarding."
    gutted = "Our service reduces all costs."
    report = _format_report(check_fidelity(original, gutted), original, gutted)
    assert "NOTHING TO CHECK" in report
    assert "This is not a pass." in report


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
        env=env, check=False
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


def test_cli_json_output_is_valid_json_with_the_default_categories(tmp_path):
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    original.write_text('Kevin said "ship it" about the v1.0 release.')
    rewrite.write_text('Kevin said "ship it now" about the v2.0 release, per Acme.')

    result = _run_cli([str(original), str(rewrite), "--json"])
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    # The JSON contract is five finding categories plus provenance. The provenance keys
    # were added 2026-09-03 after a pasted report was found to have gone stale against an
    # edited artefact -- see measured_digest() in the script. They are named here rather
    # than allowed through by a loose check, so a future addition still has to be deliberate.
    CATEGORIES = {"numbers", "quotes", "urls", "code", "claim_words"}
    PROVENANCE = {"measured_sha256", "measured_note"}
    assert set(payload.keys()) == CATEGORIES | PROVENANCE
    for name in CATEGORIES:
        assert set(payload[name].keys()) == {"appeared", "vanished", "changed"}


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
    """Identical files WITH tracked spans get the clean message."""
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    text = "We cut deploys from 40 minutes to 6, per the v2.1 release notes."
    original.write_text(text)
    rewrite.write_text(text)

    result = _run_cli([str(original), str(rewrite)])
    assert result.returncode == 0, result.stderr
    assert "No tracked differences" in result.stdout


def test_cli_prose_with_nothing_to_track_says_so_instead(tmp_path):
    """This fixture used to assert a clean pass. It was the vacuous case."""
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    original.write_text("Plain prose with no numbers, names, quotes, urls, or code.")
    rewrite.write_text("Plain prose with no numbers, names, quotes, urls, or code.")

    result = _run_cli([str(original), str(rewrite)])
    assert result.returncode == 0, result.stderr
    assert "NOTHING TO CHECK" in result.stdout
    assert "No tracked differences" not in result.stdout


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


# --- the vacuous pass, found by a graded eval ---------------------------

def test_clean_result_over_nothing_is_reported_as_nothing_to_check():
    """A pass over an empty set is not evidence, and read identically to one.

    Eval case 9 asked whether a rewrite kept all five claims. The input had
    no numbers, quotes, URLs or code spans, so this script returned "No
    tracked differences" -- and would return it for a rewrite that dropped
    every claim. The grader called the pass worthless, correctly.
    """
    original = "Our service reduces costs, improves reliability, and shortens onboarding."
    gutted = "Our service reduces costs."
    report = _format_report(check_fidelity(original, gutted))
    assert "NOTHING TO CHECK" in report
    assert "This is not a pass." in report
    assert "No tracked differences" not in report


def test_clean_result_over_real_spans_still_reports_a_pass():
    """The warning must not swallow the genuine case."""
    original = "We cut deploys from 40 minutes to 6."
    faithful = "Deploys went from 40 minutes to 6."
    report = _format_report(check_fidelity(original, faithful))
    assert "No tracked differences" in report
    assert "NOTHING TO CHECK" not in report
    assert "2 tracked item(s)" in report


def test_tracked_count_is_not_mistaken_for_a_category():
    """_tracked_in_original is bookkeeping; it must not render as a section."""
    results = check_fidelity("We saw 40 things.", "We saw 41 things.")
    assert "_tracked_in_original" in results
    report = _format_report(results)
    assert "_tracked" not in report


# ------------------------------------------------------------------ measured-bytes provenance
#
# Same fix as register_report.py, same reason. A pasted check went stale after the artefact was
# edited, and nothing in the output made that visible. The report now names a digest of the exact
# bytes it compared, so a reader holding the delivered text can tell whether the block belongs
# to it. This does not prevent staleness; it makes staleness visible, which is the only honest
# thing a report can do about it.


def test_report_states_a_digest_of_both_documents(tmp_path):
    import hashlib
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    original.write_text("The team shipped it on Tuesday after 40 minutes of review.\n", encoding="utf-8")
    rewrite.write_text("The team shipped it Tuesday, after 40 minutes of review.\n", encoding="utf-8")
    out = _run_cli([str(original), str(rewrite)]).stdout
    assert "measured:" in out
    for f in (original, rewrite):
        assert hashlib.sha256(f.read_bytes()).hexdigest()[:16] in out, f"no digest for {f.name}"


def test_the_digest_changes_when_the_rewrite_changes(tmp_path):
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    original.write_text("The team shipped it on Tuesday after 40 minutes of review.\n", encoding="utf-8")
    rewrite.write_text("The team shipped it Tuesday, after 40 minutes of review.\n", encoding="utf-8")
    before = _run_cli([str(original), str(rewrite)]).stdout
    rewrite.write_text("The team shipped it Tuesday, after 40 minutes of checking.\n", encoding="utf-8")
    after = _run_cli([str(original), str(rewrite)]).stdout
    assert before != after
    def digests(text):
        return [line for line in text.splitlines() if "measured:" in line]

    assert digests(before) != digests(after)


def test_digest_is_present_in_json_too(tmp_path):
    import json as _json
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    original.write_text("The team shipped it on Tuesday after 40 minutes of review.\n", encoding="utf-8")
    rewrite.write_text("The team shipped it Tuesday, after 40 minutes of review.\n", encoding="utf-8")
    payload = _json.loads(_run_cli([str(original), str(rewrite), "--json"]).stdout)
    assert "measured_sha256" in payload
    assert set(payload["measured_sha256"]) >= {"original", "rewrite"}
