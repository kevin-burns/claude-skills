import json
import os
import re
import subprocess
import sys
from pathlib import Path

# No pyproject.toml pytest config exists for this skill (only the named files
# for this task were touched), so resolve the import path here rather than
# relying on repo-wide pytest configuration.
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from register_report import (
    CONTRACTION,
    DEMONSTRATIVE,
    MIN_WORDS,
    NOMINALISATION,
    NOT_NOMINALISATIONS,  # noqa: E402
    collect_baseline,
    count_nominalisations,
    format_report,
    profile,
    strip_noise,
    to_json,
)

SCRIPT = SCRIPTS_DIR / "register_report.py"


def _pad(core: str, min_words: int = MIN_WORDS) -> str:
    """Pad a short sample up to MIN_WORDS with neutral filler words.

    Filler uses none of the tracked features (no pronouns, no contractions,
    no negation, no demonstratives, no nominalisation suffixes) so the
    padding cannot change the measured rates, only dilute them predictably.
    """
    words = core.split()
    filler_needed = max(0, min_words - len(words))
    filler = (["banana"] * filler_needed) if filler_needed else []
    return " ".join(words + filler)


# --- contraction regex: the possessive trap -------------------------------

def test_contraction_regex_does_not_count_possessive_s():
    # "the skill's job" has no contraction in it -- 's here is possessive.
    # A naive \w+'s pattern would match it and silently inflate warmth.
    assert CONTRACTION.findall("the skill's job") == []


def test_contraction_regex_counts_genuine_apostrophe_s_contractions():
    # "it's", "that's" etc. ARE contractions (it is / that is) even though
    # they share the same "'s" spelling as a possessive.
    assert CONTRACTION.findall("it's raining and that's fine") == ["it's", "that's"]


def test_contraction_regex_counts_nt_re_ve_ll_m():
    text = "doesn't won't we're they've I'll I'm"
    found = CONTRACTION.findall(text)
    assert len(found) == 6


def test_contraction_regex_ignores_ordinary_possessive_on_a_name():
    # A common real-world case: a person's or product's possessive should
    # never register as a contraction.
    assert CONTRACTION.findall("Kevin's post and the team's plan") == []


# --- nominalisation regex: the stem-length undercount ----------------------

def test_nominalisation_matches_short_common_nominalisations():
    # The ported prototype's \w{4,} required a 4-character stem before the
    # suffix, so it silently missed short-but-real nominalisations like
    # these (total length 6-7). This is the fix documented in the script's
    # NOMINALISATION comment -- guard it so it can't regress.
    for word in ("action", "nation", "station", "options"):
        assert NOMINALISATION.search(word), f"{word!r} should match as a nominalisation"


def test_nominalisation_still_excludes_ordinary_short_words():
    assert NOMINALISATION.findall("the cat sat on it") == []


def test_nominalisation_excludes_ordinary_words_ending_in_those_letters():
    """The real false positives, which "the cat sat on it" never exercised.

    A stem floor alone cannot separate "nation" from "stance" -- both have a
    two-character stem -- so these depend on NOT_NOMINALISATIONS. Six of
    these fire repeatedly in this skill's own reference files, "stance" most
    of all, which is how the defect was found.
    """
    prose = (
        "The stance had a chance in France. A dance by the fence in the city, "
        "hence a moment of comment in one sentence, for balance."
    )
    leaked = [
        w for w in NOMINALISATION.findall(prose)
        if w.lower() not in NOT_NOMINALISATIONS
    ]
    assert count_nominalisations(prose) == 0, f"false positives: {leaked}"


def test_exclusion_list_only_contains_words_the_matcher_actually_matches():
    """A dead entry means someone guessed instead of checking.

    Every word in NOT_NOMINALISATIONS must be something the pattern would
    otherwise catch -- otherwise the list grows with words that were never
    a problem and nobody can tell which entries are load-bearing.
    """
    dead = [w for w in NOT_NOMINALISATIONS if not NOMINALISATION.fullmatch(w)]
    assert dead == [], f"entries the pattern never matches anyway: {sorted(dead)}"


def test_nominalisation_matches_longer_forms_too():
    assert NOMINALISATION.findall("information and management") == ["information", "management"]


# --- strip_noise -------------------------------------------------------

def test_strip_noise_removes_fenced_code_block():
    text = "Some prose.\n```\n$ curl -s http://example.com | jq .\n```\nMore prose."
    cleaned = strip_noise(text)
    assert "curl" not in cleaned
    assert "Some prose." in cleaned
    assert "More prose." in cleaned


def test_strip_noise_removes_front_matter():
    text = "---\ntitle: Test\ndate: 2026-01-01\n---\nActual content here."
    cleaned = strip_noise(text)
    assert "title:" not in cleaned
    assert "Actual content here." in cleaned


def test_strip_noise_removes_table_rows():
    text = "Prose before.\n| a | b |\n| - | - |\n| 1 | 2 |\nProse after."
    cleaned = strip_noise(text)
    assert "|" not in cleaned
    assert "Prose before." in cleaned
    assert "Prose after." in cleaned


def test_strip_noise_keeps_link_label_but_drops_url():
    text = "See [the docs](https://example.com/docs) for more."
    cleaned = strip_noise(text)
    assert "the docs" in cleaned
    assert "https://example.com" not in cleaned


# --- the minimum-length gate --------------------------------------------

def test_profile_refuses_below_minimum_words():
    short_text = "This is short. " * 5  # well under MIN_WORDS
    try:
        profile(short_text)
        raise AssertionError("profile() should have raised ValueError on a short document")
    except ValueError as exc:
        assert str(MIN_WORDS) in str(exc)


def test_profile_succeeds_at_exactly_the_minimum():
    text = _pad("This is a plain sentence with no tracked features in it.", MIN_WORDS)
    result = profile(text)
    assert result["n_words"] == MIN_WORDS


def test_profile_reports_zero_contractions_on_prose_with_only_possessives():
    # Direct regression guard for the bug the evidence brief describes: a
    # naive regex would report nonzero contractions here.
    core = "The skill's job and the team's plan and the project's scope."
    text = _pad(core)
    result = profile(text)
    assert result["features"]["contraction"] == 0.0


# --- axis independence ---------------------------------------------------

def test_person_and_stiffness_features_are_disjoint_keys():
    from register_report import PERSON_META, STIFFNESS_META
    person_keys = {k for k, *_ in PERSON_META}
    stiffness_keys = {k for k, *_ in STIFFNESS_META}
    assert person_keys.isdisjoint(stiffness_keys)


def test_stiffness_features_do_not_require_first_person():
    # A purely third-person, contraction-heavy passage should still register
    # a nonzero (warm) contraction rate on the STIFFNESS axis, with zero
    # first/second person on the PERSON axis -- proving the axes don't leak
    # into each other.
    core = (
        "The system doesn't retry silently. It won't hide a failure, and "
        "the team's on-call rotation isn't optional. That's the whole point."
    )
    text = _pad(core)
    result = profile(text)
    assert result["features"]["first_person"] == 0.0
    assert result["features"]["second_person"] == 0.0
    assert result["features"]["contraction"] > 0.0


# --- baseline aggregation ---------------------------------------------------

def test_collect_baseline_averages_across_documents(tmp_path):
    doc_a = _pad("I like this and I think that helps me and my team.")
    doc_b = _pad("I like this and I think that helps me and my team.")
    (tmp_path / "a.md").write_text(doc_a, encoding="utf-8")
    (tmp_path / "b.md").write_text(doc_b, encoding="utf-8")
    result = collect_baseline(tmp_path)
    assert result is not None
    assert result["n_docs"] == 2
    assert result["n_skipped"] == 0


def test_collect_baseline_skips_short_files_without_failing(tmp_path, capsys):
    (tmp_path / "long.md").write_text(_pad("Plenty of words here to pass the gate."), encoding="utf-8")
    (tmp_path / "short.md").write_text("Too short.", encoding="utf-8")
    result = collect_baseline(tmp_path)
    assert result is not None
    assert result["n_docs"] == 1
    assert result["n_skipped"] == 1
    err = capsys.readouterr().err
    assert "short.md" in err


def test_collect_baseline_returns_none_when_no_files_qualify(tmp_path, capsys):
    (tmp_path / "short.md").write_text("Too short.", encoding="utf-8")
    result = collect_baseline(tmp_path)
    assert result is None


def test_collect_baseline_returns_none_on_empty_directory(tmp_path):
    assert collect_baseline(tmp_path) is None


# --- report formatting: axes stay labelled and separate ---------------------

def test_format_report_labels_person_as_context_never_a_fault():
    text = _pad("I write about my own work and I like it.")
    result = profile(text)
    report = format_report(result, "personal", None, "draft.md")
    assert "PERSON" in report
    assert "context" in report.lower()
    assert "never a fault" in report.lower()


def test_format_report_labels_stiffness_as_the_axis_worth_scrutiny():
    text = _pad("The service doesn't fail silently and that's intentional.")
    result = profile(text)
    report = format_report(result, "unset", None, "draft.md")
    assert "STIFFNESS" in report
    assert "scrutiny" in report.lower()


def test_report_does_not_claim_the_axes_are_independent():
    """The claim was removed on 2026-08-13 and must not creep back.

    Establishing independence needs ~95-100 same-channel documents by one
    author; at N=30 the confidence interval does not even exclude the
    correlation Biber's own loadings imply. The separation is justified by
    Biber (1988:107) reading Dimension 1 as two parameters, and by Thonney
    (2013) on first person as a rhetorical choice -- neither of which needs
    the features to be uncorrelated. An earlier version of this file asserted
    independence in the report header, the JSON payload and the docstring.
    """
    text = _pad("The service doesn't fail silently and that's intentional.")
    result = profile(text)
    report = format_report(result, "unset", None, "draft.md").lower()
    payload = json.dumps(to_json(result, "unset", None, "draft.md")).lower()
    for surface, name in ((report, "human report"), (payload, "json output")):
        assert "independent of person" not in surface, (
            f"the independence claim is back in the {name}"
        )


def test_format_report_notes_ttr_is_not_an_ai_likeness_signal():
    text = _pad("The service doesn't fail silently and that's intentional.")
    result = profile(text)
    report = format_report(result, "unset", None, "draft.md")
    assert "ai-likeness" in report.lower()


def test_format_report_declared_stance_is_printed_verbatim_not_inferred():
    # A high first-person text with --stance impersonal should still print
    # "impersonal" -- the flag is never overridden by the measured numbers.
    text = _pad("I write about my own work constantly, and I like it.")
    result = profile(text)
    report = format_report(result, "impersonal", None, "draft.md")
    assert "declared stance: impersonal" in report


def test_format_report_without_baseline_says_it_stands_alone():
    text = _pad("Plain prose with nothing special in it at all today.")
    result = profile(text)
    report = format_report(result, "unset", None, "draft.md")
    assert "no --baseline supplied" in report


def test_format_report_with_baseline_shows_a_comparison_column():
    text = _pad("Plain prose with nothing special in it at all today.")
    result = profile(text)
    baseline = {"n_docs": 3, "n_skipped": 0, "features": dict(result["features"])}
    report = format_report(result, "unset", baseline, "draft.md")
    assert "baseline" in report.lower()
    assert "3 document(s)" in report


def test_no_verdict_language_anywhere_in_the_report():
    # The hard requirement: advisory only, no score/grade/pass-fail. Matched
    # as whole words -- a substring check would false-positive on ordinary
    # prose like "wasn't passed" (contains "pass").
    text = _pad("Plain prose with nothing special in it at all today.")
    result = profile(text)
    report = format_report(result, "unset", None, "draft.md")
    lowered = report.lower()
    for banned in (r"\bpass\b", r"\bfail\b", r"\bgrade\b", r"\bscore\b", r"\bverdict\b"):
        assert not re.search(banned, lowered), banned


def test_to_json_includes_citations_and_ttr_caveat():
    text = _pad("Plain prose with nothing special in it at all today.")
    result = profile(text)
    payload = to_json(result, "unset", None, "draft.md")
    assert "citations" in payload
    assert payload["stiffness"]["ttr_caveat"]
    assert "contraction" in payload["citations"]
    assert "Biber" in payload["citations"]["contraction"]


# --- CLI behaviour (subprocess, matches li_profile_check's test style) -----

def _run_cli(args, cwd=None, input_text=None):
    env = dict(os.environ, LC_ALL="C", LANG="C")
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env, cwd=cwd, input=input_text, check=False
    )


def test_cli_help_exits_zero():
    result = _run_cli(["--help"])
    assert result.returncode == 0
    assert "PERSON" in result.stdout or "register" in result.stdout.lower()


def test_cli_refuses_short_draft_with_nonzero_exit(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("Too short.", encoding="utf-8")
    result = _run_cli([str(draft)])
    assert result.returncode == 2
    assert "REFUSING TO REPORT" in result.stderr


def test_cli_reports_zero_on_a_sufficient_draft(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(_pad("The service doesn't fail silently and that's intentional."), encoding="utf-8")
    result = _run_cli([str(draft)])
    assert result.returncode == 0
    assert "AXIS 1" in result.stdout
    assert "AXIS 2" in result.stdout


def test_cli_json_output_is_valid_json(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(_pad("The service doesn't fail silently and that's intentional."), encoding="utf-8")
    result = _run_cli([str(draft), "--json"])
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["person"]["stance"] == "unset"
    assert "stiffness" in payload


def test_cli_stance_flag_is_echoed_not_computed(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(_pad("No first person pronouns appear in this text at all."), encoding="utf-8")
    result = _run_cli([str(draft), "--stance", "personal", "--json"])
    payload = json.loads(result.stdout)
    # Zero measured first-person density, but the declared stance still
    # prints exactly what was passed -- never overridden by the numbers.
    assert payload["person"]["stance"] == "personal"
    assert payload["person"]["features"]["first_person"] == 0.0


def test_cli_missing_draft_file_is_a_usage_error(tmp_path):
    result = _run_cli([str(tmp_path / "nope.md")])
    assert result.returncode == 2


def test_cli_reads_stdin_when_no_positional_arg_given():
    text = _pad("Plain prose with nothing special in it at all today.")
    result = _run_cli([], input_text=text)
    assert result.returncode == 0
    assert "<stdin>" in result.stdout


def test_cli_baseline_dir_that_does_not_exist_is_a_usage_error(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(_pad("Plain prose with nothing special in it at all today."), encoding="utf-8")
    result = _run_cli([str(draft), "--baseline", str(tmp_path / "nope")])
    assert result.returncode == 2


def test_cli_with_baseline_adds_comparison_column(tmp_path):
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    (baseline_dir / "one.md").write_text(_pad("I like writing about my own work and I enjoy it."), encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text(_pad("The service doesn't fail silently and that's intentional."), encoding="utf-8")
    result = _run_cli([str(draft), "--baseline", str(baseline_dir)])
    assert result.returncode == 0
    assert "baseline: 1 document(s)" in result.stdout


# --- demonstratives: the citation must describe the measurement ------------

def test_demonstrative_counts_clause_initial_pronouns():
    """Biber's .76 is on demonstrative PRONOUNS. These are the real ones."""
    for text in ("That is the point.", "This means the rule changed.",
                 "Those were the rules.", "These are the eight."):
        assert len(DEMONSTRATIVE.findall(text)) == 1, f"missed a pronoun in {text!r}"


def test_demonstrative_excludes_complementiser_relativiser_and_determiner():
    """The bug this replaced: a bare this/that/these/those match counted all
    three of these as demonstrative pronouns, putting Biber's pronoun loading
    next to a number measuring something else entirely."""
    for text, why in [("I said that he left.", "complementiser"),
                      ("It shows that costs are rising.", "complementiser"),
                      ("the thing that matters most", "relativiser"),
                      ("That afternoon was long.", "determiner")]:
        assert DEMONSTRATIVE.findall(text) == [], f"{why} counted as a pronoun: {text!r}"


# --- the overlap the negation citation now documents -----------------------

def test_expanding_contractions_moves_contraction_rate_not_negation():
    """Documents the coupling rather than pretending it away.

    Rewriting "doesn't" as "does not" is the formalising edit this whole
    skill cares about. It shows up in the contraction row and is invisible
    in the negation row, because analytic negation counts both forms. A
    reader who expects negation to catch it will misread every report.
    """
    warm = _pad("It doesn't matter and it isn't ready and we don't agree.")
    cold = _pad("It does not matter and it is not ready and we do not agree.")
    w, c = profile(warm)["features"], profile(cold)["features"]
    assert w["contraction"] > 0 and c["contraction"] == 0, "contractions must move"
    assert abs(w["negation"] - c["negation"]) < 1e-9, (
        "negation rate changed under contraction expansion -- if this ever "
        "becomes true, the citation block claiming it does not must be updated"
    )


# --------------------------------------------------------------- --against (register drift)
#
# The gap these cover, from claude-skills-qyp: fidelity_check.py catches a rewrite that
# fabricates a FACT. Nothing caught a rewrite that fabricates a REGISTER. Measured on a real
# corpus by a confirmed non-native English writer -- median contraction rate 2.9 per 1000
# words, one piece at exactly 0.0 -- where Layer 3's "restore contractions the draft expanded"
# has nothing to restore and moves her further from herself with nothing reporting it.

STIFF = "It is your livingroom dolling up as a venue and the support was not bad."
LOOSE = "It's your living room dressed up as a venue and the support wasn't bad."


def _drift_section(out: str) -> str:
    i = out.upper().find("REGISTER DRIFT")
    assert i >= 0, "no REGISTER DRIFT section in the report"
    return out[i:]


def test_against_reports_the_movement(tmp_path):
    original = tmp_path / "original.md"
    original.write_text(_pad(STIFF), encoding="utf-8")
    rewrite = tmp_path / "rewrite.md"
    rewrite.write_text(_pad(LOOSE), encoding="utf-8")
    result = _run_cli([str(rewrite), "--against", str(original)])
    assert result.returncode == 0, result.stderr
    section = _drift_section(result.stdout)
    assert "contraction" in section


def test_against_does_not_judge_the_movement(tmp_path):
    """No threshold and no verdict -- the same posture as the rest of this script,
    which states outright that it reports numbers and does not judge them."""
    original = tmp_path / "original.md"
    original.write_text(_pad(STIFF), encoding="utf-8")
    rewrite = tmp_path / "rewrite.md"
    rewrite.write_text(_pad(LOOSE), encoding="utf-8")
    section = _drift_section(_run_cli([str(rewrite), "--against", str(original)]).stdout).lower()
    for verdict in ("too much", "too far", "excessive", "should be", "warning:", "problem"):
        assert verdict not in section, f"the drift section delivered a verdict: {verdict!r}"


def test_against_refuses_when_the_original_is_too_short(tmp_path):
    original = tmp_path / "original.md"
    original.write_text("Three words only.", encoding="utf-8")
    rewrite = tmp_path / "rewrite.md"
    rewrite.write_text(_pad(LOOSE), encoding="utf-8")
    result = _run_cli([str(rewrite), "--against", str(original)])
    assert result.returncode == 2
    assert "REFUSING" in result.stderr
    assert "original" in result.stderr.lower()


def test_against_with_baseline_names_movement_away_from_the_author(tmp_path):
    """The signal the bead asks for, and it is a comparison rather than a threshold:
    the original sat near the author's own rate and the rewrite left it."""
    base = tmp_path / "corpus"
    base.mkdir()
    (base / "a.md").write_text(_pad("It is a matter of record that the thing is not so."), encoding="utf-8")
    (base / "b.md").write_text(_pad("It is well known that the venue is not large at all."), encoding="utf-8")
    original = tmp_path / "original.md"
    original.write_text(_pad(STIFF), encoding="utf-8")
    rewrite = tmp_path / "rewrite.md"
    rewrite.write_text(_pad(LOOSE), encoding="utf-8")
    result = _run_cli([str(rewrite), "--against", str(original), "--baseline", str(base)])
    assert result.returncode == 0, result.stderr
    assert "AWAY" in _drift_section(result.stdout).upper()


def test_against_json_carries_the_delta(tmp_path):
    original = tmp_path / "original.md"
    original.write_text(_pad(STIFF), encoding="utf-8")
    rewrite = tmp_path / "rewrite.md"
    rewrite.write_text(_pad(LOOSE), encoding="utf-8")
    payload = json.loads(_run_cli([str(rewrite), "--against", str(original), "--json"]).stdout)
    assert "drift" in payload
    row = payload["drift"]["contraction"]
    assert set(row) >= {"original", "rewrite", "delta"}
    assert row["delta"] == row["rewrite"] - row["original"]


def test_no_drift_section_without_against(tmp_path):
    """The flag is opt-in; an ordinary run is unchanged."""
    rewrite = tmp_path / "rewrite.md"
    rewrite.write_text(_pad(LOOSE), encoding="utf-8")
    result = _run_cli([str(rewrite)])
    assert "REGISTER DRIFT" not in result.stdout.upper()


# ------------------------------------------------------------------ measured-bytes provenance
#
# claude-skills-<P1>: a pasted register_report block went stale. The check was run, the text was
# then edited, and the old numbers were presented as evidence for the new text. Contractions
# matched exactly while nominalisation was 25% out -- the signature of a check that predates an
# edit. Nothing in the output made that visible, so a stale paste and a real one are
# indistinguishable to a reader.
#
# The fix is provenance, not exhortation: the report states a digest of the exact bytes it
# measured, so anyone can hash the delivered text and see whether the block belongs to it.


def test_report_states_a_digest_of_what_it_measured(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(_pad("The service doesn't fail silently and that's intentional."), encoding="utf-8")
    out = _run_cli([str(draft)]).stdout
    assert "measured:" in out, "the report does not say what bytes it measured"
    import hashlib
    want = hashlib.sha256(draft.read_bytes()).hexdigest()[:12]
    assert want in out, "the digest in the report is not the digest of the measured file"


def test_the_digest_changes_when_the_text_changes(tmp_path):
    """The whole point: an edited artefact must not match a report run before the edit."""
    draft = tmp_path / "draft.md"
    body = _pad("The service doesn't fail silently and that's intentional.")
    draft.write_text(body, encoding="utf-8")
    before = _run_cli([str(draft)]).stdout
    draft.write_text(body.replace("intentional", "deliberate"), encoding="utf-8")
    after = _run_cli([str(draft)]).stdout

    def digest(text):
        line = next(x for x in text.splitlines() if "measured:" in x)
        return line.split()[-1]

    assert digest(before) != digest(after)


def test_digest_is_present_in_json_too(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(_pad("The service doesn't fail silently and that's intentional."), encoding="utf-8")
    payload = json.loads(_run_cli([str(draft), "--json"]).stdout)
    assert "measured_sha256" in payload
    import hashlib
    assert payload["measured_sha256"].startswith(hashlib.sha256(draft.read_bytes()).hexdigest()[:12])


# ------------------------------------------------------------- coordinated series (shape, not rhythm)
#
# Eval runs 3 and 4 both failed expectation 9.7 the same way, and the second time with better
# self-justification. Original: "Our service reduces costs, improves reliability, and shortens
# onboarding." Rewrite: "Our service cuts costs, improves reliability, and speeds up onboarding."
# Two verbs swapped for near-synonyms, the three-item coordination untouched -- delivered as
# structural variation both times.
#
# The instruction said "vary sentence rhythm". The model varied LENGTH, which is a defensible
# reading of rhythm, and left SHAPE alone. Naming that distinction in prose was not enough the
# first time, so it is measured here: a series that survives a rewrite is visible rather than
# arguable.


def test_finds_a_three_item_coordinated_series():
    from register_report import coordinated_series
    s = coordinated_series("Our service reduces costs, improves reliability, and shortens onboarding.")
    assert [n for _, n in s] == [3]


def test_finds_a_series_with_a_single_comma():
    """'A, B and C' is a three-item series with one comma -- a comma count alone misses it."""
    from register_report import coordinated_series
    assert [n for _, n in coordinated_series("The estate spans AWS, Azure and GCP.")] == [3]


def test_two_clauses_joined_by_and_are_not_a_series():
    from register_report import coordinated_series
    assert coordinated_series("It works, and it is fast.") == []


def test_a_plain_sentence_has_no_series():
    from register_report import coordinated_series
    assert coordinated_series("The deploy takes four minutes.") == []


def test_synonym_swap_leaves_the_series_intact_which_is_the_whole_point():
    from register_report import coordinated_series
    before = coordinated_series("Our service reduces costs, improves reliability, and shortens onboarding.")
    after = coordinated_series("Our service cuts costs, improves reliability, and speeds up onboarding.")
    assert before == after, "the measure must show that a synonym swap changed no structure"


def test_a_genuine_restructure_removes_the_series():
    from register_report import coordinated_series
    after = coordinated_series(
        "Our service cuts costs. It improves reliability too, which is what shortens onboarding.")
    assert after == []


def test_series_are_reported_per_sentence_with_their_position():
    from register_report import coordinated_series
    text = ("The deploy takes four minutes. "
            "It cuts costs, improves reliability, and shortens onboarding.")
    assert coordinated_series(text) == [(2, 3)]


def test_drift_section_reports_a_surviving_series(tmp_path):
    original = tmp_path / "original.md"
    rewrite = tmp_path / "rewrite.md"
    original.write_text(_pad("Our service reduces costs, improves reliability, and shortens onboarding."),
                        encoding="utf-8")
    rewrite.write_text(_pad("Our service cuts costs, improves reliability, and speeds up onboarding."),
                       encoding="utf-8")
    out = _run_cli([str(rewrite), "--against", str(original)]).stdout
    assert "COORDINATED SERIES" in out.upper()
    assert "SURVIVED" in out.upper(), "a series present before and after must be called out"


def test_a_sequenced_grouping_is_not_a_flat_series():
    """The false positive that made the first version of this detector unusable.

    Measured on a rewrite the skill had never seen, which restructured correctly:
      before  verifies the account, provisions the workspace, and notifies the team lead
      after   verifies the account and provisions the workspace, then notifies the team lead
    A flat three-item list became a 2+1 grouping -- two coordinated actions and one
    sequenced handoff. The detector reported that as a surviving three-item series, so a
    CORRECT answer failed the check. A check that fails an ideal output is as useless as
    one that cannot fail.
    """
    from register_report import coordinated_series
    assert coordinated_series(
        "The onboarding flow verifies the account and provisions the workspace, "
        "then notifies the team lead.") == []


def test_a_flat_list_is_still_caught_after_the_sequencing_fix():
    """The other direction, so the fix is not suppression."""
    from register_report import coordinated_series
    assert [n for _, n in coordinated_series(
        "The onboarding flow verifies the account, provisions the workspace, "
        "and notifies the team lead.")] == [3]
    # and the case-9 rewrite that genuinely did keep its coordination
    assert [n for _, n in coordinated_series(
        "Our service cuts costs and improves reliability, and onboarding gets faster too.")] == [3]


def test_subordinated_clauses_do_not_count_as_coordinands():
    from register_report import coordinated_series
    assert coordinated_series(
        "Our service cuts costs, which is what shortens onboarding.") == []
    assert coordinated_series(
        "It provisions the workspace and notifies the lead, so nobody waits.") == []
