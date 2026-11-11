"""specifics: an acceptance criterion may not add a figure or a name the PRD and spec do not
contain unless it says 'Proposed:'. Both directions are pinned: what it must flag (the three
with-arm misses from the 2026-11-11 eval) and what it must not (the same fact written another way)."""

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))

from check_tickets import check_specifics, figures, names, run_checks
from tickets_md import Criterion, Increment, Slice, Tickets

PRD = """# Dictation

## Goal

Dictation that types where the cursor is on my Mac, so I can write long emails by voice.

## Success check

I use it every day for a week instead of typing, and a reply takes under 2 minutes.
"""
SPEC = "As the user, I want a hotkey that starts and stops dictation within half a second.\n"


def sl(*criteria: str) -> Tickets:
    acceptance = tuple(Criterion(c, "the goal") for c in criteria)
    s = Slice(id="T1", title="T1", moscow="Must", size="S", layers=("a",), kind="slice", traces="",
              acceptance=acceptance, line=1)
    return Tickets({"layers": ["a"]}, (Increment(1, "one", (s,)),))


def flagged(*criteria: str) -> bool:
    return bool(check_specifics(sl(*criteria), PRD, SPEC))


# What it must flag: the eval's misses.

def test_flags_the_eval_misses():
    assert flagged("A five-minute dictation with pauses is typed in full")
    assert flagged("A recorded five-minute email is typed without loss")


def test_known_gap_plain_word_scope_is_not_caught():
    # New scope in plain lowercase words has no surface form a script can see. Pinned so the
    # README's claim stays true: this is left to the person's review and the eval grader.
    assert not flagged("The app starts at login")


def test_flags_digits_units_and_percentages():
    assert flagged("Latency stays under 300 ms")
    assert flagged("Accuracy is at least 95% on the recorded set")
    assert flagged("It types into TextEdit")
    assert flagged("A reply takes under 5 minutes")  # PRD says 2 minutes, not 5


def test_flags_a_figure_with_the_wrong_unit():
    assert flagged("A reply takes under 2 hours")


# What it must not flag: the same fact written another way, and ordinary words.

def test_accepts_figures_in_the_prd_or_spec_written_differently():
    assert not flagged("A reply takes under two minutes")
    assert not flagged("A reply takes under 2 min")
    assert not flagged("A reply takes under 2-minute")
    assert not flagged("Used daily for one week")          # PRD: "for a week"
    assert not flagged("The hotkey responds within 0.5 seconds")  # spec: "half a second"
    assert not flagged("The hotkey responds within half a second")


def test_accepts_names_in_the_inputs_and_sentence_starts():
    assert not flagged("Dictation types at the cursor on the Mac")
    assert not flagged("Pressing the hotkey starts dictation. Pressing it again stops it")
    assert not flagged("I can write a long email by voice")


def test_ignores_ids_and_plain_one():
    assert not flagged("Builds on T1 and user story 2")
    assert not flagged("One sentence spoken appears at the cursor")
    assert not flagged("Pressing one key starts dictation")


def test_proposed_criterion_is_not_flagged():
    assert not flagged("Proposed: a five-minute dictation with pauses is typed in full")


def test_figures_normalise():
    assert figures("a five-minute email") == {(5.0, "minute")}
    assert figures("under 2 mins, and 95 %") == {(2.0, "minute"), (95.0, "percent")}
    assert figures("for a week, an hour") == {(1.0, "week"), (1.0, "hour")}
    assert figures("half a second") == {(0.5, "second")}
    assert figures("T1 and user story 2, increment 3, issue #4") == set()
    assert figures("five sentences") == {(5.0, "")}


def test_names_skip_sentence_starts():
    assert names("Pressing it types into TextEdit. Then Mail opens") == {"textedit", "mail"}


def test_finding_names_what_was_added_and_override_key_is_the_slice():
    [f] = check_specifics(sl("A five-minute dictation in TextEdit"), PRD, SPEC)
    assert f.rule == "specifics" and f.slice == "T1"
    assert "5 minute" in f.message and "TextEdit" in f.message and "Proposed:" in f.message
    accepted = [{"rule": "specifics", "slice": "T1", "turn": "u7", "quote": "five minutes is fine",
                 "mode": "verified"}]
    assert not [x for x in run_checks(sl("A five-minute dictation"), PRD, None, SPEC, accepted=accepted)
                if x.rule == "specifics"]


def test_check_lists_proposed_criteria(tmp_path):
    d = tmp_path / "docs"
    d.mkdir()
    (d / "prd.md").write_text(PRD, encoding="utf-8")
    (d / "tickets.md").write_text("""---
prd: prd.md
layers: [a]
---

## Increment 1 — skeleton

### T1 — One
- moscow: Must
- size: S
- layers: [a]
- kind: slice
- traces: "Dictation that types where the cursor is"
- acceptance:
  - Proposed: a five-minute dictation is typed in full (proves: the goal)
""", encoding="utf-8")
    done = subprocess.run([sys.executable, str(HERE / "scripts" / "check_tickets.py"), "check", str(d / "tickets.md")],
                          capture_output=True, text=True, check=False, env={**os.environ, "HOME": str(tmp_path)})
    assert "proposed" in done.stdout and "five-minute" in done.stdout and "specifics" not in done.stdout
