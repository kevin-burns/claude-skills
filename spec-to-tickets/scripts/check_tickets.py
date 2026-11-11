#!/usr/bin/env python3
"""Check a tickets.md breakdown: vertical slices, a walking skeleton first, Musts traced to the PRD,
DSDM's MoSCoW mix and contingency per increment, acceptance criteria, the blocking graph, and size.

The checks are deterministic: no model, no network. Overrides are the person's, recorded in the
file's front matter by the accept command, each with the turn and the words in which they decided.

    check_tickets.py check TICKETS.md
    check_tickets.py accept --tickets TICKETS.md --rule RULE [--slice ID] --turn ID --quote "<their words>"

Run accept only on the person's word: the quote must appear in that turn of theirs (checked through
spec-ready's transcript reader). Without spec-ready or a readable transcript the override is
recorded as attested, and check then exits 2 until the person has seen it.
Exit codes for check: 0 clean, 1 findings or a usage problem, 2 clean only because of attested overrides.
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
MIN_QUOTE_WORDS = 4
RULES = ("vertical", "skeleton", "trace", "scope", "mix", "contingency", "acceptance", "blocks", "size")
MUST_SECTIONS = ("goal", "success check", "anti-goal")          # what a Must may trace to
NEVER_SECTIONS = ("non-goals", "out of scope", "assumptions", "open questions", "risks")
NEVER_PREFIXES = ("assumption:", "open question:", "proposed:")
MUST_ITEMS = ("goal", "success_check", "anti_goal")
_TURN = re.compile(r"^\[turn:([^\]\s]+)\]$")
_CITATION = re.compile(r"\[turn:[^\]]*\]")
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


def _sections(text: str) -> list[tuple[str, str]]:
    """(lower-case heading, line) for every non-heading line; citations removed."""
    out, current = [], ""
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
        elif line.strip() and not line.startswith("#"):
            out.append((current, _CITATION.sub("", line)))
    return out


def _usable(line: str) -> bool:
    return not re.sub(r"^\s*([-*]|\d+\.)\s*", "", line).lower().startswith(NEVER_PREFIXES)


def _must_text(prd: str) -> str:
    """The PRD text a Must may quote: its goal, success check and anti-goal when it has those
    headings, otherwise everything outside non-goals, assumptions, open questions and risks."""
    lines = _sections(prd)
    if any(section in MUST_SECTIONS for section, _ in lines):
        chosen = [line for section, line in lines if section in MUST_SECTIONS and _usable(line)]
    else:
        chosen = [line for section, line in lines if section not in NEVER_SECTIONS and _usable(line)]
    return normalise(" ".join(chosen))


def _any_text(*texts: str) -> str:
    return normalise(" ".join(line for text in texts for section, line in _sections(text)
                              if section not in NEVER_SECTIONS and _usable(line)))


def _quote(traces: str) -> str:
    return normalise(traces.strip().strip("\"'“”"))


def _enough(quote: str) -> bool:
    return len(quote.split()) >= MIN_QUOTE_WORDS


def check_vertical(t: Tickets) -> list[Finding]:
    return [Finding("vertical", s.id, f"{s.id} touches one layer ({', '.join(s.layers) or 'none'}); a slice cuts "
                    "through every layer it needs, or is marked prefactor/expand/migrate/contract")
            for s in t.slices() if s.kind == "slice" and len(set(s.layers)) < 2]


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
    readiness = readiness or {}
    verified = readiness.get("mode") == "verified"
    must_turns = {r["turn"] for r in readiness.get("items", [])
                  if r.get("status") == "settled" and r.get("item") in MUST_ITEMS and r.get("turn")}
    allowed = _must_text(prd_text)
    findings = []
    for s in t.slices():
        if s.moscow != "Must":
            continue
        traces = s.traces.strip()
        if not traces or traces.startswith("Proposed:"):
            findings.append(Finding("trace", s.id, f"Must {s.id} traces to nothing in the PRD (a Must cannot be "
                                    "Proposed:)"))
        elif match := _TURN.match(traces):
            if not verified or match.group(1) not in must_turns:
                findings.append(Finding("trace", s.id, f"Must {s.id} cites turn {match.group(1)}, which is not the "
                                        "person's settled goal, success check or anti-goal in a verified "
                                        "readiness.json"))
        else:
            quote = _quote(traces)
            if not _enough(quote):
                findings.append(Finding("trace", s.id, f"Must {s.id} quotes fewer than {MIN_QUOTE_WORDS} words"))
            elif quote not in allowed:
                findings.append(Finding("trace", s.id, f"Must {s.id} quotes text that is not in the PRD's goal, "
                                        "success check or anti-goal"))
    return findings


def check_scope(t: Tickets, prd_text: str = "", spec_text: str = "", readiness: dict | None = None) -> list[Finding]:
    readiness = readiness or {}
    turns = set(readiness.get("person_turns", [])) | {r["turn"] for r in readiness.get("items", [])
                                                      if r.get("status") == "settled" and r.get("turn")}
    text = _any_text(prd_text, spec_text)
    findings = []
    for s in t.slices():
        if s.moscow in ("Won't", "Must"):
            continue  # Musts are held to the stricter trace check
        traces = s.traces.strip()
        if not traces:
            findings.append(Finding("scope", s.id, f"{s.id} traces to nothing and is not marked 'Proposed:'"))
        elif traces.startswith("Proposed:"):
            continue
        elif match := _TURN.match(traces):
            if match.group(1) not in turns:
                findings.append(Finding("scope", s.id, f"{s.id} cites turn {match.group(1)}, which is not one of "
                                        "the person's turns"))
        elif not _enough(_quote(traces)) or _quote(traces) not in text:
            findings.append(Finding("scope", s.id, f"{s.id} quotes text that is not in the PRD or spec; trace it "
                                    "properly or mark it 'Proposed:'"))
    return findings


def check_mix(t: Tickets) -> list[Finding]:
    findings = []
    for inc in t.increments:
        live = [s for s in inc.slices if s.moscow in ("Must", "Should", "Could") and s.size in SIZE_POINTS]
        total = sum(SIZE_POINTS[s.size] for s in live)
        if total == 0:
            continue
        key = f"increment-{inc.number}"
        must = sum(SIZE_POINTS[s.size] for s in live if s.moscow == "Must")
        if must / total > MUST_SHARE_LIMIT:
            findings.append(Finding("mix", key, f"increment {inc.number}: Must effort is {must}/{total} "
                                    f"({must / total:.0%}), over DSDM's 60%"))
        if not any(s.moscow == "Could" for s in live):
            findings.append(Finding("contingency", key, f"increment {inc.number} has no Could: nothing to drop if "
                                    "the timebox runs short"))
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
    graph: dict[str, list[str]] = {}
    for s in t.slices():
        graph.setdefault(s.id, []).extend(s.blocked_by)
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


def all_findings(t: Tickets, prd_text: str, readiness: dict | None, spec_text: str = "") -> list[Finding]:
    return (check_vertical(t) + check_skeleton(t) + check_trace(t, prd_text, readiness)
            + check_scope(t, prd_text, spec_text, readiness) + check_mix(t) + check_acceptance(t) + check_blocks(t)
            + check_size(t))


def valid_override(entry: dict) -> bool:
    return (entry.get("rule") in RULES and bool(str(entry.get("turn") or "").strip())
            and bool(str(entry.get("quote") or "").strip()) and entry.get("mode") in ("verified", "attested"))


def run_checks(t: Tickets, prd_text: str, readiness: dict | None, spec_text: str = "",
               accepted: list[dict] | None = None) -> list[Finding]:
    """Findings left after the person's overrides. Only complete overrides count."""
    overrides = [a for a in (t.accepted if accepted is None else accepted) if valid_override(a)]
    waived = {(a["rule"], a.get("slice")) for a in overrides}
    return [f for f in all_findings(t, prd_text, readiness, spec_text) if (f.rule, f.slice) not in waived]


def _read(path: Path, problems: list[str], what: str) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except OSError as error:
        problems.append(f"line 1: cannot read the {what}: {error}")
        return ""


def _read_inputs(tickets_path: Path) -> tuple[Tickets, list[str], str, str, dict | None]:
    tickets, problems = parse(tickets_path.read_text(encoding="utf-8"))

    def beside(key: str, default: str) -> Path:
        ref = str(tickets.front.get(key) or "")
        path = (tickets_path.parent / ref) if ref else tickets_path.parent / default
        return path if path.is_file() else tickets_path.parent / default

    prd_path = beside("prd", "prd.md")
    prd_text = _read(prd_path, problems, "PRD")
    if not prd_text:
        problems.append("line 1: no PRD found (front matter 'prd:' or prd.md beside tickets.md)")
    spec_text = _read(beside("spec", "spec.md"), problems, "spec")
    readiness = None
    readiness_path = prd_path.parent / "readiness.json"
    if readiness_path.is_file():
        try:
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            problems.append("line 1: readiness.json beside the PRD is not valid JSON")
    return tickets, problems, prd_text, spec_text, readiness


def _person_turns() -> dict[str, str] | None:
    if _transcripts is None:
        return None
    found = _transcripts.find_transcript(os.environ, Path.home(), Path.cwd())
    if found is None:
        return None
    return {turn.id: turn.text for turn in _transcripts.load_user_turns(found[1], found[0])}


def _check(args) -> int:
    tickets, problems, prd_text, spec_text, readiness = _read_inputs(Path(args.tickets))
    turns = _person_turns()
    overrides = []
    for entry in tickets.accepted:
        if not valid_override(entry):
            problems.append(f"line 1: override {json.dumps(entry)} lacks a rule, turn, quote or mode; not applied")
        elif entry["mode"] == "verified" and turns is not None and (
                entry["turn"] not in turns or normalise(entry["quote"]) not in normalise(turns[entry["turn"]])):
            problems.append(f"line 1: override for {entry['rule']} {entry.get('slice') or ''} no longer matches the "
                            "person's turn; not applied")
        else:
            overrides.append(entry)
    findings = [Finding("format", None, p) for p in problems]
    findings += run_checks(tickets, prd_text, readiness, spec_text, accepted=overrides)
    for f in findings:
        print(f"{f.rule:<11} {f.slice or '-':<13} {f.message}")
    for o in overrides:
        rechecked = "" if o["mode"] == "attested" or turns is not None else " (not re-checked: no transcript)"
        print(f"{'override':<11} {o['rule']} {o.get('slice') or '-'} {o['mode']}{rechecked}: \"{o['quote']}\"")
    for s in tickets.slices():
        if s.traces.strip().startswith("Proposed:"):
            print(f"{'proposed':<11} {s.id:<13} {s.traces.strip()}")
    if findings:
        return 1
    if any(o["mode"] == "attested" for o in overrides):
        print("clean, but only because of attested overrides: show them to the person")
        return 2
    print("clean: every check passed")
    return 0


def _record(tickets_path: Path, entry: dict) -> None:
    lines = tickets_path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        lines = ["---\n", "---\n", "\n", *lines]
    close = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if close is None:
        raise ValueError("the front matter is not closed with ---")
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
    try:
        tickets, problems, prd_text, spec_text, readiness = _read_inputs(tickets_path)
        if any("front matter is not closed" in p for p in problems):
            return 1, "the front matter of tickets.md is not closed with ---; fix it first"
        current = {(f.rule, f.slice) for f in all_findings(tickets, prd_text, readiness, spec_text)}
        if (rule, slice_id) not in current:
            return 1, f"no current finding for rule {rule} on {slice_id or 'the whole breakdown'}; nothing to accept"
        if transcripts is None:
            _record(tickets_path, {**entry, "mode": "attested"})
            return 0, ("recorded as attested: spec-ready is not installed beside this skill, so the quote was not "
                       "checked; tell the person")
        found = transcripts.find_transcript(env, home, cwd)
        if found is None:
            _record(tickets_path, {**entry, "mode": "attested"})
            return 0, ("recorded as attested: no readable session transcript, so the quote was not checked; tell "
                       "the person")
        turns = {t.id: t for t in transcripts.load_user_turns(found[1], found[0])}
        if turn not in turns:
            return 1, f"turn {turn} is not one of the person's turns"
        if not normalise(quote) or normalise(quote) not in normalise(turns[turn].text):
            return 1, "the quote is not in that turn; quote the person's own words"
        _record(tickets_path, {**entry, "mode": "verified"})
        return 0, "recorded as verified"
    except (OSError, ValueError) as error:
        return 1, f"could not record the override: {error}"


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
    acc.add_argument("--rule", required=True, choices=RULES)
    acc.add_argument("--slice", help="a slice id, or increment-N for mix and contingency")
    acc.add_argument("--turn", required=True)
    acc.add_argument("--quote", required=True)
    args = parser.parse_args(argv)
    return {"check": _check, "accept": _accept}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
