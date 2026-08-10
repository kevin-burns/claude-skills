"""Contract regression tests over the skill's own files.

These are deliberately fast and deterministic — no API calls, no LLM. They guard
the failure class that unit tests on the checker cannot see and that a human
reviewer caught only by reading carefully: documentation drifting away from the
code it describes, a reference pointing at a file that does not exist, and a
routing edit to a *neighbouring* skill being reverted without anyone noticing.

The behavioural evals (evals/evals.json) cover whether the skill produces good
output. These cover whether the skill still says what it does.
"""

import re
from pathlib import Path

import pytest

from li_profile_check import LIMITS

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parent

SKILL_MD = SKILL_DIR / "SKILL.md"
REFERENCE = SKILL_DIR / "references" / "linkedin-profile.md"
README = SKILL_DIR / "README.md"


def _frontmatter(path: Path) -> str:
    return path.read_text().split("---")[1]


# Claude Code truncates the combined `description` and `when_to_use` text at
# this many characters in the skill listing, to reduce context usage. See
# https://code.claude.com/docs/en/skills.md. Text past it is written but never
# read, so a routing phrase that lands beyond it does nothing.
LISTING_CAP = 1536


def _description(path: Path) -> str:
    """The description field, whitespace-normalised (it is a folded YAML block)."""
    match = re.search(
        r"^description:\s*(?:>-?|\|)?\s*\n?(.*?)(?=^\w[\w-]*:|\Z)",
        _frontmatter(path),
        re.S | re.M,
    )
    return " ".join(match.group(2 if match.lastindex and match.lastindex >= 2 else 1).split())


def _visible_description(path: Path) -> str:
    """Only the part of the description the skill listing actually shows.

    Routing assertions belong here rather than on `_description`: a phrase can
    be present in the file and still invisible to the router.
    """
    return _description(path)[:LISTING_CAP]


# --- the skill still claims the LinkedIn capability ------------------------


def test_description_carries_the_linkedin_profile_triggers():
    """These phrases are what the routing harness scored 54/54. Losing one
    silently narrows what the router sends here."""
    description = _description(SKILL_MD).lower()
    for phrase in [
        "linkedin profile",
        "rewrite my linkedin headline",
        "recruiter search",
        "make my linkedin match my cv",
    ]:
        assert phrase in description, f"description no longer carries trigger: {phrase!r}"


def test_description_routes_linkedin_posts_away():
    """Posts belong to hook-and-human/clear-and-human. Without this the mode
    starts absorbing social copy it has no rules for."""
    description = _description(SKILL_MD).lower()
    assert "post" in description
    assert "hook-and-human" in description
    assert "clear-and-human" in description


# --- the neighbouring skills keep their carve-outs -------------------------
# The router spike measured that dropping these regresses CV de-slop routing
# from 4/4 to 2/4. They live in other skills, so nothing else guards them.


@pytest.mark.parametrize(
    "skill_name,required",
    [
        ("clear-and-human", "cv-and-human"),
        ("hook-and-human", "cv-and-human"),
    ],
)
def test_neighbouring_skill_still_routes_profile_work_here(skill_name, required):
    neighbour = REPO_ROOT / skill_name / "SKILL.md"
    if not neighbour.exists():
        pytest.skip(f"{skill_name} not present (skill distributed standalone)")
    description = _description(neighbour).lower()
    assert required in description, (
        f"{skill_name}'s description lost its cv-and-human carve-out — "
        "re-run the routing harness before shipping"
    )
    assert "profile" in description


# --- the fork against cv-evidence-base -------------------------------------
# Measured 2026-07-29 at 84/84 across 3 reps. The fork is: a named document
# OPERATION lands here; an open POSITIONING question lands on cv-evidence-base.


def test_description_fits_the_skill_listing_cap():
    """Anything past the cap is written but never read.

    The docs state that the combined `description` and `when_to_use` text is
    "truncated at 1,536 characters in the skill listing to reduce context
    usage" (https://code.claude.com/docs/en/skills.md). Truncation, not an
    error, so nothing fails loudly — this description sat 280 characters over
    with the cv-evidence-base fork in the discarded tail, and every routing
    assertion below still passed because they read the file rather than the
    listing.
    """
    description = _description(SKILL_MD)
    assert len(description) <= LISTING_CAP, (
        f"description is {len(description)} chars, {len(description) - LISTING_CAP} "
        f"past the {LISTING_CAP}-char listing cap. Everything after the cap is "
        f"invisible to routing. Truncated tail: {description[LISTING_CAP:]!r}"
    )


def test_description_hands_open_positioning_questions_to_the_sibling():
    """Without this carve-out, 'here's my CV, does this look OK' is claimed by
    both skills. It routed correctly even before the carve-out existed, but the
    ambiguity is real in the text and one router change could expose it.

    Asserted against the TRUNCATED description on purpose. Checking the whole
    file is the bug this test used to have: the carve-out was present, this
    passed, and the router never saw it.
    """
    description = _visible_description(SKILL_MD).lower()
    assert "cv-evidence-base" in description, (
        "cv-and-human no longer routes open positioning questions to "
        "cv-evidence-base within the first "
        f"{LISTING_CAP} characters — re-run "
        "docs/superpowers/specs/linkedin-router-harness/v3_check.py"
    )
    assert "no target role" in description, (
        "the fork's discriminator ('no target role in mind') is gone from the "
        "visible part of the description"
    )


def test_every_sibling_skill_named_in_skill_md_exists():
    """The repo ships these skills together, so cross-skill pointers are legal —
    but a pointer at a skill that was renamed or removed is a dead end the user
    only discovers mid-task. Nothing else in the suite checks across skills."""
    body = SKILL_MD.read_text()
    named = set(re.findall(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`", body))
    siblings = {n for n in named if (REPO_ROOT / n / "SKILL.md").exists()
                or n.count("-") >= 2 and not n.endswith((".py", ".md"))}
    # Only assert on names that look like sibling skills we actually reference.
    for name in sorted(n for n in named if n.endswith("-and-human") or n == "cv-evidence-base"):
        if name == SKILL_DIR.name:
            continue
        assert (REPO_ROOT / name / "SKILL.md").exists(), (
            f"SKILL.md points at sibling skill {name!r}, which does not exist"
        )
    assert siblings, "SKILL.md no longer names any sibling skill"


# --- documentation must not drift from the code ---------------------------


def test_reference_limits_table_matches_the_scripts_LIMITS():
    """The reference publishes a limits table; the script enforces LIMITS.
    If they disagree, one of them is lying to the user."""
    rows = re.findall(r"^\|\s*([A-Za-z][^|]*?)\s*\|\s*([\d,]+)\s*\|", REFERENCE.read_text(), re.M)
    documented = {
        label.strip().lower(): int(value.replace(",", ""))
        for label, value in rows
        if value.replace(",", "").isdigit()
    }

    expected = {
        "headline": LIMITS["headline"],
        "about": LIMITS["about"],
        "experience description": LIMITS["experience"],
        "position title": LIMITS["position_title"],
        "company name": LIMITS["company_name"],
        "skill (each)": LIMITS["skill"],
    }
    for label, limit in expected.items():
        assert label in documented, f"reference limits table lost its {label!r} row"
        assert documented[label] == limit, (
            f"{label}: reference says {documented[label]}, script enforces {limit}"
        )


def test_every_path_skill_md_points_at_actually_exists():
    """A dangling reference pointer is invisible until a user hits that branch."""
    referenced = re.findall(r"`((?:references|scripts)/[\w./-]+)`", SKILL_MD.read_text())
    assert referenced, "SKILL.md no longer points at any reference or script"
    for rel in sorted(set(referenced)):
        assert (SKILL_DIR / rel).exists(), f"SKILL.md points at missing path: {rel}"


# --- the boundaries are load-bearing, not decorative ----------------------


@pytest.mark.parametrize("doc", ["reference", "readme"])
def test_engagement_automation_is_refused_in_both_docs(doc):
    """The no-automation line is the one that protects the user's real account.
    It has to survive edits to either document."""
    text = (REFERENCE if doc == "reference" else README).read_text().lower()
    # Stems, so "messaging"/"connecting"/"applying" all match their base verb.
    for verb in ["connect", "post", "comment", "messag", "follow", "apply"]:
        assert verb in text, f"{doc} no longer names {verb!r} in its automation boundary"
    assert "scrap" in text or "fetch" in text, f"{doc} lost the no-scraping boundary"


def test_keyword_placement_rule_survives_in_the_reference():
    """Keywords in the headline or above the fold is the blandness failure the
    design exists to prevent."""
    text = REFERENCE.read_text().lower()
    assert "headline" in text and "200" in text
    assert "may not" in text or "must not" in text or "never" in text


def test_thin_input_still_yields_candidate_headlines():
    """Eval 3 caught the mode retreating to a fill-in-the-blank template when the
    user supplied almost nothing — a gate wearing different clothes. The
    slot-marked-candidates rule is what stops that, so it has to stay."""
    text = REFERENCE.read_text().lower()
    assert "candidate headlines" in text, "the thin-input headline rule is gone"
    assert "slot" in text, "the bracketed-slot mechanism is gone"


def test_step_0_stays_short():
    """SKILL.md's body loads on EVERY trigger, including plain CV runs that will
    never touch LinkedIn. Step 0 is a tax on those runs, so it has a budget."""
    body = SKILL_MD.read_text()
    step_0 = body.split("### Step 0")[1].split("### Step 1")[0]
    assert len(step_0.splitlines()) <= 25, "Step 0 has grown — move detail into the reference"
