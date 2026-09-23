#!/usr/bin/env python3
"""Validate references/bank.md: every question block is complete and cites a source.

WHY THIS EXISTS. The bank is the only part of this skill that asserts facts about the world:
each rubric says what a strong answer contains and names the framework it came from. A block
with no source is a rubric written from recall, which is exactly what the bank was built to
avoid. This script is the one owner of the block format, so the format is written down once.

    python3 scripts/check_bank.py                # the bundled bank
    python3 scripts/check_bank.py path/to/bank.md
    python3 scripts/check_bank.py --summary      # counts per seat and topic

Exit 0 when every block is valid, 1 otherwise. Stdlib only.
"""

import argparse
import collections
import re
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / "references" / "bank.md"

FIELDS = ("seat", "topic", "level", "question", "strong answer contains",
          "red flags", "follow-ups", "source")
SEATS = {"head-of-cloud", "head-of-hr"}
LEVELS = {"lead", "principal", "both"}
TOPICS = {"strategy", "vision", "project-management", "leadership", "operating-model",
          "finops", "risk-security", "motivation", "conflict", "values"}
LIST_FIELDS = ("strong answer contains", "red flags", "follow-ups")
SOURCE_RE = re.compile(r"^https?://\S+ \(retrieved \d{4}-\d{2}-\d{2}\)$")
HEAD_RE = re.compile(r"^### (Q\d+)\b")


def parse(text):
    """{qid: {field: value-or-list}} in file order."""
    blocks, current, field = {}, None, None
    for line in text.splitlines():
        head = HEAD_RE.match(line)
        if head:
            qid = head.group(1)
            if qid in blocks:
                blocks[qid]["_dupe"] = True
            current = blocks.setdefault(qid, {})
            field = None
            continue
        if current is None:
            continue
        if line.startswith("#"):          # the source list or another section ends the block
            current, field = None, None
            continue
        top = re.match(r"^- ([a-z -]+):\s*(.*)$", line)
        if top and top.group(1) in FIELDS:
            field = top.group(1)
            current[field] = [] if field in LIST_FIELDS else top.group(2).strip()
            continue
        item = re.match(r"^\s+- (.+)$", line)
        if item and field in LIST_FIELDS:
            current[field].append(item.group(1).strip())
    return blocks


def problems(blocks):
    out = []
    if not blocks:
        return ["no question blocks found"]
    for qid, b in blocks.items():
        if b.get("_dupe"):
            out.append(f"{qid}: duplicate id")
        for f in FIELDS:
            if not b.get(f):
                out.append(f"{qid}: missing or empty '{f}'")
        if b.get("seat") and b["seat"] not in SEATS:
            out.append(f"{qid}: unknown seat {b['seat']!r}")
        if b.get("level") and b["level"] not in LEVELS:
            out.append(f"{qid}: unknown level {b['level']!r}")
        if b.get("topic") and b["topic"] not in TOPICS:
            out.append(f"{qid}: unknown topic {b['topic']!r}")
        if b.get("source") and not SOURCE_RE.match(b["source"]):
            out.append(f"{qid}: source must be 'URL (retrieved YYYY-MM-DD)', got {b['source']!r}")
    return out


def summary(blocks):
    seats = collections.Counter(b.get("seat") for b in blocks.values())
    topics = collections.Counter((b.get("seat"), b.get("topic")) for b in blocks.values())
    lines = [f"{len(blocks)} questions"]
    for seat, n in sorted(seats.items()):
        lines.append(f"  {seat}: {n}")
        for (s, t), m in sorted(topics.items()):
            if s == seat:
                lines.append(f"    {t}: {m}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument("bank", nargs="?", default=str(DEFAULT))
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args(argv)

    blocks = parse(Path(args.bank).read_text())
    found = problems(blocks)
    if args.summary:
        print("\n".join(summary(blocks)))
    for p in found:
        print(f"FAIL {p}")
    if not found:
        print(f"OK {len(blocks)} questions, every block complete and sourced")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
