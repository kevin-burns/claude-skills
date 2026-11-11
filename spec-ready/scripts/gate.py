#!/usr/bin/env python3
"""spec-ready gate: is the person's plan ready to be written up as a PRD and spec?

The agent proposes, per item, which of the person's turns states it. This script checks the turn
exists in the harness-written transcript, asks verifiers it chooses itself, applies the quote
rule, re-checks turn hashes from the previous run, and writes readiness.json.

    gate.py check --proposals P.json --out DIR [--transcript T --harness H]
                  [--answers A.json --answers-from subagent|session-model] [--repo .]
    gate.py turns [--transcript T --harness H]        list the person's turns with their ids
    gate.py brief --item KEY --turn ID [--transcript T --harness H]
    gate.py override --out DIR --item KEY --answer yes|no --reason TEXT

Exit codes for check: 0 ready, 1 items open (or a usage problem), 2 no readable transcript
(attested mode: continue only if the person explicitly agrees).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from items import Item, ItemsError, load_items
from transcripts import Turn, find_transcript, load_user_turns, turn_hash
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


def _verdict_dict(v: Verdict) -> dict:
    return {"answer": v.answer, "p": v.p, "span": v.span, "verifier": v.verifier, "reason": v.reason}


def _previous_rows(previous: dict | None) -> dict[str, dict]:
    return {row["item"]: row for row in (previous or {}).get("items", [])}


def _row(item: Item, proposal: dict | None, turns: dict[str, Turn] | None, verifiers: list[Verifier],
         before: dict | None) -> dict:
    row = {"item": item.key, "status": "open", "turn": None, "turn_hash": None, "statement": "",
           "verdict": None, "override": None, "reason": ""}
    if proposal is None:
        row["reason"] = "not proposed"
        return row
    row["turn"], row["statement"] = proposal.get("turn"), str(proposal.get("statement", ""))
    if proposal.get("status") == "guessed":
        if item.may_be_guessed:
            row["status"], row["reason"] = "guessed", "listed as an assumption"
        else:
            row["reason"] = "this item may not be guessed"
        return row
    if turns is None:
        text = row["statement"]  # attested: there is no transcript to check against
    else:
        turn = turns.get(row["turn"] or "")
        if turn is None:
            row["reason"] = "cited turn not found among the person's turns"
            return row
        text = turn.text
        row["turn_hash"] = turn_hash(text)
        if before and before.get("turn") == row["turn"] and before.get("turn_hash") not in (None, row["turn_hash"]):
            row["reason"] = "cited turn changed since the last run"
            return row
    verdict = combine([apply_quote_rule(v.verify(item, text), text) for v in verifiers])
    row["verdict"] = _verdict_dict(verdict)
    if before and before.get("override") and before.get("turn") == row["turn"]:
        row["override"] = before["override"]
    decided = row["override"]["answer"] if row["override"] else verdict.answer
    if decided == "yes":
        row["status"] = "settled"
    else:
        row["reason"] = verdict.reason or f"verifier answered {verdict.answer}"
    return row


def _passes(rows: list[dict], items: tuple[Item, ...]) -> bool:
    allowed = {i.key: ({"settled", "guessed"} if i.may_be_guessed else {"settled"}) for i in items}
    return all(row["status"] in allowed[row["item"]] for row in rows)


def run_gate(proposals: list[dict], items: tuple[Item, ...], turns: dict[str, Turn] | None,
             verifiers: list[Verifier], previous: dict | None, harness: str | None = None) -> dict:
    by_item: dict[str, dict] = {}
    for proposal in proposals:
        by_item.setdefault(str(proposal.get("item")), proposal)
    before = _previous_rows(previous)
    rows = [_row(i, by_item.get(i.key), turns, verifiers, before.get(i.key)) for i in items]
    return {
        "harness": harness,
        "mode": "attested" if turns is None else "verified",
        "pass": _passes(rows, items),
        "verifiers": [v.name for v in verifiers],
        "items": rows,
    }


def questions(readiness: dict, items: tuple[Item, ...]) -> list[dict]:
    order = {i.key: n for n, i in enumerate(items)}
    definitions = {i.key: i for i in items}
    open_rows = [r for r in readiness["items"]
                 if r["status"] == "open" or (r["status"] == "guessed" and not definitions[r["item"]].may_be_guessed)]

    def certainty(row: dict) -> tuple[int, int]:
        answer = row["verdict"]["answer"] if row.get("verdict") else None
        return _RANK[answer], order[row["item"]]

    return [{"n": n, "item": r["item"], "question": definitions[r["item"]].definition,
             "recommendation": r.get("statement", ""), "why_open": r.get("reason", "")}
            for n, r in enumerate(sorted(open_rows, key=certainty), start=1)]


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _turns(args) -> tuple[str | None, dict[str, Turn] | None]:
    if args.transcript:
        harness, path = args.harness, Path(args.transcript)
    else:
        found = find_transcript(os.environ, Path.home(), Path.cwd())
        if found is None:
            return None, None
        harness, path = found
    return harness, {t.id: t for t in load_user_turns(path, harness)}


def _check(args) -> int:
    try:
        items = load_items(Path(args.repo))
    except ItemsError as error:
        print(f"spec-ready: {error}", file=sys.stderr)
        return 1
    independent = select_verifiers(os.environ)
    if args.answers and independent:
        print("spec-ready: an independent verifier is available (" + ", ".join(v.name for v in independent)
              + "); an answers file is only accepted when none is", file=sys.stderr)
        return 1
    verifiers: list[Verifier] = independent or (
        [AnswerFileVerifier(_load_json(Path(args.answers)), args.answers_from)] if args.answers else [])
    if not verifiers:
        print("spec-ready: no verifier available; dispatch a subagent with `gate.py brief` and pass its "
              "answers with --answers --answers-from subagent", file=sys.stderr)
        return 1
    harness, turns = _turns(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / READINESS
    previous = _load_json(path) if path.is_file() else None
    doc = run_gate(_load_json(Path(args.proposals)), items, turns, verifiers, previous, harness)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": doc["pass"], "mode": doc["mode"], "verifiers": doc["verifiers"],
                      "questions": questions(doc, items)}, indent=2))
    if doc["mode"] == "attested":
        return 2
    return 0 if doc["pass"] else 1


def _brief(args) -> int:
    items = {i.key: i for i in load_items(Path(args.repo))}
    _, turns = _turns(args)
    if args.item not in items or turns is None or args.turn not in turns:
        print("spec-ready: unknown item, no transcript, or turn not among the person's turns", file=sys.stderr)
        return 1
    print(build_brief(items[args.item], turns[args.turn].text))
    return 0


def _list_turns(args) -> int:
    harness, turns = _turns(args)
    if turns is None:
        print("spec-ready: no readable transcript", file=sys.stderr)
        return 2
    print(json.dumps([{"id": t.id, "text": t.text} for t in turns.values()], indent=2, ensure_ascii=False))
    return 0


def _override(args) -> int:
    path = Path(args.out) / READINESS
    doc = _load_json(path)
    items = load_items(Path(args.repo))
    row = next((r for r in doc["items"] if r["item"] == args.item), None)
    if row is None:
        print(f"spec-ready: no item {args.item!r} in {path}", file=sys.stderr)
        return 1
    row["override"] = {"answer": args.answer, "reason": args.reason}
    row["status"] = "settled" if args.answer == "yes" and row.get("turn") else "open"
    doc["pass"] = _passes(doc["items"], items)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "brief", "turns"):
        p = sub.add_parser(name)
        p.add_argument("--repo", default=".")
        p.add_argument("--transcript")
        p.add_argument("--harness", choices=["claude-code", "codex"], default="claude-code")
    check = sub.choices["check"]
    check.add_argument("--proposals", required=True)
    check.add_argument("--out", required=True)
    check.add_argument("--answers")
    check.add_argument("--answers-from", choices=["subagent", "session-model"], default="subagent")
    brief = sub.choices["brief"]
    brief.add_argument("--item", required=True)
    brief.add_argument("--turn", required=True)
    override = sub.add_parser("override")
    override.add_argument("--repo", default=".")
    override.add_argument("--out", required=True)
    override.add_argument("--item", required=True)
    override.add_argument("--answer", choices=["yes", "no"], required=True)
    override.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    commands = {"check": _check, "brief": _brief, "turns": _list_turns, "override": _override}
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
