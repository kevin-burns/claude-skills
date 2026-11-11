#!/usr/bin/env python3
"""spec-ready gate: is the person's plan ready to be written up as a PRD and spec?

The agent proposes, per item, which of the person's turns states it. This script finds the
session transcript itself, checks the turn exists and is the person's, asks verifiers it chooses,
applies the quote rule, re-checks turn hashes from the previous run, and writes readiness.json.

    gate.py turns                                     list the person's turns with their ids
    gate.py check --proposals P.json --out DIR [--answers A.json --answers-from subagent|session-model]
    gate.py brief --item KEY --turn ID                the script-built brief for a subagent
    gate.py override --out DIR --item KEY --turn ID --quote "<the person's words>" [--answer yes|no]
    gate.py accept-attested --out DIR --reason "<the person's words>"

Run it from the repository root. Exit codes for check: 0 ready; 1 items open or a usage problem;
2 no readable transcript (attested: nothing is settled); 4 no verifier could run.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from items import Item, ItemsError, load_items
from transcripts import Turn, find_transcript, load_user_turns, normalise, turn_hash
from verifiers import (
    AnswerFileVerifier,
    Verdict,
    Verifier,
    apply_quote_rule,
    build_brief,
    combine,
    select_verifiers,
)

READINESS = "readiness.json"
_RANK = {None: 0, "unsure": 1, "no": 2, "yes": 3}
EXIT_READY, EXIT_OPEN, EXIT_ATTESTED, EXIT_UNAVAILABLE = 0, 1, 2, 4


def _verdict_dict(v: Verdict) -> dict:
    return {"answer": v.answer, "p": v.p, "span": v.span, "verifier": v.verifier, "reason": v.reason,
            "error": v.error}


def _previous_rows(previous: dict | None) -> dict[str, dict]:
    return {row["item"]: row for row in (previous or {}).get("items", [])}


def _carried_override(before: dict | None, row: dict, turns: dict[str, Turn]) -> dict | None:
    """An override from an earlier run survives only if nothing it relied on has changed."""
    if not before or not before.get("override"):
        return None
    if before.get("turn") != row["turn"] or before.get("turn_hash") != row["turn_hash"]:
        return None
    override = before["override"]
    turn = turns.get(override.get("turn", ""))
    if turn is None or override.get("turn_hash") not in (None, turn_hash(turn.text)):
        return None
    return override


def _prepare(item: Item, proposal: dict | None, turns: dict[str, Turn] | None,
             before: dict | None) -> tuple[dict, str | None]:
    """The row as far as the transcript alone decides it, and the text a verifier must judge."""
    row = {"item": item.key, "status": "open", "turn": None, "turn_hash": None, "statement": "",
           "verdict": None, "override": None, "reason": ""}
    if proposal is None:
        row["reason"] = "not proposed"
        return row, None
    row["turn"], row["statement"] = proposal.get("turn"), str(proposal.get("statement", ""))
    if proposal.get("status") == "guessed":
        if item.may_be_guessed:
            row["status"], row["reason"] = "guessed", "listed as an assumption"
        else:
            row["reason"] = "this item may not be guessed"
        return row, None
    if turns is None:
        row["status"], row["reason"] = "attested", "no transcript: the agent's word only"
        return row, None
    turn = turns.get(row["turn"] or "")
    if turn is None:
        row["reason"] = "cited turn not found among the person's turns"
        return row, None
    row["turn_hash"] = turn_hash(turn.text)
    if before and before.get("turn") == row["turn"] and before.get("turn_hash") not in (None, row["turn_hash"]):
        row["reason"] = "cited turn changed since the last run"
        return row, None
    row["override"] = _carried_override(before, row, turns)
    return row, turn.text


def _verify(item: Item, text: str, verifiers: list[Verifier]) -> Verdict:
    return combine([apply_quote_rule(v.verify(item, text), text) for v in verifiers])


def _passes(rows: list[dict], items: tuple[Item, ...]) -> bool:
    allowed = {i.key: ({"settled", "guessed"} if i.may_be_guessed else {"settled"}) for i in items}
    return all(row["status"] in allowed[row["item"]] for row in rows)


def run_gate(proposals: list[dict], items: tuple[Item, ...], turns: dict[str, Turn] | None,
             verifiers: list[Verifier], previous: dict | None, harness: str | None = None) -> dict:
    by_item: dict[str, dict] = {}
    for proposal in proposals:
        by_item.setdefault(str(proposal.get("item")), proposal)
    before = _previous_rows(previous)
    prepared = [(i, *_prepare(i, by_item.get(i.key), turns, before.get(i.key))) for i in items]
    pending = [(i, row, text) for i, row, text in prepared if text is not None]
    # Every item at once: wall time is one verifier call, bounded by the adapters' own timeouts.
    with ThreadPoolExecutor(max_workers=max(1, len(pending))) as pool:
        verdicts = list(pool.map(lambda job: _verify(job[0], job[2], verifiers), pending))
    for (_, row, _), verdict in zip(pending, verdicts, strict=True):
        row["verdict"] = _verdict_dict(verdict)
        decided = row["override"]["answer"] if row["override"] else verdict.answer
        if decided == "yes":
            row["status"] = "settled"
        else:
            row["reason"] = verdict.reason or f"verifier answered {verdict.answer}"
    rows = [row for _, row, _ in prepared]
    attested = turns is None
    return {
        "harness": harness,
        "mode": "attested" if attested else "verified",
        "pass": False if attested else _passes(rows, items),
        "verifiers": [v.name for v in verifiers],
        "items": rows,
    }


def questions(readiness: dict, items: tuple[Item, ...]) -> list[dict]:
    order = {i.key: n for n, i in enumerate(items)}
    definitions = {i.key: i for i in items}
    open_rows = [r for r in readiness["items"] if r["status"] in ("open", "attested")]

    def certainty(row: dict) -> tuple[int, int]:
        answer = row["verdict"]["answer"] if row.get("verdict") else None
        return _RANK[answer], order[row["item"]]

    return [{"n": n, "item": r["item"], "question": definitions[r["item"]].definition,
             "recommendation": r.get("statement", ""), "why_open": r.get("reason", "")}
            for n, r in enumerate(sorted(open_rows, key=certainty), start=1)]


def _verification(verifiers: list[Verifier], attested: bool) -> str:
    names = {v.name for v in verifiers}
    if attested:
        return "none"
    if "session-model" in names:
        return "self-assessed"
    if "subagent" in names:
        return "agent-relayed"
    return "independent"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _session() -> tuple[str | None, Path | None, dict[str, Turn] | None]:
    found = find_transcript(os.environ, Path.home(), Path.cwd())
    if found is None:
        return None, None, None
    harness, path = found
    return harness, path, {t.id: t for t in load_user_turns(path, harness)}


def _fail(message: str, code: int = EXIT_OPEN) -> int:
    print(f"spec-ready: {message}", file=sys.stderr)
    return code


def _choose_verifiers(args) -> tuple[list[Verifier] | None, str]:
    independent = select_verifiers(os.environ)
    if args.answers:
        if not args.answers_from:
            return None, "--answers needs --answers-from subagent|session-model"
        usable = [v for v in independent if v.probe() is None]
        if usable:
            return None, ("an independent verifier is available (" + ", ".join(v.name for v in usable)
                          + "); an answers file is only accepted when none can run")
        return [AnswerFileVerifier(_load_json(Path(args.answers)), args.answers_from)], ""
    if not independent:
        return None, ("no verifier available; dispatch a subagent with `gate.py brief` and pass its answers "
                      "with --answers FILE --answers-from subagent")
    return independent, ""


def _check(args) -> int:
    try:
        items = load_items(Path(args.repo))
    except ItemsError as error:
        return _fail(str(error))
    verifiers, problem = _choose_verifiers(args)
    if verifiers is None:
        return _fail(problem)
    harness, path, turns = _session()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / READINESS
    previous = _load_json(target) if target.is_file() else None
    doc = run_gate(_load_json(Path(args.proposals)), items, turns, verifiers, previous, harness)
    doc["transcript"] = str(path) if path else None
    doc["verification"] = _verification(verifiers, turns is None)
    doc["environment"] = {"claude_cli": shutil.which("claude"), "path": os.environ.get("PATH", "")}
    _write(target, doc)
    print(json.dumps({"pass": doc["pass"], "mode": doc["mode"], "verification": doc["verification"],
                      "questions": questions(doc, items)}, indent=2))
    if turns is None:
        return EXIT_ATTESTED
    verdicts = [r["verdict"] for r in doc["items"] if r["verdict"]]
    if verdicts and all(v["error"] for v in verdicts):
        return _fail(f"verifier unavailable: {verdicts[0]['reason']}. Report this to the person; "
                     "if it cannot be fixed, use a subagent with --answers", EXIT_UNAVAILABLE)
    return EXIT_READY if doc["pass"] else EXIT_OPEN


def _brief(args) -> int:
    items = {i.key: i for i in load_items(Path(args.repo))}
    _, _, turns = _session()
    if args.item not in items or turns is None or args.turn not in turns:
        return _fail("unknown item, no transcript, or turn not among the person's turns")
    print(build_brief(items[args.item], turns[args.turn].text))
    return 0


def _list_turns(args) -> int:
    _, _, turns = _session()
    if turns is None:
        return _fail("no readable transcript", EXIT_ATTESTED)
    print(json.dumps([{"id": t.id, "text": t.text} for t in turns.values()], indent=2, ensure_ascii=False))
    return 0


def _override(args) -> int:
    target = Path(args.out) / READINESS
    doc = _load_json(target)
    if doc.get("mode") != "verified":
        return _fail("overrides need a verified run; this one is attested")
    _, path, turns = _session()
    if turns is None or str(path) != doc.get("transcript"):
        return _fail("cannot read the transcript this readiness.json was checked against")
    turn = turns.get(args.turn)
    quote = normalise(args.quote)
    if turn is None:
        return _fail(f"turn {args.turn} is not one of the person's turns")
    if not quote or quote not in normalise(turn.text):
        return _fail("the quote is not in that turn; quote the person's own words")
    row = next((r for r in doc["items"] if r["item"] == args.item), None)
    if row is None:
        return _fail(f"no item {args.item!r} in {target}")
    if row.get("turn") not in turns:
        row["turn"], row["turn_hash"] = args.turn, turn_hash(turn.text)
    row["override"] = {"answer": args.answer, "turn": args.turn, "quote": args.quote,
                       "turn_hash": turn_hash(turn.text)}
    row["status"] = "settled" if args.answer == "yes" else "open"
    doc["pass"] = _passes(doc["items"], load_items(Path(args.repo)))
    _write(target, doc)
    return 0


def _accept_attested(args) -> int:
    target = Path(args.out) / READINESS
    doc = _load_json(target)
    if doc.get("mode") != "attested":
        return _fail("this run is verified; nothing to accept")
    doc["attested_ack"] = args.reason
    _write(target, doc)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    commands = {}
    for name, handler in (("turns", _list_turns), ("check", _check), ("brief", _brief), ("override", _override),
                          ("accept-attested", _accept_attested)):
        commands[name] = handler
        sub.add_parser(name).add_argument("--repo", default=".")
    check = sub.choices["check"]
    check.add_argument("--proposals", required=True)
    check.add_argument("--out", required=True)
    check.add_argument("--answers")
    check.add_argument("--answers-from", choices=["subagent", "session-model"])
    brief = sub.choices["brief"]
    brief.add_argument("--item", required=True)
    brief.add_argument("--turn", required=True)
    override = sub.choices["override"]
    override.add_argument("--out", required=True)
    override.add_argument("--item", required=True)
    override.add_argument("--turn", required=True)
    override.add_argument("--quote", required=True)
    override.add_argument("--answer", choices=["yes", "no"], default="yes")
    accept = sub.choices["accept-attested"]
    accept.add_argument("--out", required=True)
    accept.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
