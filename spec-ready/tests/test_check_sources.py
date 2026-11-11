"""PRD sources check: every decision line cites a settled turn; no figure without a source."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_sources import check_prd, check_spec

READY = {"mode": "verified", "verification": "independent", "items": [
    {"item": "goal", "status": "settled", "turn": "u1"},
    {"item": "anti_goal", "status": "settled", "turn": "u2"},
    {"item": "risks", "status": "guessed", "turn": None},
]}


def prd(body: str, mode: str = "verified", verifier: str = "independent") -> str:
    return f"# Dictation\n\nReadiness: {mode}\nVerifier: {verifier}\n\n{body}"


GOOD = prd("""## Problem

Typing long emails is slow. [turn:u1]

## Goal

- Dictation that types where the cursor is. [turn:u1]

## Anti-goal

A clone of an existing app. [turn:u2]

## Assumptions

- Assumption: most use is on a laptop microphone.
""")


def test_cited_prd_passes():
    assert check_prd(GOOD, READY) == []


def test_unknown_turn_id_flagged():
    findings = check_prd(GOOD.replace("[turn:u2]", "[turn:u9]"), READY)
    assert any("u9" in f for f in findings)


def test_uncited_decision_line_flagged():
    findings = check_prd(GOOD.replace("Typing long emails is slow. [turn:u1]", "Typing long emails is slow."), READY)
    assert any("no citation" in f for f in findings)


def test_unsourced_figure_flagged():
    text = GOOD.replace("## Assumptions", "## Notes\n\nIt saves 40 minutes a day.\n\n## Assumptions")
    assert any("unsourced figure" in f for f in check_prd(text, READY))


def test_figure_in_cited_sentence_ok():
    text = GOOD.replace("A clone of an existing app. [turn:u2]", "A clone of the top 3 apps. [turn:u2]")
    assert check_prd(text, READY) == []


def test_assumptions_need_prefix():
    text = GOOD.replace("- Assumption: most use", "- most use")
    assert any("Assumption:" in f for f in check_prd(text, READY))


def test_mode_header_must_match():
    assert any("Readiness" in f for f in check_prd(GOOD.replace("Readiness: verified", "Readiness: attested"), READY))
    assert any("Readiness" in f for f in check_prd(GOOD.replace("Readiness: verified\n", ""), READY))


def test_verifier_header_must_match():
    # Review finding 7: a self-assessed check must say so in the PRD.
    assert check_prd(GOOD, READY) == []
    self_assessed = {**READY, "verification": "self-assessed"}
    assert any("Verifier" in f for f in check_prd(GOOD, self_assessed))
    assert check_prd(GOOD.replace("Verifier: independent", "Verifier: self-assessed"), self_assessed) == []
    assert any("Verifier" in f for f in check_prd(GOOD.replace("Verifier: independent\n", ""), READY))


def test_open_questions_section_is_allowed():
    # Eval 2026-11-11 (S8): an open question was forced into an "Assumption:" line.
    question = "## Open questions\n\n- Open question: what makes it different from existing apps?\n\n"
    text = GOOD.replace("## Assumptions", question + "## Assumptions")
    assert check_prd(text, READY) == []
    bad = GOOD.replace("## Assumptions", "## Open questions\n\n- what makes it different?\n\n## Assumptions")
    assert any("Open question:" in f for f in check_prd(bad, READY))


SPEC = """# Dictation — spec

## Solution

A menu-bar app that types dictated text at the cursor.

## User stories

1. As a person who writes long emails by voice, I want text typed where my cursor is, \
so that I can stay in my mail app. [turn:u1]

## Implementation decisions

- The audio driver sits behind an interface outside the core library.

## Out of scope

- Meeting transcription. [turn:u2]
"""


def test_spec_stories_and_scope_cite_or_are_marked_proposed():
    # Eval 2026-11-11 (S8): the spec added a user story and an out-of-scope line nobody stated.
    assert check_spec(SPEC, READY) == []
    invented = SPEC.replace("- Meeting transcription. [turn:u2]", "- Anything beyond dictating text.")
    assert any("Out of scope" in f or "out of scope" in f for f in check_spec(invented, READY))
    proposed = SPEC.replace("- Meeting transcription. [turn:u2]", "- Proposed: anything beyond dictating text.")
    assert check_spec(proposed, READY) == []
    story = SPEC.replace("so that I can stay in my mail app. [turn:u1]", "so that I can stay in my mail app.")
    assert any("user stor" in f for f in check_spec(story, READY))


def test_cli_checks_the_spec_too(tmp_path):
    import json
    import subprocess

    script = Path(__file__).resolve().parents[1] / "scripts" / "check_sources.py"
    (tmp_path / "prd.md").write_text(GOOD, encoding="utf-8")
    (tmp_path / "spec.md").write_text(SPEC.replace(" [turn:u2]", ""), encoding="utf-8")
    (tmp_path / "readiness.json").write_text(json.dumps(READY), encoding="utf-8")
    done = subprocess.run([sys.executable, str(script), str(tmp_path / "prd.md"), str(tmp_path / "readiness.json"),
                           "--spec", str(tmp_path / "spec.md")], capture_output=True, text=True, check=False)
    assert done.returncode == 1 and "spec.md" in done.stdout


def test_risks_section_cites_turns():
    # Full eval 2026-11-11 (S5): a stated risk had to be filed as an Assumption.
    ready = {**READY, "items": READY["items"] + [{"item": "risks", "status": "settled", "turn": "u3"}]}
    text = GOOD.replace("## Assumptions", "## Risks\n\n- Latency on older Macs. [turn:u3]\n\n## Assumptions")
    assert check_prd(text, ready) == []
    uncited = GOOD.replace("## Assumptions", "## Risks\n\n- Latency on older Macs.\n\n## Assumptions")
    assert any("no citation" in f for f in check_prd(uncited, ready))


def test_a_figure_may_cite_any_of_the_persons_turns():
    # Full eval 2026-11-11 (S7): the person's own figure, given in a later turn, could not be cited.
    ready = {**READY, "person_turns": ["u1", "u2", "u9"]}
    note = "## Notes\n\nThe person expects it to save about 40 minutes a day. [turn:u9]\n\n"
    text = GOOD.replace("## Assumptions", note + "## Assumptions")
    assert check_prd(text, ready) == []
    decision = GOOD.replace("Typing long emails is slow. [turn:u1]", "Typing long emails is slow. [turn:u9]")
    assert any("not a settled turn" in f for f in check_prd(decision, ready))
