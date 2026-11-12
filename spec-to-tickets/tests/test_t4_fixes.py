"""T4 (2026-11-12) fixes: unconfirmed proposals cannot pad the Must share or stand in as contingency;
a proposal the person confirmed cites their turn; heavy Musts are offered to the person to split."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))

from check_tickets import check_mix, split_candidates
from tickets_md import Criterion, Increment, Slice, Tickets

OK = (Criterion("works", "the goal"),)


def sl(id_, moscow="Must", size="S", traces='"a quoted line of the PRD"'):
    return Slice(id=id_, title=id_, moscow=moscow, size=size, layers=("a",), kind="slice", traces=traces,
                 acceptance=OK, line=1)


def inc(*slices, n=1):
    return Increment(n, f"inc {n}", tuple(slices))


# Fix 1: a Proposed slice counts toward neither the mix nor contingency.

def test_proposed_could_does_not_pad_the_must_share():
    # T4's shape: 4 Must of 7 is 57% only with an unconfirmed 1-point export in the denominator.
    padded = Tickets({}, (inc(sl("T1", size="M"), sl("T2", size="M"), sl("T3", "Should", "M"),
                              sl("T4", "Could", "S", traces="Proposed: spreadsheet export")),))
    found = {(f.rule, f.slice) for f in check_mix(padded)}
    assert ("mix", "increment-1") in found and ("contingency", "increment-1") in found


def test_traced_could_still_counts():
    real = Tickets({}, (inc(sl("T1", size="M"), sl("T2", size="M"), sl("T3", "Should", "M"),
                            sl("T4", "Could", "S", traces='"see the week ahead so gaps show early"')),))
    assert check_mix(real) == []


def test_mix_message_says_proposals_were_left_out():
    padded = Tickets({}, (inc(sl("T1", size="M"), sl("T4", "Could", "S", traces="Proposed: x")),))
    assert any("Proposed" in f.message for f in check_mix(padded) if f.rule == "mix")


# Fix 3: heavy Musts are named for the person to consider splitting; advice only.

def test_split_candidates_name_large_musts_and_the_heaviest_over_the_limit():
    t = Tickets({}, (inc(sl("T1", size="L", traces='"q"'), sl("T2", "Could")),
                     inc(sl("T3", size="M"), sl("T4", size="S"), sl("T5", "Could"), n=2)))
    ids = [sid for sid, _ in split_candidates(t)]
    assert ids == ["T1", "T3"]  # T1 is L; increment 2 is 3 of 4 Must and T3 is its heaviest Must


def test_no_split_advice_for_a_balanced_plan_of_small_musts():
    assert split_candidates(Tickets({}, (inc(sl("T1"), sl("T2", "Should"), sl("T3", "Could")),))) == []


# Fix 2: a proposal the person confirmed cites their turn, read from the transcript when there is no
# readiness.json; check prints split advice without changing the exit code.

TICKETS = """---
prd: prd.md
layers: [a, b]
---

## Increment 1 — skeleton

### T1 — Sign up
- moscow: Must
- size: S
- layers: [a, b]
- kind: slice
- traces: "Volunteers sign up for food-bank shifts"
- acceptance:
  - A volunteer signs up (proves: the goal)

### T2 — Export
- moscow: Could
- size: S
- layers: [a, b]
- kind: slice
- traces: [turn:u7]
- acceptance:
  - The rota downloads (proves: the person's request)

### T3 — Day view
- moscow: Should
- size: S
- layers: [a, b]
- kind: slice
- traces: "the coordinator sees each day's rota without phoning round"
- acceptance:
  - Today's rota shows (proves: the goal)
"""
PRD = "## Goal\n\nVolunteers sign up for food-bank shifts and drop out of them online, and the coordinator " \
      "sees each day's rota without phoning round.\n"


def test_confirmed_proposal_cites_a_transcript_turn_without_readiness(tmp_path):
    repo = tmp_path / "repo"
    d = repo / "docs"
    d.mkdir(parents=True)
    (d / "prd.md").write_text(PRD, encoding="utf-8")
    (d / "tickets.md").write_text(TICKETS, encoding="utf-8")
    slug = re.sub(r"[^A-Za-z0-9-]", "-", str(repo.resolve()))
    t = tmp_path / ".claude" / "projects" / slug / "s.jsonl"
    t.parent.mkdir(parents=True)
    t.write_text(json.dumps({"type": "user", "uuid": "u7", "message": {"role": "user",
                                                                     "content": "Yes, keep the export."}}) + "\n")
    env = {**os.environ, "HOME": str(tmp_path), "CLAUDE_CODE_SESSION_ID": "s"}
    run = subprocess.run([sys.executable, str(HERE / "scripts" / "check_tickets.py"), "check", str(d / "tickets.md")],
                         capture_output=True, text=True, check=False, env=env, cwd=repo)
    assert run.returncode == 0, run.stdout
    ghost = TICKETS.replace("[turn:u7]", "[turn:u9]")
    (d / "tickets.md").write_text(ghost, encoding="utf-8")
    run = subprocess.run([sys.executable, str(HERE / "scripts" / "check_tickets.py"), "check", str(d / "tickets.md")],
                         capture_output=True, text=True, check=False, env=env, cwd=repo)
    assert run.returncode == 1 and "u9" in run.stdout


def test_check_prints_split_advice_without_failing(tmp_path):
    d = tmp_path / "docs"
    d.mkdir()
    (d / "prd.md").write_text(PRD, encoding="utf-8")
    big = TICKETS.replace("- size: S\n- layers: [a, b]\n- kind: slice\n- traces: \"Volunteers",
                          "- size: L\n- layers: [a, b]\n- kind: slice\n- note: one pull request\n"
                          "- traces: \"Volunteers")
    big = big.replace("[turn:u7]", '"sees each day\'s rota without phoning round"')
    big = big.replace("- moscow: Should\n- size: S", "- moscow: Should\n- size: M")
    (d / "tickets.md").write_text(big, encoding="utf-8")
    run = subprocess.run([sys.executable, str(HERE / "scripts" / "check_tickets.py"), "check", str(d / "tickets.md")],
                         capture_output=True, text=True, check=False, env={**os.environ, "HOME": str(tmp_path)})
    assert "split?" in run.stdout and "T1" in run.stdout and run.returncode == 0, run.stdout
