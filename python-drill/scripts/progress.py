#!/usr/bin/env python3
"""Spaced-repetition progress for python-drill. Stdlib only.

Topics come from references/curriculum.md. State lives outside the skill, in
$PYTHON_DRILL_HOME (default ~/.local/share/python-drill/progress.json), so the skill
directory stays free of personal data.

Leitner boxes 1-5. A pass moves a topic up one box, a fail drops it to box 1, a partial
(passed with a hint) leaves it where it is. A topic is due when the days since it was last
seen reach the interval for its box. Never-seen topics are due.

    progress.py due [--n 4] [--track core,algo]   topics to drill now, weakest first
    progress.py record TOPIC pass|partial|fail [--note=TEXT]   (= form: a note may start with -)
    progress.py stats
    progress.py topics [--track pandas]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CURRICULUM = SKILL_DIR / "references" / "curriculum.md"
INTERVAL_DAYS = {1: 1, 2: 2, 3: 4, 4: 8, 5: 16}
TRACK_ORDER = ["core", "algo", "review", "pandas", "auto"]
LINE = re.compile(r"^- `([a-z0-9.-]+)` \[([a-z]+)\] (.+?) — (.+)$")


def state_path() -> Path:
    home = os.environ.get("PYTHON_DRILL_HOME") or str(Path.home() / ".local/share/python-drill")
    return Path(home) / "progress.json"


def load_topics(path: Path = CURRICULUM) -> dict[str, dict]:
    topics: dict[str, dict] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = LINE.match(raw)
        if m:
            tid, track, title, what = m.groups()
            if tid in topics:
                raise SystemExit(f"duplicate topic id in curriculum: {tid}")
            topics[tid] = {"track": track, "title": title, "what": what}
    if not topics:
        raise SystemExit(f"no topics parsed from {path}; check the line format")
    return topics


def load_state() -> dict:
    p = state_path()
    if not p.exists():
        return {"topics": {}, "log": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)
    if json.loads(p.read_text(encoding="utf-8")) != state:
        raise SystemExit(f"read-back mismatch writing {p}")


def today() -> dt.date:
    override = os.environ.get("PYTHON_DRILL_TODAY")
    return dt.date.fromisoformat(override) if override else dt.date.today()


def due_list(topics: dict, state: dict, tracks: list[str] | None) -> list[tuple]:
    rows = []
    order = {tid: i for i, tid in enumerate(topics)}
    for tid, t in topics.items():
        if tracks and t["track"] not in tracks:
            continue
        s = state["topics"].get(tid)
        if s is None:
            rows.append((0, 0, order[tid], tid, "new"))
            continue
        days = (today() - dt.date.fromisoformat(s["last"])).days
        overdue = days - INTERVAL_DAYS[s["box"]]
        if overdue >= 0:
            rows.append((s["box"], -overdue, order[tid], tid, f"box {s['box']}"))
    # Seen-and-weak first (low box), then new topics, so a failed topic comes back before
    # the curriculum moves on; ties go to the most overdue, then to curriculum order (core first).
    rows.sort(key=lambda r: (r[0] == 0, r[0], r[1], r[2], r[3]))
    return rows


def cmd_due(args, topics, state):
    tracks = args.track.split(",") if args.track else None
    if tracks:
        unknown = set(tracks) - set(TRACK_ORDER)
        if unknown:
            raise SystemExit(f"unknown track(s): {', '.join(sorted(unknown))}")
    rows = due_list(topics, state, tracks)[: args.n]
    if not rows:
        print("NOTHING DUE")
        return
    for _, _, _, tid, status in rows:
        t = topics[tid]
        print(f"{tid}\t{status}\t{t['title']} — {t['what']}")


def cmd_record(args, topics, state):
    if args.topic not in topics:
        raise SystemExit(f"unknown topic: {args.topic}")
    s = state["topics"].get(args.topic, {"box": 1, "passes": 0, "fails": 0})
    if args.result == "pass":
        s["box"] = min(5, s["box"] + 1) if "last" in s else 2
        s["passes"] += 1
    elif args.result == "fail":
        s["box"] = 1
        s["fails"] += 1
    s["last"] = today().isoformat()
    state["topics"][args.topic] = s
    state["log"].append({"date": s["last"], "topic": args.topic, "result": args.result, "note": args.note or ""})
    save_state(state)
    print(f"{args.topic}: {args.result} -> box {s['box']} (next due in {INTERVAL_DAYS[s['box']]}d)")


def cmd_stats(args, topics, state):
    seen = state["topics"]
    print(f"topics: {len(topics)}  seen: {len(seen)}  sessions logged: {len(state['log'])}")
    for track in TRACK_ORDER:
        ids = [t for t in topics if topics[t]["track"] == track]
        boxes = [seen[t]["box"] for t in ids if t in seen]
        print(
            f"  {track:7} {len(boxes)}/{len(ids)} seen, "
            f"weak (box 1): {sum(1 for b in boxes if b == 1)}, solid (box 4+): {sum(1 for b in boxes if b >= 4)}"
        )
    weak = sorted((t for t in seen if seen[t]["box"] == 1), key=lambda t: -seen[t]["fails"])
    if weak:
        print("weakest: " + ", ".join(weak[:8]))
    notes = [e for e in state["log"] if e["note"]][-5:]
    for e in notes:
        print(f"  {e['date']} {e['topic']} {e['result']}: {e['note']}")


def cmd_topics(args, topics, state):
    for tid, t in topics.items():
        if args.track and t["track"] != args.track:
            continue
        print(f"{tid}\t{t['track']}\t{t['title']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("due")
    d.add_argument("--n", type=int, default=4)
    d.add_argument("--track")
    r = sub.add_parser("record")
    r.add_argument("topic")
    r.add_argument("result", choices=["pass", "partial", "fail"])
    r.add_argument("--note")
    sub.add_parser("stats")
    t = sub.add_parser("topics")
    t.add_argument("--track")
    args = ap.parse_args(argv)
    topics = load_topics()
    state = load_state()
    {"due": cmd_due, "record": cmd_record, "stats": cmd_stats, "topics": cmd_topics}[args.cmd](args, topics, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
