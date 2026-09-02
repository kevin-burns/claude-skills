#!/usr/bin/env python3
"""Locate the places a reader is most likely to fall off a draft.

This prints no score, no grade and no pass/fail, and that is the whole design.
A readability formula correlates with comprehension without saying WHERE the
problem is -- Redish (2000) puts it plainly: formulas "say nothing about the
causes of any problems people might have". Every line this script emits names a
line number instead, because a location can be acted on and a number cannot.

What it measures, and why each one is defensible:

  JUNCTIONS   Content-word overlap between adjacent paragraphs. This is the
              operationalisation Coh-Metrix uses for referential cohesion
              (Graesser, McNamara, Louwerse & Cai 2004, Behavior Research
              Methods 36(2), 193-202). Low overlap is where the argument jumps.
              Reported RANKED, never thresholded -- there is no published cut-off
              for one author's technical prose and inventing one would be the
              same error as a grade band.

  COLD OPENS  A paragraph beginning with a demonstrative or pronoun whose
              referent is therefore in the previous paragraph. Harmless on its
              own. The finding worth acting on is a cold open ON TOP OF a
              low-overlap junction: the reader is asked to carry a referent
              across a gap the text does not bridge.

  TERMS       First-use line and count for each technical term, and whether the
              sentence introducing it also glosses it. A term used before it is
              explained is a referential gap that no formula can see and that
              every reader feels.

  CONNECTIVES Which paragraphs open on a connective. Read alongside JUNCTIONS:
              a low-overlap junction that is also cold and unstitched is the
              real defect; a low-overlap junction opening on "But" is a
              deliberate turn.

WHAT IS DELIBERATELY ABSENT. No Flesch Reading Ease, Flesch-Kincaid, Gunning Fog
or SMOG. They were validated on schoolchildren and Navy trainees, they punish the
domain vocabulary an expert reader already knows, and Redish (2000) reports that
nobody knows whether they are valid for technical material read by adults at all.
See references/evidence.md. If you genuinely need one, use `textstat` -- do not
ask a model to compute one, because it will produce a plausible number it never
calculated.

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Function words carry grammar, not argument. Overlap on "the" says nothing about
# whether two paragraphs are about the same thing, so they are removed before
# comparing. Kept deliberately short: an aggressive stoplist starts deleting
# content ("state", "point", "case") and quietly changes what is being measured.
STOPWORDS = frozenset([
    "a", "an", "the", "and", "or", "but", "so", "nor", "for", "yet", "of", "in", "on", "at",
    "to", "from", "by", "with", "without", "into", "onto", "is", "are", "was", "were", "be",
    "been", "being", "am", "do", "does", "did", "done", "have", "has", "had", "having", "will",
    "would", "shall", "should", "can", "could", "may", "might", "must", "not", "no", "as", "if",
    "then", "than", "that", "this", "these", "those", "it", "its", "it's", "they", "them",
    "their", "there", "here", "what", "which", "who", "whom", "whose", "when", "where", "why",
    "how", "i", "me", "my", "we", "us", "our", "you", "your", "he", "him", "his", "she", "her",
    "one", "ones", "also", "just", "only", "even", "still", "about", "after", "again",
    "against", "all", "any", "because", "before", "both", "during", "each", "few", "further",
    "more", "most", "other", "own", "same", "some", "such", "too", "very", "over", "under",
    "between", "out", "up", "down", "off", "above",
])

# Words that open a paragraph by pointing BACKWARD. The referent is in the
# previous paragraph by construction, which is fine when the junction is tight
# and expensive when it is not.
BACKREFERENCE = frozenset([
    "this", "that", "these", "those", "it", "they", "them", "he", "she", "his", "her", "its",
    "their", "such",
])

# Paragraph-initial connectives. Their presence means the author stitched the
# junction on purpose; their absence at a low-overlap junction is the gap.
CONNECTIVES = frozenset([
    "but", "so", "and", "yet", "however", "therefore", "though", "although", "because", "since",
    "while", "whereas", "meanwhile", "instead", "still", "nevertheless", "nonetheless",
    "conversely", "otherwise", "thus", "hence", "consequently", "moreover", "furthermore",
    "additionally", "first", "second", "third", "finally",
])

# Markers that a sentence is explaining the term rather than merely using it.
GLOSS = re.compile(
    r"""(?:\bis\b|\bare\b|\bmeans\b|\bstands\s+for\b|\bis\s+the\b|\bis\s+a\b
        |\brefers\s+to\b|\bnamely\b|,\s*which\b|\s--\s|\s—\s|:\s)""",
    re.X,
)

FRONT_MATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
TABLE_ROW = re.compile(r"^\s*\|")
LIST_ITEM = re.compile(r"^\s{0,3}([-*+]\s|\d+[.)]\s)")
QUOTE = re.compile(r"^\s{0,3}>")
RULE = re.compile(r"^\s{0,3}(-{3,}|\*{3,}|_{3,})\s*$")

# A technical term: something in backticks, or a token carrying a shape that
# ordinary prose does not -- internal capital, dot, hyphen-with-digit, or an
# all-caps acronym of 2 or more letters.
BACKTICKED = re.compile(r"`([^`\n]{1,60})`")
SHAPED = re.compile(r"\b(?:[a-z]+[A-Z][A-Za-z]*|[A-Z]{2,}[a-z]*|[a-z]+[-.][a-z]{2,}(?:[-.][a-z]{2,})*)\b")

WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")


def stem(word: str) -> str:
    """Trim the handful of suffixes that would otherwise split one concept in two.

    'gate' and 'gates' and 'gating' should count as the same argument. This is
    deliberately crude: a real stemmer is a dependency, and the failure mode of
    over-stemming (two different words colliding) costs more here than the
    failure mode of under-stemming (one concept counted twice), because a
    collision inflates overlap and hides a gap.
    """
    w = word.lower().rstrip("'’")
    for suffix in ("ings", "ing", "edly", "ed", "es", "s", "ly"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[: -len(suffix)]
    return w


def content_words(text: str) -> set[str]:
    return {stem(w) for w in WORD.findall(text) if w.lower() not in STOPWORDS and len(w) > 2}


def strip_front_matter(raw: str) -> tuple[str, int]:
    """Return (body, line_offset) so every reported line maps to the ORIGINAL file.

    A report that names line 42 of a stripped buffer sends the reader to the
    wrong place, which is worse than not reporting at all.
    """
    m = FRONT_MATTER.match(raw)
    if not m:
        return raw, 0
    return raw[m.end():], raw[: m.end()].count("\n")


def paragraphs(raw: str) -> list[dict]:
    """Prose paragraphs only, each carrying the line it starts on.

    Headings, fenced code, tables, list blocks and horizontal rules are excluded:
    they are structure rather than argument, and including them makes a junction
    score meaningless -- a table between two paragraphs would read as a total
    cohesion break when the reader experiences no break at all.
    """
    body, offset = strip_front_matter(raw)
    out: list[dict] = []
    buf: list[str] = []
    start = 0
    in_fence = False

    def flush() -> None:
        if not buf:
            return
        text = " ".join(s.strip() for s in buf).strip()
        if text:
            out.append({"line": start + offset + 1, "text": text, "words": content_words(text)})
        buf.clear()

    for i, line in enumerate(body.split("\n")):
        if FENCE.match(line):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line.strip() or HEADING.match(line) or TABLE_ROW.match(line) \
                or LIST_ITEM.match(line) or RULE.match(line) or QUOTE.match(line):
            flush()
            continue
        if not buf:
            start = i
        buf.append(line)
    flush()
    return out


# Below this many content words a paragraph has nothing for the measure to work
# with, and an overlap of 0.00 says "too short", not "disconnected". Reporting
# those alongside real findings is how a metric earns false confidence, so they
# are separated out and counted rather than ranked.
MIN_WORDS = 10


def junctions(paras: list[dict], window: int = 2) -> list[dict]:
    """Overlap at each adjacent pair, plus overlap against a rolling window.

    Adjacent overlap alone is too brittle on short paragraphs: on a real 2,000-word
    post, 9 of 39 junctions scored exactly 0.00 and the ranking became a list of
    ties. A reader does not carry only the last paragraph, so each one is also
    compared against the previous `window` paragraphs pooled. A paragraph sharing
    nothing with its immediate predecessor but plenty with the section is a change
    of angle, not a gap; the pair of numbers tells those apart and one cannot.

    Dividing by the smaller side rather than the union stops a long paragraph next
    to a short one from reading as a break purely because of length.
    """
    out = []
    for i in range(1, len(paras)):
        a, b = paras[i - 1], paras[i]
        pooled: set[str] = set()
        for prev in paras[max(0, i - window):i]:
            pooled |= prev["words"]
        shared = a["words"] & b["words"]
        shared_win = pooled & b["words"]
        small = min(len(a["words"]), len(b["words"]))
        first = WORD.search(b["text"])
        first_word = first.group(0).lower() if first else ""
        out.append({
            "line": b["line"],
            "overlap": len(shared) / (small or 1),
            "overlap_window": len(shared_win) / (min(len(pooled), len(b["words"])) or 1),
            "shared": sorted(shared),
            "measurable": small >= MIN_WORDS,
            "cold_open": first_word in BACKREFERENCE,
            "connective": first_word in CONNECTIVES,
            "opens": b["text"][:70],
        })
    return out


def terms(raw: str, exempt: set[str]) -> list[dict]:
    """First-use line, count, and whether the introducing sentence glosses it."""
    body, offset = strip_front_matter(raw)
    lines = body.split("\n")
    found: dict[str, dict] = {}
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        candidates = [m.group(1) for m in BACKTICKED.finditer(line)]
        candidates += [m.group(0) for m in SHAPED.finditer(BACKTICKED.sub(" ", line))]
        for c in candidates:
            key = c.strip()
            if not key or key.lower() in exempt or len(key) < 2:
                continue
            rec = found.setdefault(key, {"term": key, "line": i + offset + 1, "count": 0,
                                         "glossed": bool(GLOSS.search(line))})
            rec["count"] += 1
    return sorted(found.values(), key=lambda r: r["line"])


def print_terms(ts: list[dict]) -> None:
    """Terms used twice or more whose introducing sentence does not explain them.

    Independent of the junction measure, so it survives a document too short to
    have junctions at all.
    """
    ungl = [t for t in ts if not t["glossed"] and t["count"] >= 2]
    if not ungl:
        return
    print(f"\nTERMS FIRST USED WITHOUT A GLOSS ({len(ungl)} of {len(ts)} terms)")
    print("  Used twice or more, and the sentence that introduces it does not explain it.")
    print("  Often correct for an expert audience — this names them, it does not judge.\n")
    for t in ungl[:20]:
        print(f"  line {t['line']:>4}  {t['term']:<28} used {t['count']}×")
    print()


def report(path: Path, exempt: set[str], as_json: bool, top: int) -> int:
    raw = path.read_text(encoding="utf-8")
    paras = paragraphs(raw)
    ts = terms(raw, exempt)

    # Junctions need two paragraphs; the term inventory does not. An earlier version
    # returned early here and threw the terms away with them, which meant a short
    # document got NOTHING TO CHECK even when it used four terms it never explained.
    # The junction measure is what is unavailable, and saying so precisely is the
    # difference between a limit and a silence.
    if len(paras) < 2:
        print(f"{path}: fewer than two prose paragraphs — no junctions to compare.", file=sys.stderr)
        print("NOTHING TO CHECK for cohesion. A junction report over one paragraph is not a")
        print("clean result, it is an empty one — read it yourself, or run the second reader.")
        print_terms(ts)
        return 0

    js = junctions(paras)
    measurable = [j for j in js if j["measurable"]]
    skipped = len(js) - len(measurable)
    # Rank on the window figure -- adjacent overlap alone ties too often to order.
    # Break remaining ties by preferring the junction with MORE text either side,
    # since a zero across two substantial paragraphs is a real jump and a zero
    # across two short ones is the measure running out of material.
    ranked = sorted(measurable,
                    key=lambda j: (j["overlap_window"], j["overlap"], -len(j["shared"])))[:top]

    if as_json:
        print(json.dumps({"file": str(path), "paragraphs": len(paras),
                          "junctions": js, "terms": ts}, indent=2))
        return 0

    print(f"COHESION REPORT — {path}")
    print(f"{len(paras)} prose paragraphs, {len(js)} junctions. "
          "No score is computed; see the note at the end.\n")

    print(f"WEAKEST JUNCTIONS (lowest overlap first, {len(ranked)} of {len(measurable)} measurable)")
    if skipped:
        print(f"  {skipped} junction(s) not ranked: a paragraph under {MIN_WORDS} content words")
        print("  gives the measure nothing to work with, and a 0.00 there means \"too short\",")
        print("  not \"disconnected\". Counted, not hidden.")
    print("  Where the argument jumps. Coh-Metrix measures referential cohesion this way")
    print("  (Graesser et al. 2004). There is no threshold — read the ones at the top.\n")
    for j in ranked:
        flags = []
        if j["cold_open"]:
            flags.append("COLD OPEN — starts on a back-reference")
        if j["connective"]:
            flags.append("stitched — opens on a connective")
        tag = ("  [" + "; ".join(flags) + "]") if flags else ""
        print(f"  line {j['line']:>4}  adjacent {j['overlap']:.2f}  window {j['overlap_window']:.2f}{tag}")
        print(f"             opens: {j['opens']}…")
        print(f"             shares: {', '.join(j['shared'][:8]) or '(nothing)'}")
    print()

    cut = sorted(x["overlap_window"] for x in measurable)[len(measurable) // 3] if measurable else 0
    worst = [j for j in measurable if j["cold_open"] and not j["connective"]
             and j["overlap_window"] <= cut]
    if worst:
        print("COLD OPEN OVER A WEAK JUNCTION — the combination worth fixing first")
        print("  The paragraph asks the reader to carry a referent across a gap the text")
        print("  does not bridge. Either name the thing, or stitch the junction.\n")
        for j in worst:
            print(f"  line {j['line']:>4}  window {j['overlap_window']:.2f}  {j['opens']}…")
        print()

    print_terms(ts)

    print("WHAT THIS DID NOT DO, on purpose.")
    print("  No Flesch, Flesch-Kincaid, Gunning Fog or SMOG, and no grade level. They were")
    print("  validated on schoolchildren and Navy trainees, they score domain vocabulary as")
    print("  difficulty, and Redish (2000) reports that whether they are valid for technical")
    print("  material read by adults is unknown. A location beats a number: everything above")
    print("  names a line. See references/evidence.md.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("file", type=Path)
    p.add_argument("--terms", type=Path,
                   help="newline-separated vocabulary the audience already knows; exempted "
                        "from the un-glossed list so known jargon stops crowding out real gaps")
    p.add_argument("--json", action="store_true", help="machine-readable, for a test or a gate")
    p.add_argument("--top", type=int, default=6, help="how many weakest junctions to print")
    a = p.parse_args()
    if not a.file.exists():
        print(f"no such file: {a.file}", file=sys.stderr)
        return 2
    exempt = set()
    if a.terms and a.terms.exists():
        # Comments are stripped rather than silently becoming exempt terms. A
        # vocabulary file people maintain by hand will grow comments, and a "#"
        # line quietly joining the exemption set is the kind of thing nobody
        # notices until a real term stops being reported.
        exempt = {line.split("#", 1)[0].strip().lower()
                  for line in a.terms.read_text().split("\n")}
        exempt.discard("")
    return report(a.file, exempt, a.json, a.top)


if __name__ == "__main__":
    raise SystemExit(main())
