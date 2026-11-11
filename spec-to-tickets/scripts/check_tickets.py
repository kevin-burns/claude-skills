#!/usr/bin/env python3
"""Check a tickets.md breakdown: vertical slices, a walking skeleton first, Musts traced to the PRD,
DSDM's MoSCoW mix per increment, acceptance criteria, the blocking graph, and slice size.

The checks are deterministic: no model, no network. Overrides are the person's, recorded in the
file's front matter (see the accept command).

    check_tickets.py check TICKETS.md
    check_tickets.py accept --tickets TICKETS.md --rule RULE [--slice ID] --turn ID --quote "<their words>"

Run accept only on the person's word: the quote must appear in that turn of theirs (checked through
spec-ready's transcript reader); without spec-ready the override is recorded as attested.
Exit codes: 0 clean or recorded, 1 findings or a usage problem.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from spec_ready_link import load_transcripts
from tickets_md import SIZE_POINTS, Tickets, parse

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


def _read_inputs(tickets_path: Path) -> tuple[Tickets, list[str], str, dict | None]:
    tickets, problems = parse(tickets_path.read_text(encoding="utf-8"))
    prd_ref = str(tickets.front.get("prd") or "")
    prd_path = (tickets_path.parent / prd_ref).resolve() if prd_ref else None
    if prd_path is None or not prd_path.is_file():
        prd_path = tickets_path.parent / "prd.md"
    prd_text = prd_path.read_text(encoding="utf-8") if prd_path.is_file() else ""
    if not prd_text:
        problems.append("line 1: no PRD found (front matter 'prd:' or prd.md beside tickets.md)")
    readiness_path = prd_path.parent / "readiness.json"
    readiness = json.loads(readiness_path.read_text(encoding="utf-8")) if readiness_path.is_file() else None
    return tickets, problems, prd_text, readiness


def _check(args) -> int:
    tickets, problems, prd_text, readiness = _read_inputs(Path(args.tickets))
    findings = [Finding("format", None, p) for p in problems] + run_checks(tickets, prd_text, readiness)
    for f in findings:
        print(f"{f.rule:<10} {f.slice or '-':<6} {f.message}")
    if not findings:
        print("clean: every check passed")
    return 1 if findings else 0


def _record(tickets_path: Path, entry: dict) -> None:
    lines = tickets_path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        lines = ["---\n", "---\n", "\n", *lines]
    close = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    header = next((i for i in range(1, close) if lines[i].split(":", 1)[0].strip() == "accepted"), None)
    item = "  - " + json.dumps(entry, ensure_ascii=False) + "\n"
    if header is None:
        lines[close:close] = ["accepted:\n", item]
    else:
        end = header + 1
        while end < close and lines[end].startswith((" ", "\t")):
            end += 1
        lines[end:end] = [item]
    tickets_path.write_text("".join(lines), encoding="utf-8")


def accept_override(tickets_path: Path, rule: str, slice_id: str | None, turn: str, quote: str, transcripts,
                    env: Mapping[str, str], home: Path, cwd: Path) -> tuple[int, str]:
    entry = {"rule": rule, "slice": slice_id, "turn": turn, "quote": quote}
    if transcripts is None:
        _record(tickets_path, {**entry, "mode": "attested"})
        return 0, "recorded as attested: spec-ready is not installed beside this skill, so the quote was not checked"
    found = transcripts.find_transcript(env, home, cwd)
    if found is None:
        _record(tickets_path, {**entry, "mode": "attested"})
        return 0, "recorded as attested: no readable session transcript, so the quote was not checked"
    turns = {t.id: t for t in transcripts.load_user_turns(found[1], found[0])}
    if turn not in turns:
        return 1, f"turn {turn} is not one of the person's turns"
    if not normalise(quote) or normalise(quote) not in normalise(turns[turn].text):
        return 1, "the quote is not in that turn; quote the person's own words"
    _record(tickets_path, {**entry, "mode": "verified"})
    return 0, "recorded as verified"


def _accept(args) -> int:
    code, message = accept_override(Path(args.tickets), args.rule, args.slice, args.turn, args.quote,
                                    _transcripts, os.environ, Path.home(), Path.cwd())
    print(f"spec-to-tickets: {message}", file=sys.stderr if code else sys.stdout)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a tickets.md breakdown.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("tickets")
    acc = sub.add_parser("accept")
    acc.add_argument("--tickets", required=True)
    acc.add_argument("--rule", required=True, choices=["vertical", "skeleton", "trace", "scope", "mix", "acceptance",
                                                       "blocks", "size"])
    acc.add_argument("--slice")
    acc.add_argument("--turn", required=True)
    acc.add_argument("--quote", required=True)
    args = parser.parse_args(argv)
    return {"check": _check, "accept": _accept}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
