"""Tests for cohesion_report.

The properties worth pinning are the ones that would make the report LIE about a
location or invent confidence it has not earned. A wrong line number sends the
reader to the wrong paragraph; a 0.00 printed for a four-word paragraph reads as
a cohesion break when it is really the measure running out of material.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import cohesion_report as c  # noqa: E402

# ------------------------------------------------------------------ line mapping

def test_line_numbers_survive_front_matter():
    """REGRESSION RISK: a report that names line 3 of a stripped buffer sends the
    reader to line 3 of the file, which is inside the YAML. Every finding has to
    map to the ORIGINAL file or the whole design point -- a location beats a
    number -- is lost."""
    doc = '---\ntitle: "x"\nslug: y\n---\n\nFirst paragraph about cohesion.\n\nSecond paragraph about cohesion.\n'
    paras = c.paragraphs(doc)
    assert len(paras) == 2
    assert paras[0]["line"] == 6, paras[0]["line"]
    assert doc.split("\n")[paras[0]["line"] - 1].startswith("First paragraph")


def test_line_numbers_are_correct_without_front_matter():
    doc = "\n\nAlpha beta gamma.\n\nDelta epsilon zeta.\n"
    paras = c.paragraphs(doc)
    assert doc.split("\n")[paras[0]["line"] - 1].startswith("Alpha")


# ------------------------------------------------------------------ what counts as prose

def test_fenced_code_is_not_a_paragraph():
    doc = "Prose one here.\n\n```bash\necho definitely not prose\n```\n\nProse two here.\n"
    assert [p["text"] for p in c.paragraphs(doc)] == ["Prose one here.", "Prose two here."]


def test_headings_tables_lists_rules_and_quotes_are_excluded():
    """Each of these between two paragraphs would otherwise read as a total
    cohesion break, when the reader experiences no break at all. Blockquotes were
    the one originally missed: a quoted line scored as a paragraph sharing nothing
    with its neighbours and took a slot in the ranked output."""
    doc = (
        "Real prose about extraction.\n\n"
        "## A heading\n\n"
        "| col | col |\n| --- | --- |\n\n"
        "- a list item\n- another\n\n"
        "> a quoted line from somewhere else\n\n"
        "---\n\n"
        "More real prose about extraction.\n"
    )
    texts = [p["text"] for p in c.paragraphs(doc)]
    assert texts == ["Real prose about extraction.", "More real prose about extraction."], texts


# ------------------------------------------------------------------ the measure

def test_repeated_subject_scores_higher_than_a_topic_jump():
    """The only claim the overlap number makes: two paragraphs about the same thing
    share more content words than two about different things. No threshold is
    asserted anywhere -- just the ordering."""
    same = c.junctions(c.paragraphs(
        "The extractor reads the PDF and returns text.\n\n"
        "That extractor returns text the parser then reads from the PDF.\n"))
    diff = c.junctions(c.paragraphs(
        "The extractor reads the PDF and returns text.\n\n"
        "Yesterday the weather in Aachen turned cold and rain fell.\n"))
    assert same[0]["overlap"] > diff[0]["overlap"]
    assert diff[0]["overlap"] == 0.0


def test_a_short_paragraph_is_reported_as_unmeasurable_not_as_a_break():
    """A four-word paragraph scoring 0.00 means "too short", not "disconnected".
    Printing those alongside real findings is how a metric earns false confidence,
    so they are flagged and counted rather than ranked."""
    doc = ("A long opening paragraph carrying plenty of distinct content words about "
           "extraction, parsing, hyphenation and column widths in a generated document.\n\n"
           "Not many words.\n")
    j = c.junctions(c.paragraphs(doc))[0]
    assert j["measurable"] is False


def test_the_window_sees_context_the_adjacent_pair_misses():
    """A paragraph that returns to the section's subject after an aside should not
    read as a gap. Adjacent overlap alone called 9 of 39 junctions exactly 0.00 on
    a real 2,000-word post and the ranking became a list of ties."""
    doc = ("Terragrunt orchestrates the modules and keeps the estate consistent everywhere.\n\n"
           "Briefly, an aside about weather in Aachen during a cold wet autumn week.\n\n"
           "Terragrunt then reapplies those modules across the estate consistently.\n")
    j = c.junctions(c.paragraphs(doc), window=2)[-1]
    assert j["overlap_window"] > j["overlap"]


# ------------------------------------------------------------------ referential findings

def test_a_backreference_opener_is_flagged_and_a_connective_is_not():
    doc = ("The gate asserts against the extracted text every single build without fail.\n\n"
           "This is the part people skip when they are busy shipping other things.\n")
    j = c.junctions(c.paragraphs(doc))[0]
    assert j["cold_open"] is True and j["connective"] is False

    doc2 = doc.replace("This is the part", "However that is the part")
    j2 = c.junctions(c.paragraphs(doc2))[0]
    assert j2["connective"] is True and j2["cold_open"] is False


def test_a_term_introduced_with_an_explanation_is_not_listed_as_unglossed():
    glossed = c.terms("`pdftotext` is the poppler tool that extracts text.\n"
                      "Later we run `pdftotext` again.\n", exempt=set())
    rec = [t for t in glossed if t["term"] == "pdftotext"][0]
    assert rec["glossed"] is True and rec["count"] == 2

    bare = c.terms("We pipe it through `pdftotext` and move on.\n"
                   "Then `pdftotext` runs again.\n", exempt=set())
    assert [t for t in bare if t["term"] == "pdftotext"][0]["glossed"] is False


def test_an_exempt_term_is_dropped_so_known_jargon_stops_crowding_out_real_gaps():
    ts = c.terms("We run `pdftotext` here and `pdftotext` there.\n", exempt={"pdftotext"})
    assert not any(t["term"] == "pdftotext" for t in ts)


def test_terms_inside_a_code_fence_are_ignored():
    """Code is not prose. A term used only in an example has not been introduced to
    the reader, and counting it would hide the fact that it never was."""
    ts = c.terms("Prose here.\n\n```bash\npdftotext --layout in.pdf out.txt\n```\n", exempt=set())
    assert not any(t["term"] == "pdftotext" for t in ts)


# ------------------------------------------------------------------ what it must never do

def test_the_report_names_the_formulas_only_to_say_it_did_not_compute_them(capsys, tmp_path):
    """The single rule this skill exists to enforce. The report is ALLOWED to name
    Flesch and grade levels -- it has to, in order to say why they are absent -- but
    it must never attach a number to one, and must never print a verdict. An earlier
    version of this test banned the words outright and failed on the disclaimer,
    which would have meant deleting the most important paragraph in the output."""
    f = tmp_path / "d.md"
    f.write_text(
        "The extractor reads a generated document and returns plain text for indexing, "
        "which is the version an applicant tracking system actually receives.\n\n"
        "A column width changed by four millimetres and the hyphenation moved, so the "
        "same sentence produced two different strings under two different extractors.\n")
    c.report(f, exempt=set(), as_json=False, top=6)
    out = capsys.readouterr().out

    # a number attached to any formula name is the failure
    for name in ("flesch", "kincaid", "gunning", "smog", "grade"):
        assert not re.search(rf"{name}[^.\n]{{0,20}}?\d", out, re.I), f"{name} carries a number"
    for verdict in ("PASS", "FAIL", "too hard", "too easy", "target score"):
        assert verdict.lower() not in out.lower(), f"report emitted a verdict: {verdict!r}"

    # and the disclaimer must be there, because silence about the formulas is how
    # somebody reaches for one anyway
    assert "WHAT THIS DID NOT DO" in out
    assert "Redish" in out


def test_a_single_paragraph_says_nothing_to_check_rather_than_reporting_clean(capsys, tmp_path):
    """Borrowed from fidelity_check: a pass over an empty set is not evidence. One
    paragraph has no junctions, and printing a clean report would be a lie of
    omission."""
    f = tmp_path / "d.md"
    f.write_text("Only one paragraph exists in this document.\n")
    c.report(f, exempt=set(), as_json=False, top=6)
    assert "NOTHING TO CHECK" in capsys.readouterr().out


def test_a_comment_line_in_the_terms_file_does_not_become_an_exempt_term(tmp_path):
    """A hand-maintained vocabulary file grows comments. A "#" line joining the
    exemption set is the kind of thing nobody notices until a real term stops being
    reported, which is a silent loss of a finding."""
    import subprocess
    import sys as _s
    terms = tmp_path / "t.txt"
    terms.write_text("# vocabulary the audience knows\npdftotext\n\n# trailing note\n")
    doc = tmp_path / "d.md"
    doc.write_text("We pipe it through `pdftotext` and then `poppler` twice for the sake "
                   "of comparing two extractors against one generated document here.\n\n"
                   "Later the same `poppler` invocation runs again on a second document, "
                   "and `pdftotext` is called once more against the same input file.\n")
    script = Path(__file__).resolve().parents[1] / "scripts" / "cohesion_report.py"
    out = subprocess.run([_s.executable, str(script), str(doc), "--terms", str(terms), "--json"],
                         capture_output=True, text=True, check=True).stdout
    # Assert against the TERMS list specifically. Searching the whole blob is wrong:
    # an exempt term still legitimately appears in a junction's shared-word list,
    # because exempting it from the glossary check does not delete it from the prose.
    names = [t["term"] for t in json.loads(out)["terms"]]
    assert "pdftotext" not in names, "a listed term should be exempt from the term inventory"
    assert "poppler" in names, "an unlisted term must still be reported"
    assert not any("vocabulary" in n for n in names), "a comment line became an exempt term"


def test_terms_are_still_reported_when_the_document_is_too_short_for_junctions(capsys, tmp_path):
    """A one-paragraph document has no junctions, but it can still use four terms it
    never explains. An earlier version returned early and threw the term inventory
    away with the junctions, so a short document got NOTHING TO CHECK and nothing
    else -- a silence dressed up as a limit."""
    f = tmp_path / "d.md"
    f.write_text("We pipe it through `pdftotext` and then `pdftotext` again later.\n")
    c.report(f, exempt=set(), as_json=False, top=6)
    out = capsys.readouterr().out
    assert "NOTHING TO CHECK for cohesion" in out
    assert "pdftotext" in out, "the term inventory must survive a document with no junctions"
