"""Contract regression tests over the skill's own files.

Fast and deterministic — no API calls, no LLM. They guard the properties that
make this skill worth having, which prose alone does not protect:

  * the not-credible exclusion, which is the entire wedge and the thing most
    likely to be softened under user pushback;
  * the confidence tagging that keeps elicited claims defensible at interview;
  * the eviction pass, which is the only thing stopping monotonic growth;
  * the routing fork against cv-and-human.

The behavioural evals (evals/evals.json) cover whether the skill produces good
output. These cover whether the skill still says what it does.
"""

import json
import re
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parent

SKILL_MD = SKILL_DIR / "SKILL.md"
README = SKILL_DIR / "README.md"
ARCHETYPES = SKILL_DIR / "references" / "archetypes.md"
QUESTIONS = SKILL_DIR / "references" / "question-bank.md"
EVALS = SKILL_DIR / "evals" / "evals.json"


def _flat(path: Path) -> str:
    """Lowercased with whitespace collapsed, so a phrase split across a line
    break still matches. These tests assert on meaning, not on line layout."""
    return " ".join(path.read_text().lower().split())


def _description(path: Path) -> str:
    """The description field, whitespace-normalised (it is a folded YAML block)."""
    match = re.search(
        r"^description:\s*(?:>-?|\|)?\s*\n?(.*?)(?=^\w[\w-]*:|\Z)",
        path.read_text().split("---")[1],
        re.S | re.M,
    )
    return " ".join(match.group(1).split())


# --- the wedge: exclusions are mandatory, not optional ---------------------


@pytest.mark.parametrize("doc", [SKILL_MD, ARCHETYPES, README])
def test_not_credible_exclusion_is_mandatory(doc):
    """A grading with no exclusions is flattery wearing a lab coat, and it is
    the first thing a user pushes back on. If any of these three documents stops
    demanding it, the skill degrades into generic encouragement without anything
    detecting the change."""
    text = _flat(doc)
    assert "not credible" in text, f"{doc.name} lost the not-credible bucket"
    assert "at least one" in text, (
        f"{doc.name} no longer requires AT LEAST ONE exclusion every time — "
        "without the quantifier this becomes optional in practice"
    )


def test_exclusions_must_say_what_is_missing():
    """An exclusion with no stated gap reads as a door closing rather than a map,
    and is indistinguishable from a token exclusion picked to satisfy the rule."""
    text = _flat(ARCHETYPES)
    assert "what specifically is missing" in text or "say what specifically" in text


# --- the fabrication floor -------------------------------------------------


def test_confidence_tagging_survives():
    """Questioning generates fresh claims under social pressure. The three tags
    are what stop a guess being promoted to a fact the person must then defend
    in a 45-minute interview."""
    text = _flat(SKILL_MD)
    for tag in ["confirmed", "approximate", "unverified"]:
        assert tag in text, f"SKILL.md lost the {tag!r} confidence tag"
    assert "interview" in text, "the defend-it-at-interview test is gone"


def test_counting_the_document_is_governed_too():
    """Two independent runs described a Jul 2023 -> Mar 2024 gap as 'eight
    months' when the blank months are Aug..Feb, seven; one also reported
    'fourteen lines of technologies' for thirteen. Counts of the CV's own
    contents read as observations rather than claims, which is why they slip
    past a fabrication rule written only about invented achievements."""
    text = _flat(SKILL_MD)
    assert "counting the document" in text, "the count-discipline rule is gone"
    assert "hedge it visibly" in text or "hedge it" in text, (
        "the count rule no longer offers hedging as the alternative to counting"
    )
    assert "blank months between" in text, (
        "the gap-arithmetic rule is gone — this is the count a screener is "
        "most likely to check"
    )


def test_missing_numbers_become_work_not_estimates():
    """The specific failure this prevents: a claim that would be stronger with a
    figure the person does not have, so the figure gets estimated."""
    text = _flat(SKILL_MD)
    assert "quantify" in text
    assert "never invent" in text or "do not invent" in text or "never let" in text


# --- eviction is unconditional --------------------------------------------


def test_eviction_pass_is_not_opt_in():
    """Every other CV tool only adds. Eviction is the part that makes the
    document better rather than merely longer, and it only works if it runs
    without being asked for."""
    text = _flat(SKILL_MD)
    assert "eviction" in text
    assert "every session" in text
    assert "without being asked" in text, (
        "eviction has become something the user has to request — at which point "
        "it will not happen and the CV grows monotonically"
    )


# --- elicitation method ----------------------------------------------------


def test_oblique_questioning_rationale_survives():
    """Direct questions return the bullets already on the page. If the reasoning
    for that is lost, the question bank degrades into 'what were your key
    achievements' and the skill stops recovering anything."""
    text = _flat(QUESTIONS)
    assert "oblique" in text
    assert "self-assess" in text


def test_question_batching_limits_survive():
    """A forty-question grilling gets abandoned at question nine, and everything
    after that point is lost work."""
    text = _flat(SKILL_MD)
    assert "three to five" in text, "the per-batch question cap is gone"
    assert "two or three batches" in text, "the per-session batch cap is gone"


# --- the routing fork against cv-and-human --------------------------------


def test_description_hands_document_operations_away():
    """Measured 2026-07-29 at 84/84 over 3 reps. The fork is: a named document
    OPERATION goes to cv-and-human; an open POSITIONING question comes here."""
    description = _description(SKILL_MD).lower()
    assert "cv-and-human" in description, "the handoff target is gone"
    assert "do not use" in description, "the negative route is gone"
    for operation in ["tailor", "ats", "de-slop", "linkedin"]:
        assert operation in description, (
            f"description no longer routes {operation!r} work away — "
            "re-run docs/superpowers/specs/linkedin-router-harness/v3_check.py"
        )


def test_description_claims_the_positioning_triggers():
    description = _description(SKILL_MD).lower()
    for trigger in ["pigeonholed", "credible", "no target role", "career change"]:
        assert trigger in description, f"description lost trigger: {trigger!r}"


def test_body_hands_the_rewrite_to_cv_and_human():
    """Two tools fighting over one artifact serves nobody, and tailoring must
    come second — tailoring thin material only optimises a weaker case."""
    text = SKILL_MD.read_text()
    assert "cv-and-human" in text, "SKILL.md body never names the rewrite skill"


# --- structural integrity --------------------------------------------------


def test_every_path_skill_md_points_at_actually_exists():
    """A dangling reference pointer is invisible until a user hits that branch."""
    referenced = re.findall(r"`((?:references|assets|scripts)/[\w./-]+)`", SKILL_MD.read_text())
    assert referenced, "SKILL.md no longer points at any reference or asset"
    for rel in sorted(set(referenced)):
        assert (SKILL_DIR / rel).exists(), f"SKILL.md points at missing path: {rel}"


def test_every_sibling_skill_named_exists():
    """These skills ship together, so cross-skill pointers are legal — but a
    pointer at a renamed or absent skill is a dead end found mid-task."""
    named = set(re.findall(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`", SKILL_MD.read_text()))
    for name in sorted(n for n in named if n.endswith("-and-human")):
        assert (REPO_ROOT / name / "SKILL.md").exists(), (
            f"SKILL.md points at sibling skill {name!r}, which does not exist"
        )


def test_every_eval_carries_assertions():
    """Prompts without assertions grade nothing. The repo convention is that a
    skill's evals are checkable, not just runnable."""
    data = json.loads(EVALS.read_text())
    assert data["skill_name"] == SKILL_DIR.name, "evals.json skill_name is stale"
    for eval_case in data["evals"]:
        assertions = eval_case.get("assertions")
        assert assertions, f"eval {eval_case['id']} ({eval_case['name']}) has no assertions"


def test_eval_fixtures_all_exist():
    data = json.loads(EVALS.read_text())
    for eval_case in data["evals"]:
        for rel in eval_case.get("files", []):
            assert (SKILL_DIR / "evals" / rel).exists(), (
                f"eval {eval_case['id']} points at missing fixture: {rel}"
            )


def test_fabrication_assertions_cover_the_measured_baseline_failures():
    """The baseline run invented a certification count and merged a date range
    over a seven-month gap. Both were introduced by restructuring rather than by
    inventing an achievement, which is why generic 'no fabricated numbers' did
    not catch them."""
    text = json.dumps(json.loads(EVALS.read_text())).lower()
    assert "count" in text, "no assertion guards invented counts of the CV's own contents"
    assert "hedge" in text or "tilde" in text, "no assertion guards hedge preservation"
    assert "date range" in text, "no assertion guards restructuring that merges date ranges"
