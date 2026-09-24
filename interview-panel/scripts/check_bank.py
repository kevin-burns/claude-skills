#!/usr/bin/env python3
"""Validate the question banks: every block complete, every cited source actually saying it.

WHY THIS EXISTS. A bank is the only part of this skill that asserts facts about the world:
each rubric says what a strong answer contains and names the page it came from. The first
version of this script checked that a source was PRESENT, and it passed a bank in which an
independent review later found 20 of 49 rubrics citing pages that did not support them -- one
cited 13 times for a method it never mentions, one a dead URL. Presence is not support.

So each sourced block now carries an `evidence:` quote, and `--verify` fetches the page and
checks the quote is on it. A rubric with no supporting page says `source: none (common
practice)` rather than borrowing a URL.

    python3 scripts/check_bank.py                      # every bank in references/banks/
    python3 scripts/check_bank.py path/to/bank.md      # one file (e.g. a private bank)
    python3 scripts/check_bank.py --summary
    python3 scripts/check_bank.py --verify             # fetch sources, check each quote

Seats are whatever references/personas/ defines; a bank seat with no persona fails, and so
does a persona with no bank. Exit 0 when valid, 1 otherwise. Stdlib only.
"""

import argparse
import collections
import html
import http.client
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BANKS = SKILL / "references" / "banks"
PERSONAS = SKILL / "references" / "personas"

REQUIRED = ("seat", "topic", "type", "question", "strong answer contains",
            "red flags", "follow-ups", "source", "source-type")
OPTIONAL = ("level", "why they ask", "answer path", "evidence")
FIELDS = REQUIRED + OPTIONAL
LIST_FIELDS = ("strong answer contains", "red flags", "follow-ups")
TYPES = {"behavioural", "situational", "scenario", "technical", "strategic"}
LEVELS = {"lead", "principal", "both"}
SOURCE_TYPES = {"asked", "answer", "company", "none"}
URL_SOURCE = re.compile(r"^(https?://\S+) \(retrieved \d{4}-\d{2}-\d{2}\)$")
NO_SOURCE = re.compile(r"^none\b")
HEAD_RE = re.compile(r"^### ([A-Z]{2}\d+)\b")


def seats_defined(personas=PERSONAS):
    return {p.stem for p in personas.glob("*.md")} if personas.is_dir() else set()


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
        if line.startswith("#"):          # another section ends the block
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


def problems(blocks, seats):
    out = []
    if not blocks:
        return ["no question blocks found"]
    for qid, b in blocks.items():
        if b.get("_dupe"):
            out.append(f"{qid}: duplicate id")
        for f in REQUIRED:
            if not b.get(f):
                out.append(f"{qid}: missing or empty '{f}'")
        if b.get("seat") and b["seat"] not in seats:
            out.append(f"{qid}: seat {b['seat']!r} has no persona file")
        if b.get("type") and b["type"] not in TYPES:
            out.append(f"{qid}: unknown type {b['type']!r}")
        if b.get("level") and b["level"] not in LEVELS:
            out.append(f"{qid}: unknown level {b['level']!r}")
        st = b.get("source-type")
        if st and st not in SOURCE_TYPES:
            out.append(f"{qid}: unknown source-type {st!r}")
        src = b.get("source", "")
        if src and NO_SOURCE.match(src):
            if st and st != "none":
                out.append(f"{qid}: source is none but source-type is {st!r}")
        elif src:
            if not URL_SOURCE.match(src):
                out.append(f"{qid}: source must be 'URL (retrieved YYYY-MM-DD)' or 'none (…)'")
            if st == "none":
                out.append(f"{qid}: a URL source cannot have source-type none")
            if not b.get("evidence"):
                out.append(f"{qid}: a URL source needs an evidence quote from that page")
    return out


def _norm(text):
    text = unicodedata.normalize("NFKC", html.unescape(text))
    text = text.translate(str.maketrans("‘’“”–—", "''\"\"--"))
    return " ".join(re.sub(r"[^\w\s']", " ", text.lower()).split())


def _https_get(url, redirects=5):
    """GET over HTTPS only. `HTTPSConnection`, not `urlopen`: it speaks no other scheme, so a
    `file://` or `http://` source in a bank cannot become a local read or a clear-text fetch
    (bandit B310), and a redirect to one is refused rather than followed."""
    for _ in range(redirects + 1):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            raise ValueError(f"source must be https: {url}")
        path = urllib.parse.urlunsplit(("", "", parts.path or "/", parts.query, ""))
        conn = http.client.HTTPSConnection(parts.hostname, parts.port, timeout=30)
        try:
            conn.request("GET", path, headers={"User-Agent": "interview-panel check_bank"})
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308) and resp.getheader("Location"):
                url = urllib.parse.urljoin(url, resp.getheader("Location"))
                continue
            if resp.status != 200:
                raise OSError(f"HTTP {resp.status}")
            return resp.read().decode("utf-8", errors="ignore")
        finally:
            conn.close()
    raise OSError("too many redirects")


def _page_text(url, cache):
    if url not in cache:
        try:
            raw = _https_get(url)
            raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
            # alt and title text is page content too: a diagram's caption can carry the claim.
            raw = re.sub(r"""<[^>]*?\b(?:alt|title)\s*=\s*["']([^"']*)["'][^>]*>""", r" \1 ", raw)
            cache[url] = _norm(re.sub(r"<[^>]+>", " ", raw))
        except (OSError, ValueError, http.client.HTTPException) as e:
            cache[url] = e
    return cache[url]


def verify(blocks, cache=None):
    """(unreachable, unsupported) lists. Unreachable is reported apart: it is not a verdict."""
    cache = {} if cache is None else cache
    unreachable, unsupported = [], []
    for qid, b in blocks.items():
        m = URL_SOURCE.match(b.get("source", ""))
        quote = (b.get("evidence") or "").strip().strip('"')
        if not m or not quote:
            continue
        page = _page_text(m.group(1), cache)
        if isinstance(page, Exception):
            unreachable.append(f"{qid}: {m.group(1)} ({type(page).__name__})")
        elif _norm(quote) not in page:
            unsupported.append(f"{qid}: quote not found on {m.group(1)}")
    return unreachable, unsupported


def summary(blocks):
    by = collections.Counter((b.get("seat"), b.get("type")) for b in blocks.values())
    st = collections.Counter(b.get("source-type") for b in blocks.values())
    lines = [f"{len(blocks)} questions; source-type {dict(st)}"]
    for seat in sorted({s for s, _ in by}):
        n = sum(v for (s, _), v in by.items() if s == seat)
        kinds = ", ".join(f"{t} {v}" for (s, t), v in sorted(by.items()) if s == seat)
        lines.append(f"  {seat}: {n} ({kinds})")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument("bank", nargs="?", help="one bank file; default: every file in references/banks/")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--verify", action="store_true", help="fetch each source and check its quote")
    args = ap.parse_args(argv)

    seats = seats_defined()
    files = [Path(args.bank)] if args.bank else sorted(BANKS.glob("*.md"))
    found, blocks = [], {}
    if not files:
        found.append(f"no bank files in {BANKS}")
    for f in files:
        these = parse(f.read_text())
        found += [f"{f.name}: {p}" for p in problems(these, seats)]
        found += [f"{f.name}: id {q} also in another bank" for q in these if q in blocks]
        blocks.update(these)
    if not args.bank:
        banked = {b.get("seat") for b in blocks.values()}
        found += [f"persona {s!r} has no questions in any bank" for s in sorted(seats - banked)]

    if args.summary:
        print("\n".join(summary(blocks)))
    if args.verify:
        unreachable, unsupported = verify(blocks)
        found += unsupported
        for u in unreachable:
            print(f"UNREACHABLE {u}")
    for p in found:
        print(f"FAIL {p}")
    if not found:
        print(f"OK {len(blocks)} questions across {len(files)} bank(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
