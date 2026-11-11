#!/usr/bin/env python3
"""Check a tickets.md breakdown: vertical slices, a walking skeleton first, Musts traced to the PRD,
DSDM's MoSCoW mix per increment, acceptance criteria, the blocking graph, and slice size.

The checks are deterministic: no model, no network. Overrides are the person's, recorded in the
file's front matter (see the accept command).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from spec_ready_link import load_transcripts
from tickets_md import SIZE_POINTS, Tickets

MUST_SHARE_LIMIT = 0.60
_TURN = re.compile(r"^\[turn:([^\]\s]+)\]$")
_TYPOGRAPHY = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "–": "-", "—": "-", "−": "-", " ": " ",
})


def _local_normalise(text: str) -> str:
    """Same rule as spec-ready's transcripts.normalise, for when spec-ready is not installed."""
    return " ".join(unicodedata.normalize("NFC", text).translate(_TYPOGRAPHY).split())


_transcripts = load_transcripts()
normalise = _transcripts.normalise if _transcripts else _local_normalise


@dataclass(frozen=True)
class Finding:
    rule: str
    slice: str | None
    message: str


def check_vertical(t: Tickets) -> list[Finding]:
    return [Finding("vertical", s.id, f"{s.id} touches one layer ({', '.join(s.layers) or 'none'}); a slice cuts "
                    "through every layer it needs, or is marked prefactor/expand/migrate/contract")
            for s in t.slices() if s.kind == "slice" and len(s.layers) < 2]


def check_skeleton(t: Tickets) -> list[Finding]:
    layers = set(t.front.get("layers") or [])
    if not t.increments:
        return [Finding("skeleton", None, "no increments")]
    first = t.increments[0]
    for s in first.slices:
        if s.moscow == "Must" and s.kind == "slice" and layers and layers <= set(s.layers):
            return []
    return [Finding("skeleton", None, f"increment {first.number} has no Must slice through every declared layer "
                    f"({', '.join(sorted(layers)) or 'none declared'}): start with a walking skeleton")]


def check_trace(t: Tickets, prd_text: str, readiness: dict | None) -> list[Finding]:
    settled = {r["turn"] for r in (readiness or {}).get("items", []) if r.get("status") == "settled" and r.get("turn")}
    prd = normalise(prd_text)
    findings = []
    for s in t.slices():
        if s.moscow != "Must":
            continue
        traces = s.traces.strip()
        if not traces or traces.startswith("Proposed:"):
            findings.append(Finding("trace", s.id, f"Must {s.id} traces to nothing in the PRD"))
        elif match := _TURN.match(traces):
            if match.group(1) not in settled:
                findings.append(Finding("trace", s.id, f"Must {s.id} cites turn {match.group(1)}, which is not a "
                                        "settled turn in readiness.json"))
        else:
            quote = normalise(traces.strip("\"'“”"))
            if not quote or quote not in prd:
                findings.append(Finding("trace", s.id, f"Must {s.id} quotes text that is not in the PRD"))
    return findings


def check_scope(t: Tickets) -> list[Finding]:
    return [Finding("scope", s.id, f"{s.id} traces to nothing and is not marked 'Proposed:'")
            for s in t.slices() if s.moscow != "Won't" and not s.traces.strip()]


def check_mix(t: Tickets) -> list[Finding]:
    findings = []
    for inc in t.increments:
        live = [s for s in inc.slices if s.moscow in ("Must", "Should", "Could") and s.size in SIZE_POINTS]
        total = sum(SIZE_POINTS[s.size] for s in live)
        if total == 0:
            continue
        must = sum(SIZE_POINTS[s.size] for s in live if s.moscow == "Must")
        if must / total > MUST_SHARE_LIMIT:
            findings.append(Finding("mix", None, f"increment {inc.number}: Must effort is {must}/{total} "
                                    f"({must / total:.0%}), over DSDM's 60%"))
        if not any(s.moscow == "Could" for s in live):
            findings.append(Finding("mix", None, f"increment {inc.number} has no Could: nothing to drop if the "
                                    "timebox runs short"))
    return findings


def check_acceptance(t: Tickets) -> list[Finding]:
    findings = []
    for s in t.slices():
        if not s.acceptance:
            findings.append(Finding("acceptance", s.id, f"{s.id} has no acceptance criteria"))
        elif any(not c.proves for c in s.acceptance):
            findings.append(Finding("acceptance", s.id, f"{s.id} has a criterion that names nothing it proves"))
    return findings


def check_blocks(t: Tickets) -> list[Finding]:
    graph = {s.id: list(s.blocked_by) for s in t.slices()}
    findings = [Finding("blocks", sid, f"{sid} is blocked by {b}, which does not exist")
                for sid, blockers in graph.items() for b in blockers if b not in graph]
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        path.append(node)
        for nxt in graph.get(node, []):
            if nxt not in graph:
                continue
            if state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt]
            if state.get(nxt) is None and (cycle := visit(nxt)):
                return cycle
        state[node] = 2
        path.pop()
        return None

    for node in graph:
        if state.get(node) is None and (cycle := visit(node)):
            findings.append(Finding("blocks", None, "blocking cycle: " + " -> ".join(cycle)))
            break
    return findings


def check_size(t: Tickets) -> list[Finding]:
    return [Finding("size", s.id, f"{s.id} is L: say in its note why it is still one context window and one "
                    "pull request, or split it") for s in t.slices() if s.size == "L" and not s.note.strip()]


def run_checks(t: Tickets, prd_text: str, readiness: dict | None) -> list[Finding]:
    findings = (check_vertical(t) + check_skeleton(t) + check_trace(t, prd_text, readiness) + check_scope(t)
                + check_mix(t) + check_acceptance(t) + check_blocks(t) + check_size(t))
    accepted = {(a.get("rule"), a.get("slice")) for a in t.accepted}
    return [f for f in findings if (f.rule, f.slice) not in accepted]
