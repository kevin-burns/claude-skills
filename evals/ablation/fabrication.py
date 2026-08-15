#!/usr/bin/env python3
"""Fabrication metric: did the rewrite invent specifics the input did not have?

Core rule 1 of clear-and-human is "never invent specifics to add texture".
Coverage Jaccard cannot see a breach of it -- an arm can flag exactly the right
tells and then fabricate freely in the rewrite. This counts three kinds of
invention, all mechanically:

  person   first-person forms in the rewrite when the input has none. That is
           an invented authorial stance, and it is the exact thing eval case 2
           forbids ("no first-person experiential claim absent from the input").
  number   digits or spelled-out numbers in the rewrite that are not in the
           input. Catches "three years" that a digits-only scan misses.
  proper   capitalised mid-sentence tokens absent from the input -- invented
           names, products, companies.

Every count is of things ADDED. Dropping a specific is a different fault.
"""

import json
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).parent
RUNS = HERE / "runs"
CASES = HERE / "cases"

FIRST_PERSON = re.compile(
    r"\b(i|i'm|i've|i'd|i'll|me|my|mine|myself|we|we're|we've|we'd|we'll|us|our|ours)\b",
    re.I,
)
# Unreliable in practice: "one" fires on "the right one" and "the one nobody markets".
# Every hit on this channel that was checked by hand turned out to be a false positive,
# so it is reported but never used as a headline. Kept because a real "three years"
# fabrication did appear in the runs and a digits-only scan would have missed it.
NUMBER_WORDS = [
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "twenty", "thirty", "forty", "fifty", "hundred", "thousand",
    "million", "billion", "dozen", "half", "double", "triple",
]
STOP_CAPS = {"I", "The", "A", "An", "It", "And", "But", "So", "This", "That", "There"}


def numbers(text: str) -> set[str]:
    found = {m.lower() for m in re.findall(r"\b\d[\d,.]*%?\b", text)}
    found |= {w for w in NUMBER_WORDS if re.search(rf"\b{w}\b", text, re.I)}
    return found


def propers(text: str) -> set[str]:
    # capitalised tokens that are not sentence-initial
    toks = re.findall(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]{2,})\b", text, re.M)
    return {t for t in toks if t not in STOP_CAPS}


PLACEHOLDER = re.compile(r"\[[^\]]*\]")


def score(source: str, rewrite: str) -> dict:
    if not rewrite.strip():
        return {}
    # Bracketed placeholders are the CORRECT response to a missing specific --
    # core rule 1 says leave one rather than invent. Scoring their contents as
    # invented numbers and proper nouns inverted the measurement: the first
    # version of this script scored "[concrete capability 1]" as a fabricated
    # number and "[Platform name]" as a fabricated proper noun.
    rewrite = PLACEHOLDER.sub(" ", rewrite)
    src_fp = len(FIRST_PERSON.findall(source))
    rw_fp = len(FIRST_PERSON.findall(rewrite))
    return {
        "person_added": rw_fp if src_fp == 0 else 0,
        "numbers_added": len(numbers(rewrite) - numbers(source)),
        "propers_added": len(propers(rewrite) - propers(source)),
        "words": len(rewrite.split()),
    }


def main() -> int:
    cases = sys.argv[1:] or ["1", "3", "8", "9"]
    print(f"{'case':<5} {'arm':<4} {'rep':<4} {'words':<6} {'person+':<8} {'nums+':<6} {'propers+':<9}")
    print("-" * 48)
    arms = sorted({p.stem.split("-")[1] for p in RUNS.glob("*-*-*.json")})
    totals: dict[str, list[int]] = {a: [] for a in arms}
    for case in cases:
        source = (CASES / f"{case}.txt").read_text()
        for arm in arms:
            for p in sorted(RUNS.glob(f"{case}-{arm}-*.json")):
                rep = p.stem.rsplit("-", 1)[1]
                if not p.stat().st_size:
                    continue
                env = json.loads(p.read_text())
                if env.get("is_error"):
                    continue
                try:
                    payload = json.loads(env["result"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
                s = score(source, payload.get("rewrite", ""))
                if not s:
                    continue
                flag = " <-- INVENTED STANCE" if s["person_added"] else ""
                print(
                    f"{case:<5} {arm:<4} {rep:<4} {s['words']:<6} {s['person_added']:<8} "
                    f"{s['numbers_added']:<6} {s['propers_added']:<9}{flag}"
                )
                totals[arm].append(s["person_added"])
    # Only the person channel is reported as a headline. The numbers and
    # proper-noun channels were checked by hand against the rewrites and every
    # hit was a false positive -- "the right one" matching a number word,
    # "five original claims" from a self-audit narration. Every person-channel
    # hit was checked the same way and every one was a genuine invention.
    print("\ninvented first-person stance (verified channel)")
    for arm, v in totals.items():
        if v:
            dirty = sum(1 for x in v if x)
            print(f"  arm {arm}: {dirty}/{len(v)} rewrites   mean {statistics.mean(v):.2f}   raw={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
