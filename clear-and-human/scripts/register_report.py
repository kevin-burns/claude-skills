#!/usr/bin/env python3
"""Report where a draft sits on two register axes: PERSON and STIFFNESS.

This exists so the model editing a draft can see the numbers rather than judge
"does this sound stiff" by eye. It is advisory only: it prints feature rates
and the citation behind each one, never a score, a grade, a pass/fail, or a
threshold to write toward. There is no "ok" field anywhere in its output.

  PERSON     -- first/second-person density. A stance the author CHOOSES per
                piece (a product write-up legitimately has no "I"). Reported
                as context and never flagged, and never inferred from the
                text -- pass --stance to label it, or it prints as "unset".

  STIFFNESS  -- contractions, analytic negation, demonstratives, word length,
                type/token ratio, nominalisation. This is the axis worth an
                editor's scrutiny.

WHY THEY ARE SPLIT, and what is NOT being claimed.

An earlier version of this file said the two axes are "independent". That was
a falsifiable empirical claim, and it should not have been made: establishing
it needs roughly 95-100 same-channel documents by one author (the 95% CI
half-width around rho=0 is +-0.36 at N=30, which does not even exclude the
correlation Biber's own loadings imply). It has been removed rather than
caveated. Nothing here depends on the two axes being uncorrelated.

Two things are claimed instead, and both are defensible without any statistics:

  1. Biber himself reads Dimension 1 as TWO parameters, not one. Biber (1988:
     107) names "the primary purpose of the writer/speaker: informational
     versus interactive, affective, and involved" AND "the production
     circumstances: those circumstances characterized by careful editing
     possibilities ... versus circumstances dictated by real-time constraints".
     Heylighen & Dewaele (1999) read the same page the same way, and object
     that Biber has "some difficulty fitting the empirically derived factor
     into a single theoretical construct". Since the features co-occur partly
     BECAUSE of production circumstances, holding those constant -- edited
     prose, one author, no real-time pressure -- weakens the reason to expect
     them to move together here.

  2. First-person density is a rhetorical choice, not a defect. Thonney (2013,
     Across the Disciplines, DOI 10.37514/ATD-J.2013.10.1.03) reports that
     experts use first person to "promote an impression of confidence and
     authority" and are roughly four times more likely than students to do so
     (citing Hyland 2002a/2002b), and that its prevalence varies by discipline,
     WITHIN disciplines, and WITHIN genres. That is what licenses "report
     PERSON, never flag it" -- an authorial choice, not a fault.

Known evidence on the other side, recorded rather than buried: Heylighen &
Dewaele (1999) factor-analysed a single held-constant situation and still
recovered an explicitness factor explaining over 50% of variance, with
pronouns loading strongly -- calling them "the only ones moving monotonically
with formality". Their measure treats pronouns as a CONSTITUENT of formality
rather than a separate axis. It is unrefereed, at word-class rather than
person level, and across speakers rather than within one author, but it is the
closest direct test that exists and it does not support the split.

The practical case for reporting them separately survives all of that: a draft
can be highly personal and still have zero contractions, so a single blended
score would pass it. That observation never needed the axes to be uncorrelated.

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
import hashlib
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
NOT_NOMINALISATIONS = frozenset([
    "stance", "stances", "chance", "chances", "france", "advance", "advances", "balance",
    "balances", "finance", "finances", "instance", "instances", "romance", "romances", "entrance",
    "entrances", "sentence", "sentences", "silence", "science", "sciences", "audience", "audiences",
    "patience", "conscience", "nuisance", "moment", "moments", "comment", "comments", "garment",
    "garments", "ornament", "fragment", "fragments", "monument", "monuments", "pigment", "segment",
    "segments", "cement", "parliament", "tournament", "document", "documents",
])


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
# Biber's .76 loading is on demonstrative PRONOUNS. A bare
# \b(this|that|these|those)\b does not measure that: it also counts the
# determiner ("that afternoon"), the complementiser ("I said that he left")
# and the relativiser ("the thing that matters"). Those belong to different
# Biber features entirely, so the old pattern printed a citation next to a
# number the citation did not describe.
#
# No POS tagger is available here, so this is deliberately CONSERVATIVE:
# it counts a demonstrative only in clause-initial subject position followed
# by a verb form -- "That is the point.", "This means X", "Those were the
# rules". Every match is near-certainly a pronoun; many real pronouns are
# missed (object position, "because of that", "I like these"). It undercounts
# rather than mislabels, which is the right direction for a feature whose
# whole purpose is to carry a citation honestly.
_DEMO_VERB = (r"(?:is|are|was|were|isn['’]t|aren['’]t|wasn['’]t|weren['’]t|has|have|had|"
              r"does|do|did|doesn['’]t|don['’]t|didn['’]t|will|would|can|could|should|"
              r"might|may|must|means|meant|gives|gave|makes|made|leaves|left|"
              r"seems|seemed|becomes|became|turns|turned|matters|mattered|"
              r"tends|tended|looks|looked|feels|felt|reads|read|works|worked)")
DEMONSTRATIVE = re.compile(
    r"(?:^|[.!?;:]\s+|\n\s*)(?:this|that|these|those)\s+" + _DEMO_VERB + r"\b",
    re.I | re.M,
)
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
    return re.sub(r"https?://\S+", " ", text)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_COORDINATOR = re.compile(r"\s+(?:and|or|nor)\s+", re.I)

# A segment opening with one of these is not a coordinand -- it is sequenced or subordinated,
# and that IS a change of shape. Added after the detector's first version failed a correct
# rewrite: "verifies the account and provisions the workspace, THEN notifies the team lead"
# was reported as a surviving three-item series, when turning a flat list into a 2+1 grouping
# is exactly what the rule asks for. A check that fails an ideal output is as useless as one
# that cannot fail.
_NOT_A_COORDINAND = re.compile(
    r"^(?:then|next|after|afterwards|before|once|while|so|because|which|who|whose|whom|"
    r"whereas|although|though|since|unless|until|if|when|meanwhile|finally|therefore|thus)\b",
    re.I,
)


def coordinated_series(text: str, minimum: int = 3) -> list[tuple[int, int]]:
    """Coordinated series of `minimum`+ items, as (1-based sentence number, item count).

    WHY THIS IS MEASURED RATHER THAN DESCRIBED. An eval expectation asking that a rewrite vary
    sentence structure rather than reproduce a flat parallel list failed three times running,
    each time on an output that described the change convincingly while leaving the coordination
    intact. The instruction it was measured against said "vary sentence rhythm", which the model
    read as LENGTH -- a defensible reading -- leaving SHAPE alone. Prose could not settle that
    argument, so this counts the thing being argued about: a series that survives shows up as
    the same number in the same sentence, and there is nothing left to narrate.

    NO FAILING EXAMPLE IS QUOTED HERE, DELIBERATELY. An earlier version of this docstring named
    one, and a graded run showed the model reading it and editing around the quoted STRINGS --
    avoiding those specific words while leaving the defect in place, then calling that a
    restructure. A named example in a file the model reads becomes a blocklist of tokens rather
    than an illustration of a principle. State the principle; let the count do the rest.

    A HEURISTIC, AND DELIBERATELY A CRUDE ONE. Segments are split on commas and on a
    coordinator, then counted. It cannot tell a list of noun phrases from a list of clauses and
    it does not try -- a parser would be a dependency, and this only has to make a survival
    visible, not classify English. It over-counts a sentence with unrelated commas and
    under-counts a series spanning a semicolon. Read the sentence it points at.

    IT PASSES NO JUDGEMENT. A rule of three is not a defect; `ai-patterns.md` flags it "forced
    everywhere", not present at all. Three genuinely parallel things belong in a list. What this
    reports is whether the shape changed, which is a fact, and not whether it should have.
    """
    out = []
    for i, sentence in enumerate(_SENTENCE_SPLIT.split(text.strip()), start=1):
        if "," not in sentence:
            continue
        parts = []
        for chunk in sentence.split(","):
            parts.extend(_COORDINATOR.split(chunk))
        items = [p for p in (x.strip(" ;:-—–") for x in parts) if p]
        # Drop segments that are sequenced or subordinated rather than coordinated. Only the
        # flat "X, Y, and Z" shape is what the rule is about; "X and Y, then Z" is the fix.
        items = [x for x in items if not _NOT_A_COORDINAND.match(x)]
        if len(items) >= minimum:
            out.append((i, len(items)))
    return out


def measured_digest(text: str) -> str:
    """A short SHA-256 of the exact bytes measured, printed with every report.

    WHY THIS EXISTS. On 2026-09-03 a pasted register_report block went stale: the check was
    run, the artefact was then edited, and the old numbers were presented as evidence for the
    new text. Contractions matched exactly while nominalisation was 25% out -- the signature
    of a check that predates an edit. Nothing in the output made that visible, so a stale
    paste and a live one were indistinguishable to a reader, and the skill's loudest rule
    ("a narrated check is worse than no check, because it reads as verification") had no
    mechanism behind it.

    A digest gives it one. Anyone holding the delivered text can hash it and see whether the
    report belongs to it. This does not stop staleness; it makes staleness VISIBLE, which is
    the only thing a report can honestly do about it.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


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
        "OVERLAPS WITH CONTRACTIONS BY DESIGN: \"doesn't\" counts once here and",
        "once there, because Biber treats them as separate features and a word",
        "can serve both. Two consequences worth knowing. First, this feature",
        "does NOT detect contraction expansion -- rewriting every \"doesn't\" as",
        "\"does not\" leaves this rate exactly unchanged; that move shows up in",
        "the contraction row, which is where to look for it. Second, the shared",
        "tokens mechanically couple the two rows, so do not correlate them",
        "against each other and read the result as a finding.",
        "Unverified: whether Biber's own definition of analytic negation",
        "includes n't or only not. Treat the .78 as indicative here.",
    ]),
    ("demonstrative", "demonstrative pronouns, clause-initial (that is/this means...)", "rate", [
        "Biber (1988) Dim. 1: demonstrative PRONOUN loading .76 (involved pole).",
        "Counted conservatively: only clause-initial demonstratives followed by",
        "a verb form, so the determiner (\"that afternoon\"), the complementiser",
        "(\"said that he left\") and the relativiser (\"the thing that matters\")",
        "are excluded -- those are different Biber features and counting them",
        "here would put this citation next to a number it does not describe.",
        "The cost is undercounting: object-position pronouns are missed. Rates",
        "are therefore NOT comparable to any figure from a bare",
        "this/that/these/those match, including this script before 2026-08-13.",
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


ALL_META = PERSON_META + STIFFNESS_META


def compute_drift(original: dict, rewrite: dict, baseline: dict | None) -> dict:
    """Per-feature movement from the pre-rewrite text to the rewrite.

    THE GAP THIS EXISTS TO CLOSE. `fidelity_check.py` catches a rewrite that invents a
    FACT. Until this, nothing caught a rewrite that invented a REGISTER -- and Layer 3 of
    the skill has a step, "restore contractions the draft expanded", that assumes there is
    something to restore. Measured on a real corpus by a confirmed non-native English
    writer: median contraction rate 2.9 per 1000 words, band 0.0-5.6, one published piece
    at exactly 0.0. Running that step on her moves her away from herself, and no part of
    the report said so.

    `direction` is only populated when a baseline exists, because "away" is meaningless
    without something to be away FROM. It is a comparison of two distances, not a
    threshold: the question is whether the rewrite sits further from the author's own rate
    than the original did.
    """
    out = {}
    for key, _label, _unit, _cit in ALL_META:
        o = original["features"][key]
        r = rewrite["features"][key]
        row = {"original": o, "rewrite": r, "delta": r - o}
        if baseline is not None:
            b = baseline["features"][key]
            was, now = abs(o - b), abs(r - b)
            if now > was:
                row["direction"] = "away"
            elif now < was:
                row["direction"] = "toward"
            else:
                row["direction"] = "unchanged"
        out[key] = row
    return out


def format_series_block(before: list, after: list) -> list[str]:
    """Which coordinated series survived the rewrite, which broke, which are new.

    'Survived' is the row that settles expectation 9.7's argument: a series in the same
    sentence position with the same item count is the same shape, whatever was done to the
    words inside it.
    """
    b = dict(before)
    a = dict(after)
    lines = [
        "COORDINATED SERIES -- shape, which is not rhythm",
        "A list whose words were swapped is the same list. This block reports",
        "whether the shape changed; it does not say whether it should have.",
        "EVERY ROW IS A POINTER, NOT A VERDICT. The detector splits on commas and",
        "coordinators and cannot parse English -- go and read the sentence it names.",
        "A rule of three is not a defect: ai-patterns.md flags it forced everywhere,",
        "not present at all.",
        "",
    ]
    if not b and not a:
        lines.append("  none in either document")
        lines.append("")
        return lines
    for idx in sorted(set(b) | set(a)):
        if idx in b and idx in a and b[idx] == a[idx]:
            lines.append(f"  sentence {idx}: {b[idx]}-item series  SURVIVED unchanged")
        elif idx in b and idx in a:
            lines.append(f"  sentence {idx}: {b[idx]}-item -> {a[idx]}-item  changed")
        elif idx in b:
            lines.append(f"  sentence {idx}: {b[idx]}-item series  BROKEN by the rewrite")
        else:
            lines.append(f"  sentence {idx}: {a[idx]}-item series  NEW in the rewrite")
    lines.append("")
    return lines


def format_drift(drift: dict, has_baseline: bool) -> list[str]:
    lines = [
        "=" * 78,
        "REGISTER DRIFT -- what the rewrite moved",
        "Movement is not a defect. A rewrite is supposed to change the text, and",
        "several of these features are exactly what it was asked to change. This",
        "section reports the size and direction of the movement so an editor can",
        "decide whether it was the movement they wanted. It sets no threshold and",
        "returns no verdict, in either direction.",
    ]
    if has_baseline:
        lines.append("With --baseline, each row also says whether the rewrite ended up")
        lines.append("closer to the author's own rate than the original was, or further")
        lines.append("from it. That is a comparison of two distances, not a limit.")
    else:
        lines.append("Without --baseline there is nothing to be 'away from', so no")
        lines.append("direction is shown -- only the movement itself.")
    lines.append("=" * 78)
    for key, label, unit, _cit in ALL_META:
        row = drift[key]
        d = row["delta"]
        delta = "--" if d == 0 else f"{'+' if d > 0 else ''}{_fmt_value(d, unit).strip()}"
        lines.append(f"  {label:<62}")
        line = (f"      {_fmt_value(row['original'], unit).strip():>12}"
                f"  ->{_fmt_value(row['rewrite'], unit).strip():>12}"
                f"   {delta:>12}")
        if "direction" in row:
            line += f"   {row['direction'].upper()}"
        lines.append(line)
    lines.append("")
    return lines


def format_report(draft: dict, stance: str, baseline: dict | None, label: str,
                  drift: dict | None = None, digest: str | None = None,
                  series: tuple | None = None) -> str:
    lines = [f"register report -- {label} ({draft['n_words']} words)"]
    if digest:
        lines.append(f"measured: {label} sha256:{digest}")
    lines.append("")

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
    lines.append("None of these require first person: a draft can be entirely")
    lines.append("third-person and still be warm (\"doesn't\") or stiff (\"does not\").")
    lines.append("This is the axis worth an editor's scrutiny. It is reported apart")
    lines.append("from PERSON because person is an authorial choice (Thonney 2013),")
    lines.append("not because the two are uncorrelated -- see the module docstring.")
    lines.append("This script reports the numbers; it does not judge them.")
    lines.append("=" * 78)
    lines.extend(_feature_block(STIFFNESS_META, draft["features"], baseline["features"] if baseline else None))

    if drift is not None:
        lines.extend(format_drift(drift, baseline is not None))
        if series is not None:
            lines.append("=" * 78)
            lines.extend(format_series_block(series[0], series[1]))

    if baseline is not None:
        note = f"(baseline: {baseline['n_docs']} document(s)"
        if baseline["n_skipped"]:
            note += f", {baseline['n_skipped']} skipped as too short"
        note += ")"
        lines.append(note)
    else:
        lines.append("(no --baseline supplied -- report stands alone; that's normal)")

    return "\n".join(lines)


def to_json(draft: dict, stance: str, baseline: dict | None, label: str,
            drift: dict | None = None, digest: str | None = None,
            series: tuple | None = None) -> dict:
    out = {
        "document": label,
        "measured_sha256": digest,
        "measured_note": "sha256 (first 16 hex) of the exact bytes measured. If the delivered "
                         "text does not hash to this, the report predates an edit and does not "
                         "describe what was delivered.",
        "n_words": draft["n_words"],
        "person": {
            "stance": stance,
            "note": "context only -- not inferred from text, never used to flag anything",
            "features": {k: draft["features"][k] for k, *_ in PERSON_META},
        },
        "stiffness": {
            "note": "reported separately from PERSON because person is an authorial "
                    "choice, not because the axes are uncorrelated -- no independence "
                    "is claimed",
            "features": {k: draft["features"][k] for k, *_ in STIFFNESS_META},
            "ttr_caveat": "type/token ratio is a register indicator only, never an AI-likeness signal",
        },
        "citations": {k: " ".join(c) for k, _, _, c in PERSON_META + STIFFNESS_META},
    }
    if series is not None:
        out["coordinated_series"] = {"original": series[0], "rewrite": series[1]}
    if drift is not None:
        out["drift"] = drift
        out["drift_note"] = (
            "movement from the pre-rewrite text to the rewrite, per feature. Movement is "
            "not a defect -- a rewrite is meant to change the text. No threshold is applied "
            "and no verdict is returned. 'direction' appears only with a baseline, and "
            "compares two distances rather than testing a limit."
        )
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
    parser.add_argument(
        "--against", type=Path, default=None,
        help="path to the PRE-REWRITE text. Adds a REGISTER DRIFT section reporting what "
             "the rewrite moved, per feature. fidelity_check.py catches an invented fact; "
             "this catches an invented register, which nothing else does.",
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

    original = None
    if args.against is not None:
        if not args.against.is_file():
            parser.error(f"--against file not found: {args.against}")
        try:
            original = profile(args.against.read_text(encoding="utf-8"))
        except ValueError as exc:
            # Same refusal as for the draft, and it names WHICH document is short --
            # otherwise the message is indistinguishable from the draft being short.
            print(f"REFUSING TO REPORT: the --against original is too short -- {exc}",
                  file=sys.stderr)
            return 2

    baseline = None
    if args.baseline is not None:
        if not args.baseline.is_dir():
            parser.error(f"--baseline is not a directory: {args.baseline}")
        baseline = collect_baseline(args.baseline)

    drift = compute_drift(original, draft, baseline) if original is not None else None
    digest = measured_digest(text)
    series = None
    if args.against is not None:
        series = (coordinated_series(args.against.read_text(encoding="utf-8")),
                  coordinated_series(text))

    if args.json:
        print(json.dumps(to_json(draft, args.stance, baseline, label, drift, digest, series), indent=2))
    else:
        print(format_report(draft, args.stance, baseline, label, drift, digest, series))
    return 0


if __name__ == "__main__":
    sys.exit(main())
