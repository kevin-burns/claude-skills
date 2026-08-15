#!/usr/bin/env python3
"""Deterministic fabrication/loss check: diff a rewrite against its original.

clear-and-human's two most emphatic rules are "never invent specifics to add
texture" and "preserve meaning, change delivery not substance" -- and until
now both were verified only by a model reading the prose and self-attesting.
This script checks the one thing a model's self-report can't be trusted to
catch reliably: whether a *concrete, checkable specific* -- a number, a name,
a quote, a URL, a code span -- was added, dropped, or altered between draft
and rewrite. A rewrite is free to change every sentence's rhythm; it is not
free to change what a reader would fact-check.

It tracks five span types: numbers (incl. percentages, currency, dates,
version strings), proper nouns, quoted spans, URLs, and code spans. For each
it reports what APPEARED (in the rewrite only), what VANISHED (in the
original only), and what CHANGED (present in both, but a different number of
times). A number that APPEARED is the single most important finding this
script can produce -- it is the one deterministic signature of a rewrite
inventing a statistic that was never in the source -- so it is surfaced in
its own banner ahead of the full report, not buried in a list.

It also diffs a sixth thing that is not a span at all: a closed list of
CLAIM WORDS -- the words that rank, scope, compare or require. Those cover
the failure the span types cannot see, where a style rule removes meaning
while appearing to remove only shape. Deleting "single most" from "the
single most important build" looks like boldface cleanup and takes a ranking
with it; deleting "simultaneously" from "it is simultaneously A, B and C"
looks like rule-of-three tightening and takes a claim of joint truth with
it. Neither deletion touches a number, a quote, a URL or a code span, so
before this section both passed clean.

This is advisory, not a gate: it prints findings and stops. It does not
compute or print a verdict, a grade, a pass/fail, or a score of any kind,
and there is nothing here to optimise against -- see clear-and-human's
evidence brief for why an AI-detector-style score was explicitly rejected
for this skill. Needs no baseline corpus and no configuration, so it works
for any user on the very first run.
"""

import argparse
import json
import re
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# Code and URL spans -- extracted and masked out FIRST so that digits inside
# a URL path (".../v2/report") or a code identifier aren't mistaken for a
# fact the prose is asserting. Quotes are extracted from the *unmasked* text
# below, since a quoted number or name is still exactly the kind of specific
# this script exists to protect.
# ---------------------------------------------------------------------------
FENCED_CODE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
URL_RE = re.compile(r"\bhttps?://[^\s<>\)\]\"']+|\bwww\.[^\s<>\)\]\"']+", re.I)


def _mask(text: str, pattern: re.Pattern) -> tuple[str, list[str]]:
    """Pull out every match of `pattern`, replacing each with same-length
    blanks so surrounding sentence structure (and later offsets) survive."""
    found = [m.group(0) for m in pattern.finditer(text)]
    masked = pattern.sub(lambda m: " " * len(m.group(0)), text)
    return masked, found


def extract_tracked_spans(text: str) -> dict:
    """Peel code and URL spans off the text, in that order, and return what's
    left ("clean") for the number/proper-noun scanners below."""
    working, fenced = _mask(text, FENCED_CODE_RE)
    working, inline = _mask(working, INLINE_CODE_RE)
    working, urls = _mask(working, URL_RE)
    return {"clean": working, "code": fenced + inline, "urls": urls}


def normalize_url(raw: str) -> str:
    """Drop trailing sentence punctuation the URL regex over-grabbed
    ("...the docs at https://x.io/a." should not carry the sentence's own
    full stop). A trailing slash is left alone -- that can be a real part
    of the path, not punctuation."""
    return raw.rstrip(".,;:!?")


def normalize_code(raw: str) -> str:
    """Strip the backtick fence itself; keep the interior byte-for-byte,
    since code is exactly the one span type where whitespace and case ARE
    the content and must never be normalised away."""
    if raw.startswith("```"):
        inner = raw[3:-3]
        # A fenced block's first line is often just a language tag
        # ("```python\n"), not part of the code -- drop that one line only.
        inner = re.sub(r"^[ \t]*\w*\n", "", inner, count=1)
    else:
        inner = raw.strip("`")
    return inner.strip()


# ---------------------------------------------------------------------------
# Numbers: percentages, currency, dates, version strings, plain numbers.
# Written as one alternation so more specific patterns are tried, at a given
# starting position, before the catch-all plain-number pattern -- Python's
# re module takes the first alternative that matches at each position, not
# the longest, so order here is load-bearing: version/date/currency/percent
# all have to sit ABOVE plain or they'd never get a chance to match.
# ---------------------------------------------------------------------------
_MONTHS = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)
_DATE_TEXT = (
    r"\b(?:" + _MONTHS + r")\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b"
    r"|\b\d{1,2}\s+(?:" + _MONTHS + r")\.?,?\s+\d{4}\b"
)

NUMBER_RE = re.compile(
    r"(?P<currency>[$€£¥]\s?\d[\d,]*(?:\.\d+)?)"
    r"|(?P<percent>\d[\d,]*(?:\.\d+)?\s?%)"
    r"|(?P<date_iso>\b\d{4}-\d{2}-\d{2}\b)"
    r"|(?P<date_slash>\b\d{1,2}/\d{1,2}/\d{2,4}\b)"
    r"|(?P<date_text>" + _DATE_TEXT + r")"
    r"|(?P<version>\bv\d+(?:\.\d+){1,3}\b|\b\d+\.\d+\.\d+(?:\.\d+)?\b)"
    r"|(?P<plain>\b\d[\d,]*(?:\.\d+)?\b)",
    re.IGNORECASE,
)


def normalize_number(raw: str, category: str) -> str:
    """Collapse the trivial spelling variants the brief calls out -- "20 %"
    vs "20%", a thousands-separator comma -- without touching the digits
    that make two numbers actually different, and without mangling a text
    date: stripping ALL whitespace from "Aug 12, 2026" would produce the
    unreadable, un-matchable "Aug122026", so date_text keeps its spacing
    (collapsed to single spaces) and only the numeric categories have
    whitespace removed outright.

    Known gap: this assumes US-style comma-thousands / dot-decimal. A
    European "1.234,56" is not recognised as the same number as "1234.56"
    and would show up as a spurious appeared/vanished pair -- no
    stdlib-only way to disambiguate the two conventions from a two-file
    diff alone.
    """
    if category == "date_text":
        return re.sub(r"\s+", " ", raw.strip())
    if category in ("currency", "percent", "plain"):
        return re.sub(r"\s+", "", raw.replace(",", ""))
    return raw  # date_iso / date_slash / version: no interior whitespace to fix


def extract_numbers(text: str) -> list[str]:
    return [normalize_number(m.group(0), m.lastgroup) for m in NUMBER_RE.finditer(text)]


# ---------------------------------------------------------------------------
# Proper nouns: a capitalised-token heuristic, because there is no POS
# tagger in the standard library and the brief forbids adding one.
# ---------------------------------------------------------------------------
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")

# The closed class of English words that get capitalised purely because
# they happen to open a sentence -- articles, pronouns, demonstratives,
# wh-words, conjunctions/subordinators, and the common sentence-adverbs and
# section-label words ("Note:", "Example:") technical prose leans on. This
# is the same kind of finite, built-in word list as LIMITS above or
# FUNCTION_WORDS in the earlier prototype -- not user configuration, just
# a fixed vocabulary the script ships with. Anything NOT in this set that
# shows up capitalised is presumed a real proper noun even if every one of
# its occurrences happens to open a sentence (see extract_proper_nouns).
PROPER_NOUN_STOPWORDS = {
    "a", "an", "the", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "one",
    "there", "here", "what", "who", "which", "where", "when", "why", "how",
    "and", "but", "or", "nor", "so", "yet",
    "if", "unless", "since", "after", "before", "until", "as", "while",
    "because", "although", "though",
    "also", "however", "meanwhile", "sometimes", "additionally", "finally",
    "then", "now", "still", "overall", "instead", "otherwise", "indeed",
    "perhaps", "maybe", "certainly", "clearly", "similarly", "actually",
    "furthermore", "moreover", "nevertheless", "nonetheless", "regardless",
    "consequently", "therefore", "thus", "hence",
    "note", "example", "tip", "warning", "caution",
}


def _sentences(text: str) -> list[str]:
    """Rough sentence split for the capitalisation check below.

    Deliberately crude: a real sentence segmenter needs the abbreviation
    list ("Dr.", "e.g.", "U.S.") a proper NLP pipeline carries, and this
    skill has none. Splitting on newlines first (so a heading or list item
    is never merged into its neighbour) and then on ./!/? followed by a
    capital or digit is good enough for a heuristic that only needs to know
    "is this word at the start of its unit or not".
    """
    units: list[str] = []
    for line in text.splitlines():
        units.extend(
            re.split(r"(?<=[.!?])[\"'’”)\]]*\s+(?=[A-Z0-9])", line)
        )
    return [u for u in units if u.strip()]


def _looks_like_heading(sentence: str) -> bool:
    """True for a Title Case or ALL-CAPS line ("Quarterly Report Summary"),
    where every word being capitalised is a formatting choice, not evidence
    about any individual word. A normal sentence almost always has at least
    one lowercase function word (an, the, of, met, ...), so this rarely
    fires on real prose -- but it is a heuristic, not a guarantee; a short,
    all-proper-noun sentence ("Kevin Met Jane") would be skipped too."""
    words = WORD_RE.findall(sentence)
    return len(words) >= 3 and all(w[0].isupper() for w in words)


def extract_proper_nouns(text: str) -> list[str]:
    """Capitalised tokens that are evidence of a proper noun, not just of
    sitting at the front of a sentence.

    The rule: a capitalised word is a candidate UNLESS it is one of the
    closed-class PROPER_NOUN_STOPWORDS -- in which case it only counts if
    at least one of its occurrences sits somewhere OTHER than the start of
    a sentence (the one position in English where capitalising "the" or
    "this" carries no information at all). This is deliberately asymmetric:
    an ordinary name like "Kevin" is kept even if every single occurrence
    opens its own sentence ("Kevin wrote... Kevin also..." is common and
    should not be suppressed just because Kevin is always the subject),
    while a closed-class word like "The" only survives the filter if it
    shows up capitalised somewhere unusual (inside a quoted title, say).

    Stated misses, on purpose rather than silently:
    - The stopword list is finite. A capitalised word that isn't in it but
      also isn't a real proper noun (an uncommon sentence-adverb this list
      doesn't happen to carry) will still be reported. That is the
      trade-off for not missing genuine repeated names -- see above.
    - ALL-CAPS headings and Title Case lines are the other classic false
      trigger (every word looks "capitalised"); `_looks_like_heading`
      filters the obvious case -- a short line where every single word
      starts uppercase -- but a heading that mixes case, or a heading that
      is itself a run of real proper nouns, will not be caught.
    """
    mid_sentence_hits: set[str] = set()
    all_hits: list[tuple[str, bool]] = []
    for sentence in _sentences(text):
        if _looks_like_heading(sentence):
            continue
        words = WORD_RE.findall(sentence)
        for i, word in enumerate(words):
            if not word[0].isupper():
                continue
            is_initial = i == 0
            all_hits.append((word, is_initial))
            if not is_initial:
                mid_sentence_hits.add(word)
    return [
        w for w, is_initial in all_hits
        if w.lower() not in PROPER_NOUN_STOPWORDS or w in mid_sentence_hits
    ]


# ---------------------------------------------------------------------------
# Quoted spans -- straight and curly, double and single.
# ---------------------------------------------------------------------------
QUOTE_RE = re.compile(
    r'"([^"\n]+)"'
    r"|“([^”\n]+)”"
    r"|'([^'\n]*\s[^'\n]*)'"
    r"|‘([^’\n]*\s[^’\n]*)’"
)

_CURLY_TO_STRAIGHT = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
})


def normalize_quote(inner: str) -> str:
    """Curly vs straight quote MARKS are already stripped by the regex
    (only the inner text is captured); this normalises curly apostrophes
    that can appear INSIDE the quoted text itself, plus incidental
    whitespace -- not the words, which is the whole point of tracking a
    quote at all."""
    return re.sub(r"\s+", " ", inner.translate(_CURLY_TO_STRAIGHT).strip())


def extract_quotes(text: str) -> list[str]:
    """Quoted spans. Single quotes require an internal space, i.e. at
    least two words: a naive '...' pattern pairs across contractions and
    possessives ("she said 'don't stop'" reads the apostrophe in "don't"
    as the closing mark, capturing the fragment "don"), the same trap the
    contraction regex in the earlier prototype had to work around. The
    whitespace requirement rejects that fragment outright, because a
    contraction/possessive apostrophe is never followed by a space before
    the "closing" mark -- at the cost of also missing any genuine
    single-word single-quoted term ('yes', 'no'). Double quotes need no
    such trade-off and are the reliable signal; single-quote detection is
    deliberately best-effort.
    """
    out = []
    for m in QUOTE_RE.finditer(text):
        inner = next(g for g in m.groups() if g is not None)
        out.append(normalize_quote(inner))
    return out


# ---------------------------------------------------------------------------
# Claim words: the closed class of words that assert something beyond the
# proposition they sit in -- a rank, a scope, a comparison, a requirement.
# Unlike everything above, these are not "specifics a reader would
# fact-check"; they are the load-bearing function words a style edit can
# delete without appearing to have changed a claim at all.
#
# The four groups, and where each list comes from:
#
#   ranking      superlatives and ordinals. Removing one stops the sentence
#                placing its subject in an order.
#   scope        universal quantifiers and emphatic negation. Removing one
#                narrows or widens what the claim covers.
#   relation     comparatives, the comparison marker "than", and the adverbs
#                that assert things hold jointly rather than in sequence.
#   requirement  the RFC 2119 key words (Bradner, S., "Key words for use in
#                RFCs to Indicate Requirement Levels", BCP 14, RFC 2119,
#                March 1997), which is the one group here taken from a
#                normative source rather than assembled by judgement.
#                Borrowed as a WORD LIST only, not with its semantics: RFC
#                8174 (Leiba, B., "Ambiguity of Uppercase vs Lowercase in
#                RFC 2119 Key Words", RFC 8174, May 2017) restricts the
#                defined meanings to the uppercase forms, and this script
#                matches case-insensitively across ordinary prose. Downgrade
#                a doc's "must" to "should" and the diff shows one word
#                vanishing and another appearing, which is the point.
#
# Two deliberate omissions, both because clear-and-human's own rules delete
# them by design and a check that fires on every correct run is a check
# nobody reads:
#
#   "not" and "no" -- Strunk's "put statements in positive form" is Layer 1
#   of this skill (references/elements-of-style.md). A rewrite that turns
#   "not unlike" into "like" is obeying the skill, and would be reported as
#   losing negation on almost every document. The emphatic negations that a
#   style edit has no business touching -- never, none, neither, nor,
#   cannot -- are kept.
#
#   Intensifiers -- very, really, quite, extremely, truly. These are the
#   textbook "omit needless words" cut and they assert nothing on their own:
#   "very large" and "large" make the same claim with different force. They
#   are absent from every group below, on purpose.
# ---------------------------------------------------------------------------
CLAIM_WORD_GROUPS: dict[str, frozenset[str]] = {
    "ranking": frozenset({
        "best", "worst", "most", "least", "greatest", "largest", "smallest",
        "highest", "lowest", "first", "last", "foremost", "single", "sole",
        "only", "primary", "principal", "chief", "main",
    }),
    "scope": frozenset({
        "all", "every", "each", "any", "both", "none", "never", "always",
        "neither", "nor", "entirely", "wholly", "completely", "fully",
        "exclusively", "solely", "universally", "invariably",
    }),
    "relation": frozenset({
        "than", "more", "less", "fewer", "better", "worse", "greater",
        "higher", "lower", "faster", "slower", "simultaneously",
        "concurrently", "respectively",
    }),
    "requirement": frozenset({
        "must", "shall", "should", "may", "cannot", "required",
        "recommended", "optional",
    }),
}

CLAIM_WORD_OF_GROUP: dict[str, str] = {
    word: group for group, words in CLAIM_WORD_GROUPS.items() for word in words
}

# (?<![\w-]) / (?![\w-]) rather than \b so that a hyphenated compound is left
# alone: "first-class" is not the ordinal "first", "all-in-one" is not the
# quantifier "all", and "single-file" is not the ranking "single".
CLAIM_WORD_RE = re.compile(
    r"(?<![\w-])(?:" + "|".join(sorted(CLAIM_WORD_OF_GROUP, key=len, reverse=True))
    + r")(?![\w-])",
    re.IGNORECASE,
)


def extract_claim_words(text: str) -> list[str]:
    """Every claim-word occurrence, lowercased. Multiset, not a set: losing
    three of five "only"s matters and a set would hide it.

    Stated misses, since a closed list cannot help having them:
    - Inflected superlatives outside the list ("fastest", "cleanest") are not
      matched. A `-est` suffix rule would drag in interest, honest, request,
      modest and two dozen others, and the style rules that cause this bug
      target adverbs and determiners rather than inflected adjectives.
    - Multi-word forms ("must not", "at once", "in every case") are matched
      only through whichever single word they contain.
    - Sense is not disambiguated. "a single file" is a count, not a ranking;
      "may" can be permission or possibility. This reports the word and lets
      a reader judge, which is the same bargain the proper-noun heuristic
      makes.
    """
    return [m.group(0).lower() for m in CLAIM_WORD_RE.finditer(text)]


# ---------------------------------------------------------------------------
# The diff itself: a multiset (Counter) comparison per span type. No
# alignment, no edit distance, no fuzzy matching -- a span either occurs the
# same number of times in both texts, more in one, or not at all in one.
# That is everything that can be said deterministically without guessing
# which occurrence in the rewrite "is" which occurrence in the original.
# ---------------------------------------------------------------------------

def diff_multiset(original_items: list[str], rewrite_items: list[str]) -> dict:
    orig_counts = Counter(original_items)
    rewrite_counts = Counter(rewrite_items)
    appeared, vanished, changed = [], [], []
    for key in sorted(set(orig_counts) | set(rewrite_counts)):
        o, r = orig_counts.get(key, 0), rewrite_counts.get(key, 0)
        if o == 0 and r > 0:
            appeared.append({"value": key, "count": r})
        elif o > 0 and r == 0:
            vanished.append({"value": key, "count": o})
        elif o != r:
            changed.append({"value": key, "original_count": o, "rewrite_count": r})
    return {"appeared": appeared, "vanished": vanished, "changed": changed}


CATEGORY_LABELS = {
    "numbers": "NUMBERS (incl. percentages, currency, dates, version strings)",
    "proper_nouns": "PROPER NOUNS",
    "quotes": "QUOTED SPANS",
    "urls": "URLS",
    "code": "CODE SPANS",
    # Last on purpose. It is the softest evidence in the report and the only
    # section where a finding is routinely a correct edit, so it sits below
    # the spans a reader should act on first.
    "claim_words": "CLAIM WORDS (ranking, scope, relation, requirement)",
}


def check_fidelity(original: str, rewrite: str, names: bool = False) -> dict:
    """Run every tracked-span diff between an original draft and its rewrite.

    Needs no baseline corpus and no configuration -- everything it compares
    comes from the two texts handed to it, so it works identically on the
    very first run for any user of the skill.

    Proper nouns are OFF by default (`names=True` to enable). Without a POS
    tagger the heuristic cannot tell a name from any other capitalised word,
    so it returns things like "The", "It's", "Cut" and "Apply", and a pure
    reordering -- which is most of what this skill does to a draft -- reports
    words as appearing and vanishing when nothing was invented at all. That
    noise sits directly beneath the fabricated-number banner and teaches a
    reader to skim past it, which costs more than the section is worth.
    """
    orig_spans = extract_tracked_spans(original)
    rewrite_spans = extract_tracked_spans(rewrite)

    results = {
        "numbers": diff_multiset(
            extract_numbers(orig_spans["clean"]), extract_numbers(rewrite_spans["clean"])
        ),
        # Quotes are read from the UNMASKED text: a quoted number or name is
        # still a specific worth protecting, not noise to strip.
        "quotes": diff_multiset(extract_quotes(original), extract_quotes(rewrite)),
        "urls": diff_multiset(
            [normalize_url(u) for u in orig_spans["urls"]],
            [normalize_url(u) for u in rewrite_spans["urls"]],
        ),
        "code": diff_multiset(
            [normalize_code(c) for c in orig_spans["code"]],
            [normalize_code(c) for c in rewrite_spans["code"]],
        ),
        # Read from the masked text like numbers are: `all()` in a code span
        # is an identifier, not a quantifier the prose is asserting.
        "claim_words": diff_multiset(
            extract_claim_words(orig_spans["clean"]),
            extract_claim_words(rewrite_spans["clean"]),
        ),
    }

    if names:
        results["proper_nouns"] = diff_multiset(
            extract_proper_nouns(orig_spans["clean"]),
            extract_proper_nouns(rewrite_spans["clean"]),
        )

    # How much there was to check at all. Without this the report cannot tell
    # "nothing changed" apart from "there was nothing here to change", and
    # those mean opposite things. See _format_report's vacuity warning.
    #
    # Two counters, not one, and the split is load-bearing. Claim words are
    # near-ubiquitous in real prose -- almost any paragraph carries an "all"
    # or an "only" -- so counting them toward the vacuity test would suppress
    # that warning on exactly the numberless, quoteless drafts it was added
    # for. The warning stays keyed to the four hard span types; the headline
    # count in the clean message includes claim words, because they were in
    # fact compared and saying otherwise would understate the run.
    results["_hard_spans_in_original"] = (
        len(extract_numbers(orig_spans["clean"]))
        + len(extract_quotes(original))
        + len(orig_spans["urls"])
        + len(orig_spans["code"])
    )
    results["_tracked_in_original"] = (
        results["_hard_spans_in_original"]
        + len(extract_claim_words(orig_spans["clean"]))
    )
    return results


def _format_item(item: dict, sign: str) -> str:
    times = f" (x{item['count']})" if item["count"] > 1 else ""
    return f"  {sign} {item['value']}{times}"


def _normalize_sentence(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence.strip()).lower()


def _snippet(sentence: str, pattern: re.Pattern, width: int = 96) -> str:
    """A one-line window around the match, so a long paragraph doesn't push
    the word itself off the end of the line."""
    flat = re.sub(r"\s+", " ", sentence.strip())
    if len(flat) <= width:
        return flat
    match = pattern.search(flat)
    start = max(0, match.start() - width // 3) if match else 0
    end = min(len(flat), start + width)
    return ("..." if start else "") + flat[start:end] + ("..." if end < len(flat) else "")


def _claim_contexts(word: str, source: str, other: str, limit: int = 2) -> list[str]:
    """Sentences in `source` containing `word` that `other` does not carry
    verbatim.

    The verbatim filter is the cheap half of the job: a sentence the rewrite
    kept untouched cannot be where the word went, so dropping those leaves a
    shorter list of real candidates. It does not attempt alignment -- there
    is no way to say which occurrence "is" which without guessing, and this
    script's whole contract is that it never guesses.
    """
    pattern = re.compile(rf"(?<![\w-]){re.escape(word)}(?![\w-])", re.I)
    kept = {_normalize_sentence(s) for s in _sentences(other)}
    out: list[str] = []
    for sentence in _sentences(source):
        if not pattern.search(sentence) or _normalize_sentence(sentence) in kept:
            continue
        out.append(_snippet(sentence, pattern))
        if len(out) == limit:
            break
    return out


CLAIM_WORDS_PREAMBLE = (
    "  Each of these asserts something the sentence stops asserting without it.\n"
    "  A vanished one may still be a correct cut -- this says where to look, not\n"
    "  what to do. Contexts are from the text the word is missing from."
)


def _format_claim_words(section: dict, original: str, rewrite: str) -> list[str]:
    """Render the claim-word section: group label, count, and the sentences
    the word sat in. Falls back to a bare list when the source texts weren't
    passed (e.g. a caller diffing pre-extracted results)."""
    lines = [CLAIM_WORDS_PREAMBLE]
    rows = (
        [("VANISHED", i["value"], i["count"], "original") for i in section["vanished"]]
        + [
            ("CHANGED", i["value"], i["original_count"] - i["rewrite_count"], "original")
            for i in section["changed"]
            if i["original_count"] > i["rewrite_count"]
        ]
        + [("APPEARED", i["value"], i["count"], "rewrite") for i in section["appeared"]]
        + [
            ("CHANGED", i["value"], i["rewrite_count"] - i["original_count"], "rewrite")
            for i in section["changed"]
            if i["rewrite_count"] > i["original_count"]
        ]
    )
    for verb, word, delta, side in rows:
        group = CLAIM_WORD_OF_GROUP.get(word, "?")
        count = f" (x{delta})" if delta > 1 else ""
        direction = "-" if side == "original" else "+"
        lines.append(f"  {verb:<9}{direction} {word}  [{group}]{count}")
        source, other = (original, rewrite) if side == "original" else (rewrite, original)
        if source:
            for context in _claim_contexts(word, source, other):
                lines.append(f'      "{context}"')
    return lines


def _format_report(results: dict, original: str = "", rewrite: str = "") -> str:
    lines: list[str] = []

    # The one finding that matters most, first and unmissable: a number the
    # rewrite introduced that the original never stated. Everything else in
    # this report is useful; this specific case is the reason it exists.
    new_numbers = results["numbers"]["appeared"]
    if new_numbers:
        lines.append("!" * 72)
        lines.append("NEW NUMBER(S) IN THE REWRITE, ABSENT FROM THE ORIGINAL")
        lines.append("This is the shape of a fabricated statistic -- check these first.")
        lines.append("!" * 72)
        for item in new_numbers:
            lines.append(_format_item(item, "+"))
        lines.append("")

    any_findings = bool(new_numbers)
    for category, label in CATEGORY_LABELS.items():
        # proper_nouns is absent unless --names was passed, so this iterates
        # over what the run actually produced rather than every known label.
        section = results.get(category)
        if section is None:
            continue
        if not (section["appeared"] or section["vanished"] or section["changed"]):
            continue
        any_findings = True
        lines.append(f"-- {label} --")
        if category == "claim_words":
            lines.extend(_format_claim_words(section, original, rewrite))
            lines.append("")
            continue
        for item in section["appeared"]:
            lines.append(f"  APPEARED{_format_item(item, '+')[1:]}")
        for item in section["vanished"]:
            lines.append(f"  VANISHED{_format_item(item, '-')[1:]}")
        for item in section["changed"]:
            lines.append(
                f"  CHANGED   {item['value']}"
                f"  (was x{item['original_count']}, now x{item['rewrite_count']})"
            )
        lines.append("")

    if not any_findings:
        # Name only the categories this run actually compared. Claiming to
        # have checked proper nouns when --names was not passed would be a
        # false all-clear, in a tool whose whole job is catching those.
        checked = ", ".join(
            CATEGORY_LABELS[c].lower() for c in CATEGORY_LABELS if c in results
        )
        # A clean result over an original that contained nothing to track is
        # not evidence of fidelity -- it is the absence of evidence, and the
        # two read identically unless this says so. Found by a graded eval:
        # a rewrite that dropped two of three claims from a numberless
        # sentence returned "No tracked differences", and the grader
        # correctly called the pass worthless.
        if not results.get("_hard_spans_in_original"):
            return (
                "NOTHING TO CHECK. The original contains no numbers, quoted spans, "
                "URLs or code spans, so this script can tell you nothing about "
                "whether the rewrite is faithful. It would report a clean result "
                "for a rewrite that dropped every claim in the text.\n"
                "Verify the claims by reading. This is not a pass."
            )
        return (
            f"No tracked differences: all {results['_tracked_in_original']} tracked "
            f"item(s) in the original ({checked}) are present, unchanged, at the "
            "same count, in the rewrite. A claim that ranks, scopes, compares or "
            "requires nothing, and carries no number, quote, URL or code span, is "
            "outside what this checks -- read for those."
        )

    # The same warning, as a footer, when there WERE findings but no hard
    # spans behind them. A claim-word row is a real finding and can carry a
    # whole report on its own -- and a reader who sees a populated report
    # reasonably assumes the rest of it was checked. Over a draft with no
    # numbers, quotes, URLs or code, it wasn't.
    if not results.get("_hard_spans_in_original"):
        lines.append(
            "NOTE: the original carries no numbers, quoted spans, URLs or code "
            "spans, so everything above comes from claim words alone. A dropped "
            "claim that used none of these is invisible here. Read for those."
        )
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    parser.add_argument("original", help="path to the original draft")
    parser.add_argument("rewrite", nargs="?", help="path to the rewrite; omit to read stdin")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of the human-readable report")
    parser.add_argument(
        "--names",
        action="store_true",
        help="also diff capitalised words as proper nouns. Off by default: without a "
             "POS tagger this is noisy on reordered prose, and reordering is normal here",
    )
    args = parser.parse_args()

    with open(args.original, encoding="utf-8") as fh:
        original = fh.read()
    if args.rewrite:
        with open(args.rewrite, encoding="utf-8") as fh:
            rewrite = fh.read()
    else:
        rewrite = sys.stdin.buffer.read().decode("utf-8")

    results = check_fidelity(original, rewrite, names=args.names)
    if args.json:
        # Keys prefixed with _ are internal bookkeeping for the report text
        # (see _tracked_in_original). They are not part of the JSON contract.
        print(json.dumps({k: v for k, v in results.items()
                          if not k.startswith("_")}, indent=2))
    else:
        print(_format_report(results, original, rewrite))

    # Advisory tool, by design: there is no threshold to clear, so there is
    # no verdict to compute. Exit 0 means the run completed, not that the
    # rewrite "passed" anything -- a non-zero exit here would only ever mean
    # the run itself failed (unreadable file, bad encoding).
    return 0


if __name__ == "__main__":
    sys.exit(main())
