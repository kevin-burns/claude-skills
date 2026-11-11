"""The checks: each fails what it should, passes what it should, and drops what the person accepted."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_tickets import (
    _local_normalise,
    check_acceptance,
    check_blocks,
    check_mix,
    check_scope,
    check_size,
    check_skeleton,
    check_trace,
    check_vertical,
    normalise,
    run_checks,
)
from tickets_md import Criterion, Increment, Slice, Tickets

PRD = "## Goal\n\nDictation that types where the cursor is, so I can write long emails by voice.\n"
READY = {"mode": "verified", "items": [{"item": "goal", "status": "settled", "turn": "u1"}]}
OK = (Criterion("types at the cursor", "user story 1"),)
LAYERS = ["audio", "core", "ui"]


def sl(id_, moscow="Must", size="M", layers=("audio", "core", "ui"), kind="slice", traces="[turn:u1]",
       blocked=(), acceptance=OK, note=""):
    return Slice(id=id_, title=id_, moscow=moscow, size=size, layers=tuple(layers), kind=kind, traces=traces,
                 blocked_by=tuple(blocked), acceptance=acceptance, note=note, line=1)


def tickets(*increments, accepted=()):
    incs = tuple(Increment(n, f"inc {n}", tuple(s)) for n, s in enumerate(increments, start=1))
    return Tickets({"layers": LAYERS}, incs, tuple(accepted))


def rules(findings):
    return [(f.rule, f.slice) for f in findings]


GOOD = tickets([sl("T1", size="S"), sl("T2", moscow="Should", size="S"), sl("T3", moscow="Could", size="S",
                                                                           traces="Proposed: nice to have")])


def test_good_breakdown_is_clean():
    assert run_checks(GOOD, PRD, READY) == []


def test_vertical():
    assert rules(check_vertical(tickets([sl("T1", layers=["core"])]))) == [("vertical", "T1")]
    assert check_vertical(GOOD) == []


def test_prefactor_is_exempt_from_vertical():
    for kind in ("prefactor", "expand", "migrate", "contract"):
        assert check_vertical(tickets([sl("T1", layers=["core"], kind=kind)])) == []


def test_skeleton():
    no_full_must = tickets([sl("T1", layers=["audio", "core"]), sl("T2", moscow="Could", layers=LAYERS)])
    assert rules(check_skeleton(no_full_must)) == [("skeleton", None)]
    assert check_skeleton(GOOD) == []
    assert rules(check_skeleton(Tickets({"layers": LAYERS}, ()))) == [("skeleton", None)]


def test_trace():
    assert rules(check_trace(tickets([sl("T1", traces="")]), PRD, READY)) == [("trace", "T1")]
    assert rules(check_trace(tickets([sl("T1", traces="[turn:u9]")]), PRD, READY)) == [("trace", "T1")]
    assert rules(check_trace(tickets([sl("T1", traces="[turn:u1]")]), PRD, None)) == [("trace", "T1")]
    quoted = '"Dictation that types where the cursor is"'
    assert check_trace(tickets([sl("T1", traces=quoted)]), PRD, None) == []
    invented = '"Dictation that also translates"'
    assert rules(check_trace(tickets([sl("T1", traces=invented)]), PRD, None)) == [("trace", "T1")]
    assert check_trace(tickets([sl("T1", moscow="Could", traces="")]), PRD, READY) == []


def test_trace_quote_normalises_typography():
    prd = "## Goal\n\nIt’s for “long emails” – by voice.\n"
    assert check_trace(tickets([sl("T1", traces='"It\'s for "long emails" - by voice"')]), prd, None) == []


def test_normalise_matches_spec_ready_when_present():
    for text in ["it’s  “done” – now", "  a\n\tb  "]:
        assert normalise(text) == _local_normalise(text)


def test_scope():
    assert rules(check_scope(tickets([sl("T1", moscow="Could", traces="")]), PRD)) == [("scope", "T1")]
    assert check_scope(tickets([sl("T1", moscow="Could", traces="Proposed: polish")]), PRD) == []


def test_mix_boundary_at_sixty_percent():
    # 3 of 5 points Must passes; 4 of 6 fails.
    ok = tickets([sl("T1", size="S"), sl("T2", size="M"), sl("T3", moscow="Should", size="S"),
                  sl("T4", moscow="Could", size="S")])
    assert check_mix(ok) == []
    over = tickets([sl("T1", size="M"), sl("T2", size="M"), sl("T3", moscow="Should", size="S"),
                    sl("T4", moscow="Could", size="S")])
    assert rules(check_mix(over)) == [("mix", "increment-1")]


def test_mix_needs_a_could():
    assert any("Could" in f.message for f in check_mix(tickets([sl("T1", size="S"), sl("T2", moscow="Should",
                                                                                       size="L")])))


def test_mix_ignores_wont_and_empty_increments():
    assert check_mix(tickets([sl("T1", moscow="Won't", size="L")], [])) == []
    with_wont = tickets([sl("T1", size="S"), sl("T2", moscow="Could", size="S"), sl("T3", moscow="Won't", size="L")])
    assert rules(check_mix(with_wont)) == []


def test_acceptance():
    assert rules(check_acceptance(tickets([sl("T1", acceptance=())]))) == [("acceptance", "T1")]
    vague = (Criterion("works", ""),)
    assert rules(check_acceptance(tickets([sl("T1", acceptance=vague)]))) == [("acceptance", "T1")]


def test_blocks_unknown_id():
    assert rules(check_blocks(tickets([sl("T1", blocked=["T9"])]))) == [("blocks", "T1")]


def test_blocks_reports_the_cycle_path():
    findings = check_blocks(tickets([sl("T1", blocked=["T2"]), sl("T2", blocked=["T3"]), sl("T3", blocked=["T1"])]))
    assert len(findings) == 1 and "T1 -> T2 -> T3 -> T1" in findings[0].message


def test_size():
    assert rules(check_size(tickets([sl("T1", size="L")]))) == [("size", "T1")]
    assert check_size(tickets([sl("T1", size="L", note="one context window: a single pipeline")])) == []


def test_accepted_overrides_drop_matching_findings():
    over = tickets([sl("T1", size="L", note="x"), sl("T2", moscow="Could", size="S")],
                   accepted=[{"rule": "mix", "slice": "increment-1", "turn": "u7", "quote": "fine",
                              "mode": "verified"}])
    assert [f.rule for f in run_checks(over, PRD, READY)] == []
