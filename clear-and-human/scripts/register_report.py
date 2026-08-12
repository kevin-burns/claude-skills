#!/usr/bin/env python3
"""Report where a draft sits on two independent register axes: PERSON and STIFFNESS.

This exists so the model editing a draft can see the numbers rather than judge
"does this sound stiff" by eye. It is advisory only: it prints feature rates
and the citation behind each one, never a score, a grade, a pass/fail, or a
threshold to write toward. There is no "ok" field anywhere in its output.

The two-axis design (both from Biber, D. (1988), Variation Across Speech and
Writing, Cambridge University Press -- Dimension 1, "involved vs
informational production"):

  PERSON     -- first/second-person density. A stance the author CHOOSES per
                piece (a product write-up legitimately has no "I"). Reported
                as context and never flagged, and never inferred from the
                text -- pass --stance to label it, or it prints as "unset".

  STIFFNESS  -- contractions, analytic negation, demonstratives, word length,
                type/token ratio, nominalisation. None of these require first
                person: a draft can be entirely third-person and still be
                warm ("doesn't") or stiff ("does not"). This is the axis
                worth an editor's scrutiny.

Conflating the two is the design error this script exists to avoid: a stiff
impersonal draft and a correctly impersonal draft look identical on PERSON
alone.

Deliberately absent, per the evidence brief's rejected list: any AI-detector
score or "AI-likeness" percentage, burstiness (no academic grounding located;
GPTZero's own methodology page says they dropped it in autumn 2023),
readability indices (wrong validation domain -- Navy trainees and
schoolchildren's textbooks, not stylistic authenticity), the Heylighen &
Dewaele F-score (needs a POS tagger), perplexity, and any LLM call. This
script is stdlib-only and self-contained.
"""

# House convention -- sixteen scripts in this repo open this way. Keeps
# annotations lazy, so a signature never costs anything at import time.
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# Rates per 1000 words are noise below this many words -- one contraction in
# 40 words swings the rate by 25, which dwarfs any real signal. The prototype
# this script ports refused rather than printing a number that looked
# precise but wasn't, and that refusal is a feature worth keeping: a script
# that always prints something invites trusting the something.
MIN_WORDS = 200

# MATTR window: also doubles as the length floor above, so the "not enough
# words for one window" branch in ttr() below is unreachable by construction
# and exists only as a guard if the two constants are ever pulled apart.
TTR_WINDOW = 200

WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")

# Possessive 's and contracted 's share the same characters on the page, so a
# naive \w+'s pattern counts "the skill's job" as informality. This is the
# corrected pattern from the working prototype: unambiguous suffixes (n't,
# 're, 've, 'll, 'm) are matched openly; 's is matched only against the
# closed set of pronouns/adverbs where it cannot be a possessive. This bug
# is not cosmetic -- an earlier, naive version of this regex hid the
# project's headline finding (a post with a real contraction rate of zero
# was scoring nonzero from possessives alone) until it was caught.
# Citation: Biber (1988) Dim. 1, contraction loading .90 -- the single
# highest loading of any feature in the involved/warm direction.
CONTRACTION = re.compile(
    r"\b\w+['’](?:t|re|ve|ll|m)\b"
    r"|\b(?:it|that|there|here|what|who|he|she|let|which|everything|"
    r"nothing|something|one)['’]s\b"
    r"|\b(?:i|you|we|they|he|she|it|who|that)['’]d\b",
    re.I,
)

# Herbold, Hautli-Janisz, Heuer, Kikteva & Trautsch (2023), "AI, write an
# essay for me", Scientific Reports 13:18617: LLM essays carried
# significantly more nominalisation than human ones, measured by counting
# verb-to-noun suffixes rather than parsing -- reproducible in stdlib.
#
# Suffix matching is a proxy, and the stem length is the whole argument.
#
# The prototype used \w{4,}, which for a 4-letter suffix means an 8-character
# minimum word -- that silently drops "action", "nation", "station",
# "options", which are exactly the words this feature exists to catch.
# Relaxing it to \w+ overshoots the other way and starts matching ordinary
# words that merely end in those letters: stance, chance, France, dance,
# fence, city, moment, comment.
#
# Neither bound separates them, because "nation" (stem 2) and "stance"
# (stem 2) are indistinguishable by length. So: a 2-character stem floor,
# which alone excludes dance/fence/city, plus an explicit exclusion list for
# the frequent survivors. The list is not exhaustive and does not need to be
# -- this is a rate over a whole document, so a handful of misses shifts it
# by a fraction of a point. It exists to stop the common words that would
# otherwise fire several times per page.
#
# Calibration note: these rates are NOT comparable to figures produced by
# the earlier prototype, which used \w{4,}. Recalibrate before comparing
# against any number computed with that pattern.
NOMINALISATION = re.compile(r"\b\w{2,}(?:tion|sion|ment|ness|ity|ance|ence)s?\b", re.I)

# Words that clear the stem floor but are not verb-derived abstract nouns.
# Checked against the matcher, not assumed -- see the test of the same name.
NOT_NOMINALISATIONS = frozenset("""
stance stances chance chances france advance advances balance balances
finance finances instance instances romance romances entrance entrances
sentence sentences silence science sciences audience audiences
patience conscience nuisance moment moments comment comments
garment garments ornament fragment fragments monument monuments
pigment segment segments cement parliament tournament document documents
""".split())


def count_nominalisations(text: str) -> int:
    """Suffix matches, less the words that end in those letters by accident."""
    return sum(
        1 for m in NOMINALISATION.findall(text)
        if m.lower() not in NOT_NOMINALISATIONS
    )

# Biber (1988) Dim. 1 loadings, involved/warm (+) vs informational/stiff (-):
#   contractions .90 | 2nd person .86 | analytic negation .78
#   demonstratives .76 | 1st person .74 | word length -.58 | TTR -.54
FIRST_PERSON = re.compile(r"\b(?:i|me|my|mine|we|us|our|ours)\b", re.I)
SECOND_PERSON = re.compile(r"\b(?:you|your|yours|yourself)\b", re.I)
DEMONSTRATIVE = re.compile(r"\b(?:this|that|these|those)\b", re.I)
NEGATION = re.compile(r"\bnot\b|\w+n['’]t\b", re.I)


def strip_noise(text: str) -> str:
    """Remove what isn't the author's prose: code, tables, links, front matter.

    Without this, a post with a large YAML block or a shell transcript scores
    as though the author writes in it -- the whole document would look far
    stiffer or warmer than the prose actually is, purely from quoted code.
    """
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)      # front matter
    text = re.sub(r"```.*?```", " ", text, flags=re.S)            # fenced code
    text = re.sub(r"`[^`\n]+`", " ", text)                        # inline code
    text = re.sub(r"^\s*\|.*\|\s*$", " ", text, flags=re.M)       # table rows
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)             # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)          # links -> label
    # [ \t]{4,}, not \s{4,}: \s also matches \n, so a \s{4,} version can
    # span across several blank/whitespace-only lines (e.g. the blank lines
    # left behind by the table-row substitution just above) and then
    # swallow the *next real line of prose* into the same match, deleting
    # it outright. Confirmed by hand: "Prose before.\n| a | b |\n...\nProse
    # after." lost "Prose after." entirely under the \s{4,} version. Real
    # indented code (four leading spaces/tabs on one line) still matches.
    text = re.sub(r"^[ \t]{4,}\S.*$", " ", text, flags=re.M)      # indented code
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)            # heading marks
    text = re.sub(r"https?://\S+", " ", text)
    return text


def profile(text: str) -> dict:
    """Compute the eight-feature register profile for one document.

    Raises ValueError below MIN_WORDS instead of returning a number -- see
    the MIN_WORDS comment for why that refusal is deliberate, not a bug.
    """
    clean = strip_noise(text)
    words = [w.lower() for w in WORD.findall(clean)]
    n = len(words)
    if n < MIN_WORDS:
        raise ValueError(
            f"only {n} words after stripping code/tables/links/front matter -- "
            f"need at least {MIN_WORDS} for stable per-1000-word rates; "
            f"refusing to report rather than printing a noisy number"
        )

    feats = {
        "first_person": len(FIRST_PERSON.findall(clean)) / n * 1000,
        "second_person": len(SECOND_PERSON.findall(clean)) / n * 1000,
        "contraction": len(CONTRACTION.findall(clean)) / n * 1000,
        "negation": len(NEGATION.findall(clean)) / n * 1000,
        "demonstrative": len(DEMONSTRATIVE.findall(clean)) / n * 1000,
        "nominalisation": count_nominalisations(clean) / n * 1000,
        "word_length": sum(len(w) for w in words) / n,
    }

    # TTR is length-confounded (a longer document has more chances to repeat
    # a word, so raw TTR falls with length for reasons that have nothing to
    # do with style). MATTR averages the ratio over a sliding fixed-size
    # window instead of computing it once over the whole document, so a long
    # post doesn't score as "less varied" purely for being long.
    if n >= TTR_WINDOW:
        ratios = [
            len(set(words[i:i + TTR_WINDOW])) / TTR_WINDOW
            for i in range(0, n - TTR_WINDOW + 1, TTR_WINDOW // 2)
        ]
        feats["ttr"] = statistics.mean(ratios)
    else:
        # Unreachable while TTR_WINDOW == MIN_WORDS (see the constant's
        # comment); kept as a guard rather than deleted, so this function
        # stays correct if the two are ever set to different values.
        feats["ttr"] = len(set(words)) / n

    return {"n_words": n, "features": feats}


def collect_baseline(dir_path: Path) -> dict | None:
    """Aggregate a directory of the author's own writing into mean feature rates.

    Entirely optional context: most users pointing this at a single draft
    will have no comparable corpus handy, so the report must stand on its
    own without this. Per-document rates are averaged (matching how the
    evidence brief's own worked table compares documents) rather than
    pooling every file's words into one blob, so one very long file can't
    dominate the average.

    Returns None (with a stderr note, not a raised error) if the directory
    yields no usable document -- a missing/empty baseline degrades the
    report, it does not break it.
    """
    paths = sorted(
        p for p in dir_path.rglob("*")
        if p.is_file() and p.suffix.lower() in (".md", ".markdown", ".txt")
    )
    if not paths:
        print(f"baseline: no .md/.txt files found under {dir_path}", file=sys.stderr)
        return None

    per_doc = []
    skipped = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            skipped.append(f"{p.name} (unreadable: {exc})")
            continue
        try:
            per_doc.append(profile(text))
        except ValueError:
            skipped.append(f"{p.name} (too short)")

    if not per_doc:
        print(
            f"baseline: none of {len(paths)} file(s) under {dir_path} reached "
            f"{MIN_WORDS} words -- omitting the baseline column",
            file=sys.stderr,
        )
        return None

    if skipped:
        print(f"baseline: skipped {len(skipped)} file(s): {', '.join(skipped)}", file=sys.stderr)

    keys = per_doc[0]["features"].keys()
    mean_feats = {k: statistics.mean(d["features"][k] for d in per_doc) for k in keys}
    return {"n_docs": len(per_doc), "n_skipped": len(skipped), "features": mean_feats}


# Each row: (key, human label, unit, citation lines). Citations are printed
# next to every feature so a reader never has to take the number on faith.
PERSON_META = [
    ("first_person", "1st-person pronouns (I/me/my/we/us/our)", "rate", [
        "Biber (1988) Dim. 1: 1st-person pronoun loading .74 (involved pole).",
    ]),
    ("second_person", "2nd-person pronouns (you/your/yourself)", "rate", [
        "Biber (1988) Dim. 1: 2nd-person pronoun loading .86 (involved pole,",
        "second-highest loading of any single feature after contractions).",
    ]),
]

STIFFNESS_META = [
    ("contraction", "contractions (doesn't/it's/we're...)", "rate", [
        "Biber (1988) Dim. 1: contraction loading .90 -- the single highest",
        "loading of any feature, in either direction.",
        "Pavlick & Tetreault (2016, TACL 4, 61-74): annotators rewriting",
        "informal sentences as formal expanded contractions in 16% of coded",
        "edits -- a discrete formalising move, not a whole-register shift.",
    ]),
    ("negation", "analytic negation (not / n't)", "rate", [
        "Biber (1988) Dim. 1: analytic negation loading .78 (involved pole).",
    ]),
    ("demonstrative", "demonstratives (this/that/these/those)", "rate", [
        "Biber (1988) Dim. 1: demonstrative pronoun loading .76 (involved pole).",
    ]),
    ("nominalisation", "nominalisation (-tion/-sion/-ment/-ness/-ity/-ance/-ence)", "rate", [
        "Herbold, Hautli-Janisz, Heuer, Kikteva & Trautsch (2023), Scientific",
        "Reports 13:18617: ChatGPT essays carried significantly more",
        "nominalisation than human ones (Cohen's d -0.88 to -1.35, a large",
        "effect). Counted by suffix, not parsed -- reproducible in stdlib,",
        "per their own methodology. Their absolute means are on a DIFFERENT",
        "normalisation than the rate above, so only the direction transfers:",
        "higher means stiffer. There is no published rate to compare against.",
    ]),
    ("word_length", "mean word length", "chars", [
        "Biber (1988) Dim. 1: word length loading -.58 (informational/stiff pole).",
    ]),
    ("ttr", "type/token ratio (MATTR, window=200)", "ratio", [
        "Biber (1988) Dim. 1: TTR loading -.54 (informational/stiff pole).",
        "REGISTER INDICATOR ONLY -- do not read this as an AI-likeness signal.",
        "It is contested in that role: Herbold et al. (2023) found ChatGPT MORE",
        "lexically diverse than humans; Shaib et al. (arXiv:2403.00553) found",
        "LLM output LESS diverse on most of nine metrics. Both can be true",
        "because they measure different things -- TTR here describes register,",
        "not authorship or machine origin.",
    ]),
]


def _fmt_value(value: float, unit: str) -> str:
    if unit == "chars":
        return f"{value:.2f} chars"
    if unit == "ratio":
        return f"{value:.3f}"
    return f"{value:.1f} /1000w"


def _feature_block(meta, draft_feats: dict, baseline_feats: dict | None) -> list[str]:
    lines = []
    for key, label, unit, citation in meta:
        row = f"  {label:<58} draft {_fmt_value(draft_feats[key], unit):>12}"
        if baseline_feats is not None:
            row += f"   baseline {_fmt_value(baseline_feats[key], unit):>12}"
        lines.append(row)
        lines.extend(f"      {c}" for c in citation)
        lines.append("")
    return lines


def format_report(draft: dict, stance: str, baseline: dict | None, label: str) -> str:
    lines = [f"register report -- {label} ({draft['n_words']} words)", ""]

    lines.append("=" * 78)
    lines.append("AXIS 1 -- PERSON")
    lines.append("A stance the author chooses per piece. Context only, never a fault --")
    lines.append("and never inferred here from the numbers below: this line is whatever")
    lines.append("--stance said, or 'unset' if it wasn't passed.")
    lines.append(f"declared stance: {stance}")
    lines.append("=" * 78)
    lines.extend(_feature_block(PERSON_META, draft["features"], baseline["features"] if baseline else None))

    lines.append("=" * 78)
    lines.append("AXIS 2 -- STIFFNESS")
    lines.append("Independent of PERSON: none of these require first person. A draft can")
    lines.append("be entirely third-person and still be warm (\"doesn't\") or stiff (\"does")
    lines.append("not\"). This is the axis worth an editor's scrutiny -- this script only")
    lines.append("reports the numbers, it does not judge them.")
    lines.append("=" * 78)
    lines.extend(_feature_block(STIFFNESS_META, draft["features"], baseline["features"] if baseline else None))

    if baseline is not None:
        note = f"(baseline: {baseline['n_docs']} document(s)"
        if baseline["n_skipped"]:
            note += f", {baseline['n_skipped']} skipped as too short"
        note += ")"
        lines.append(note)
    else:
        lines.append("(no --baseline supplied -- report stands alone; that's normal)")

    return "\n".join(lines)


def to_json(draft: dict, stance: str, baseline: dict | None, label: str) -> dict:
    out = {
        "document": label,
        "n_words": draft["n_words"],
        "person": {
            "stance": stance,
            "note": "context only -- not inferred from text, never used to flag anything",
            "features": {k: draft["features"][k] for k, *_ in PERSON_META},
        },
        "stiffness": {
            "note": "independent of PERSON; the axis worth an editor's scrutiny",
            "features": {k: draft["features"][k] for k, *_ in STIFFNESS_META},
            "ttr_caveat": "type/token ratio is a register indicator only, never an AI-likeness signal",
        },
        "citations": {k: " ".join(c) for k, _, _, c in PERSON_META + STIFFNESS_META},
    }
    if baseline is not None:
        out["baseline"] = {
            "n_docs": baseline["n_docs"],
            "n_skipped": baseline["n_skipped"],
            "person_features": {k: baseline["features"][k] for k, *_ in PERSON_META},
            "stiffness_features": {k: baseline["features"][k] for k, *_ in STIFFNESS_META},
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    parser.add_argument("draft", nargs="?", help="path to the draft file; omit to read stdin")
    parser.add_argument(
        "--stance", choices=["personal", "impersonal", "unset"], default="unset",
        help="declared authorial stance, printed as PERSON-axis context only -- "
             "never inferred from the text and never used to flag anything",
    )
    parser.add_argument(
        "--baseline", type=Path, default=None,
        help="optional directory of the author's own writing; adds a comparison "
             "column. The report is complete without it.",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()

    if args.draft:
        draft_path = Path(args.draft)
        if not draft_path.is_file():
            parser.error(f"draft file not found: {draft_path}")
        text = draft_path.read_text(encoding="utf-8")
        label = draft_path.name
    else:
        text = sys.stdin.read()
        label = "<stdin>"

    try:
        draft = profile(text)
    except ValueError as exc:
        # A refusal, not a verdict on the writing -- there isn't enough text
        # to measure yet. Exit code 2 mirrors argparse's own usage-error code.
        print(f"REFUSING TO REPORT: {exc}", file=sys.stderr)
        return 2

    baseline = None
    if args.baseline is not None:
        if not args.baseline.is_dir():
            parser.error(f"--baseline is not a directory: {args.baseline}")
        baseline = collect_baseline(args.baseline)

    if args.json:
        print(json.dumps(to_json(draft, args.stance, baseline, label), indent=2))
    else:
        print(format_report(draft, args.stance, baseline, label))
    return 0


if __name__ == "__main__":
    sys.exit(main())
