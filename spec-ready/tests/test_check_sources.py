"""PRD sources check: every decision line cites a settled turn; no figure without a source."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_sources import check_prd

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
