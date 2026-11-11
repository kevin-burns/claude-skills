"""The tickets.md format: parsed forgivingly, because the person will edit it by hand."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from tickets_md import KINDS, MOSCOW, SIZE_POINTS, Criterion, parse

EXAMPLE = """---
source: built here
prd: docs/specs/2026-11-11-dictation/prd.md
spec: docs/specs/2026-11-11-dictation/spec.md
timebox: 1 week
layers: [audio, core, ui]
accepted:
  - {"rule": "mix", "slice": "T2", "turn": "u7", "quote": "fine for week one", "mode": "verified"}
---

## Increment 1 — walking skeleton

### T1 — Dictate one sentence into the focused app
- moscow: Must
- size: M
- layers: [audio, core, ui]
- kind: slice
- traces: "[turn:u1]"
- blocked by: []
- parallel: yes
- acceptance:
  - Speaking a sentence types it at the cursor in TextEdit (proves: user story 1)

### T2 — Settings window
- moscow: could
- size: s
- layers: [core, ui]
- kind: slice
- traces: Proposed: the person has not asked for settings
- blocked by: [T1]
- acceptance:
  - The hotkey can be changed (proves: user story 3)
"""


def test_parses_the_spec_example():
    tickets, problems = parse(EXAMPLE)
    assert problems == []
    assert tickets.front["layers"] == ["audio", "core", "ui"] and tickets.front["timebox"] == "1 week"
    assert tickets.accepted == ({"rule": "mix", "slice": "T2", "turn": "u7", "quote": "fine for week one",
                                 "mode": "verified"},)
    (inc,) = tickets.increments
    assert inc.number == 1 and inc.title == "walking skeleton"
    t1, t2 = inc.slices
    assert (t1.id, t1.title, t1.moscow, t1.size, t1.kind) == ("T1", "Dictate one sentence into the focused app",
                                                              "Must", "M", "slice")
    assert t1.layers == ("audio", "core", "ui") and t1.traces == "[turn:u1]" and t1.parallel is True
    assert t1.acceptance == (Criterion("Speaking a sentence types it at the cursor in TextEdit", "user story 1"),)
    assert t2.blocked_by == ("T1",) and t2.traces.startswith("Proposed:") and t2.parallel is None


def test_moscow_and_size_are_normalised():
    tickets, _ = parse(EXAMPLE)
    t2 = tickets.increments[0].slices[1]
    assert (t2.moscow, t2.size) == ("Could", "S")


def test_wont_spelling_variants():
    for spelling in ("Won't", "Wont", "won’t", "WON'T"):
        tickets, problems = parse(EXAMPLE.replace("moscow: could", f"moscow: {spelling}"))
        assert tickets.increments[0].slices[1].moscow == "Won't" and problems == []


def test_parse_is_forgiving_and_reports_problems():
    broken = EXAMPLE.replace("- size: M\n", "").replace("kind: slice\n- traces: \"[turn:u1]\"",
                                                         "kind: layer\n- traces: \"[turn:u1]\"")
    broken = broken.replace("layers: [core, ui]", "layers: core, ui")
    broken = broken.replace("\n\n### T2", "\n\n\n- stray bullet\n### T2")
    tickets, problems = parse(broken)
    t1, t2 = tickets.increments[0].slices
    assert t1.size == "" and t1.kind == ""
    assert any("size" in p for p in problems) and any("kind" in p for p in problems)
    assert any("layers" in p for p in problems) and t2.layers == ()
    assert all(p.startswith("line ") for p in problems)


def test_front_matter_layers_and_accepted():
    tickets, problems = parse(EXAMPLE.replace("accepted:\n  - {", "accepted:\n  - {not json"))
    assert tickets.accepted == () and any("accepted" in p for p in problems)


def test_constants():
    assert SIZE_POINTS == {"S": 1, "M": 2, "L": 4}
    assert MOSCOW == ("Must", "Should", "Could", "Won't")
    assert KINDS == ("slice", "prefactor", "expand", "migrate", "contract")
