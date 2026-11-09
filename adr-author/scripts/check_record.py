#!/usr/bin/env python3
"""Self-check one architecture decision record, in plain words, with no model and no network.

Every finding is a question for the author, not an automatic fix: a hedge may be a deliberate
preference, and a name missing from the repo may be code not written yet.

Usage:
    check_record.py RECORD [--repo DIR] [--adr-dir DIR] [--intended NAME ...]
                    [--against DRAFT | --baseline [REF]] [--confirmed NAME ...] [--sources NOTES ...] [--json]

--against compares the final record with the draft the author approved: anything that vanished,
any claim word that changed, any figure added, and any name added without the author confirming it.
--sources checks that every figure in the record (a number, date, percentage, duration, count or
amount) appears in the author's own words.

Exit codes: 0 nothing found, 1 findings, 2 usage error or unreadable record.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from records import Record, filename_scheme, load_records, parse_record

MAX_FILE_BYTES = 1_000_000
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}
BINDING_ROLES = ("decision", "consequences")
HEDGES = ("should", "prefer", "ideally", "where practical", "where possible", "try to", "aim to",
          "recommended")
DECISION_PHRASES = ("we will", "we decided", "must not", "never")
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?[A-Za-z%]*")
CLAIM_WORDS = ("must not", "must", "should", "never", "always", "only", "all", "none", "every")


@dataclass(frozen=True)
class Finding:
    kind: str
    line: int | None
    message: str


def _normalise_name(span: str) -> str:
    """Drop the decorations people add to a name: a call `f()`, a line `a.py:12` or `a.py#L12`."""
    span = re.sub(r"\(.*\)$", "", span.strip())
    return re.sub(r"(?:[:#]L?\d+(?:-L?\d+)?)$", "", span)


def looks_like_name(span: str) -> bool:
    """Is this code span a path or an identifier the code could carry, not a value, flag or URL?"""
    span = _normalise_name(span)
    if not span or span[0] in "-$/~" or span[0].isdigit() or " " in span or "://" in span:
        return False
    if "/" in span or "::" in span or "_" in span:
        return True
    if re.search(r"\w\.\w", span):
        return True
    return bool(re.fullmatch(r"[A-Z][a-z][A-Za-z0-9]+", span))


def _candidate_files(repo: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=repo, capture_output=True, check=True,
        ).stdout
        return [repo / p for p in out.decode("utf-8", errors="replace").split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        files = []
        for path in repo.rglob("*"):
            if path.is_file() and not SKIP_DIRS.intersection(path.relative_to(repo).parts):
                files.append(path)
        return files


def _readable_texts(repo: Path, exclude: Path):
    exclude = exclude.resolve()
    for path in _candidate_files(repo):
        try:
            if path.resolve().is_relative_to(exclude) or path.stat().st_size > MAX_FILE_BYTES:
                continue
            yield path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def _word(name: str) -> re.Pattern:
    return re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])")


def name_exists(name: str, repo: Path, exclude: Path) -> bool:
    """A name exists if it is a path in the repo, or a whole word in a readable file outside the ADRs.
    `Class.method` also counts when both parts appear as words in the same file."""
    name = _normalise_name(name)
    if "*" in name:
        if any(repo.glob(name)):
            return True
    elif (repo / name).exists():
        return True
    if re.fullmatch(r"\w+(?:\.\w+)+", name):
        as_path = repo / name.replace(".", "/")
        if as_path.with_suffix(".py").exists() or as_path.is_dir():
            return True
    whole = _word(name)
    parts = [_word(p) for p in name.split(".")] if re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", name) else []
    for text in _readable_texts(repo, exclude):
        if whole.search(text) or (parts and all(p.search(text) for p in parts)):
            return True
    return False


def _decision_lines(rec: Record) -> list[tuple[int, str]]:
    return [pair for role in BINDING_ROLES for pair in rec.sections.get(role, [])]


def _binding_lines(rec: Record) -> list[tuple[int, str]]:
    """The sentences that decide something. A one-paragraph record has no sections, so all of it counts."""
    return _decision_lines(rec) or rec.sections.get("other", [])


def _check_hedges(rec: Record) -> list[Finding]:
    found = []
    for line_no, text in _binding_lines(rec):
        low = text.lower()
        if any(re.search(r"\b" + re.escape(h) + r"\b", low) for h in HEDGES):
            found.append(Finding("hedge", line_no,
                                 f"This sentence hedges, so it does not decide anything yet: '{text}'. "
                                 "Is it a firm rule, or a preference the team is happy to see broken?"))
    return found


def _check_names(rec: Record, repo: Path, adr_dir: Path, intended: frozenset[str]) -> list[Finding]:
    found = []
    for line_no, text in _binding_lines(rec):
        for span in _CODE_SPAN.findall(text):
            if span in intended or not looks_like_name(span):
                continue
            if not name_exists(span, repo, adr_dir):
                found.append(Finding("name-not-found", line_no,
                                     f"'{span}' does not appear anywhere in the repository. Is it a typo, "
                                     "or code that does not exist yet?"))
    return found


def _check_status_and_shape(rec: Record) -> list[Finding]:
    found = []
    if rec.status is None:
        found.append(Finding("no-status", None,
                             "The record has no status. Readers cannot tell whether it is proposed, "
                             "accepted or replaced."))
    if not _decision_lines(rec):
        found.append(Finding("no-decision", None,
                             "No Decision section found. That is fine for a one-paragraph record; "
                             "otherwise, which part states what was decided?"))
    for role in ("context", "options"):
        for line_no, text in rec.sections.get(role, []):
            low = text.lower()
            if any(re.search(r"\b" + re.escape(p) + r"\b", low) for p in DECISION_PHRASES):
                where = "Context" if role == "context" else "the options"
                found.append(Finding("decision-outside-decision", line_no,
                                     f"This reads like a decision but sits in {where}: '{text}'. "
                                     "Is it meant to be part of what was decided?"))
    return found


def _check_numbering(rec: Record, others: list[Record]) -> list[Finding]:
    if rec.number is None:
        return []
    numbers = [o.number for o in others if o.number is not None]
    if rec.number in numbers:
        return [Finding("number-taken", None, f"Another record already uses number {rec.number}.")]
    if numbers and rec.number > max(numbers) + 1:
        return [Finding("number-not-next", None,
                        f"The highest existing number is {max(numbers)}, so the next would be "
                        f"{max(numbers) + 1}, not {rec.number}.")]
    return []


def _check_supersede(rec: Record, others: list[Record]) -> list[Finding]:
    """Supersede links must agree in both records. Links may name a record by number or by file."""
    by_number = {o.number: o for o in others if o.number is not None}
    by_file = {o.path.name: o for o in others}
    me = rec.number if rec.number is not None else rec.path.name
    found = []

    def replaced_by_me(old: Record) -> bool:
        return old.status == "Superseded" and (
            (rec.number is not None and old.superseded_by == rec.number)
            or old.superseded_by_file == rec.path.name)

    targets = [(n, by_number.get(n)) for n in rec.supersedes] + [(f, by_file.get(f)) for f in rec.supersedes_files]
    for ref, old in targets:
        if old is None:
            found.append(Finding("supersede-link", None, f"It replaces record {ref}, which does not exist."))
        elif not replaced_by_me(old):
            found.append(Finding("supersede-link", None,
                                 f"It replaces record {ref}, but record {ref} does not yet say it was replaced "
                                 f"by record {me}. Change both in the same commit."))
    if rec.status == "Superseded":
        successor = rec.superseded_by if rec.superseded_by is not None else rec.superseded_by_file
        if successor is None:
            found.append(Finding("supersede-link", None,
                                 "The record says it was replaced but not by which record."))
        elif successor not in by_number and successor not in by_file:
            found.append(Finding("supersede-link", None,
                                 f"The record says record {successor} replaced it, but that record "
                                 "does not exist."))
    return found


def _check_scheme(rec: Record, others: list[Record]) -> list[Finding]:
    schemes = {filename_scheme(o.path) for o in [*others, rec]} - {"other"}
    if len(schemes) > 1:
        return [Finding("scheme-conflict", None,
                        "This directory mixes filename styles (" + ", ".join(sorted(schemes)) + "). "
                        "Which one should new records follow?")]
    return []


def check(record_path: Path, repo: Path, adr_dir: Path, intended: frozenset[str] = frozenset()) -> list[Finding]:
    """All findings for one record, in reading order of the checks."""
    rec = parse_record(record_path)
    others = [o for o in load_records(adr_dir) if o.path.resolve() != record_path.resolve()]
    return [
        *_check_status_and_shape(rec),
        *_check_hedges(rec),
        *_check_names(rec, repo, adr_dir, intended),
        *_check_numbering(rec, others),
        *_check_supersede(rec, others),
        *_check_scheme(rec, others),
    ]


def _claim_counts(text: str) -> Counter[str]:
    low = text.lower()
    counts: Counter[str] = Counter()
    for word in CLAIM_WORDS:
        pattern = re.compile(r"\b" + re.escape(word) + r"\b")
        counts[word] = len(pattern.findall(low))
        low = pattern.sub(" ", low)
    return +counts


_SMALL_NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                  "eleven", "twelve"]
# "one" is left out on purpose: "one service", "one-off" are not figures anyone measured.
_NUMBER_WORDS = {w: str(i) for i, w in enumerate(_SMALL_NUMBERS) if i >= 2}
_NUMBER_WORDS.update({"twenty": "20", "thirty": "30", "hundred": "100", "thousand": "1000", "dozen": "12"})
# A number keeps the word after it only when that word is a unit; "40 of them" and "about 40 services"
# are the same figure. Synonyms normalise, so "2 hours" matches "2h" and "30 seconds" matches "30s".
_UNITS = {
    "%": "%", "percent": "%", "\u20ac": "eur", "eur": "eur", "$": "usd", "usd": "usd",
    "ms": "ms", "msec": "ms", "millisecond": "ms", "milliseconds": "ms",
    "s": "s", "sec": "s", "secs": "s", "second": "s", "seconds": "s",
    "min": "min", "mins": "min", "minute": "min", "minutes": "min",
    "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
    "d": "d", "day": "d", "days": "d", "week": "w", "weeks": "w",
    "month": "mo", "months": "mo", "year": "y", "years": "y",
    "k": "k", "kb": "kb", "mb": "mb", "gb": "gb", "tb": "tb", "rps": "rps", "qps": "qps", "x": "x",
}
_UNIT_PATTERN = "|".join(sorted((re.escape(u) for u in _UNITS), key=len, reverse=True))
_FIGURE = re.compile(
    r"(?<![\w.-])(\d+(?:[.,]\d+)?)(?:\s?(" + _UNIT_PATTERN + r")(?![A-Za-z]))?"
    r"|\b(" + "|".join(_NUMBER_WORDS) + r")\s+([a-z]+)",
    re.IGNORECASE,
)
_EXEMPT_LINE = re.compile(r"^\W*(date|status|supersedes|superseded|deciders)\b", re.IGNORECASE)
_RECORD_REF = re.compile(r"\b(?:ADR[-\s]?|records?\s+)\d+\b", re.IGNORECASE)
_EDIT_DATE = re.compile(r"^\W*(amended|exception)\b.{0,30}?\d{4}-\d{2}-\d{2}", re.IGNORECASE)


def _figure_text(text: str) -> str:
    """The prose that can carry factual figures: no title, header lines, record refs or list numbers."""
    kept = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or _EXEMPT_LINE.match(stripped) or stripped == "---":
            continue
        stripped = re.sub(r"^\d+[.)]\s", "", stripped)
        stripped = re.sub(r"\d{4}-\d{2}-\d{2}", "", stripped) if _EDIT_DATE.match(stripped) else stripped
        stripped = _CODE_SPAN.sub(lambda m: "" if looks_like_name(m.group(1)) else m.group(1), stripped)
        kept.append(_RECORD_REF.sub("", stripped))
    return "\n".join(kept)


def _figures(text: str) -> dict[str, str]:
    """Normalised figure -> how it was written. 'three outages' and '3 outages' normalise alike."""
    found = {}
    for m in _FIGURE.finditer(_figure_text(text)):
        if m.group(1):
            value, unit = m.group(1).replace(",", "."), _UNITS.get((m.group(2) or "").lower(), "")
        else:
            value, unit = _NUMBER_WORDS[m.group(3).lower()], ""
        found.setdefault(value + unit, m.group(0).lower())
    return found


def unsourced_figures(record_text: str, sources: str) -> list[Finding]:
    """Figures in the record that the author's own words never state."""
    known = set(_figures(sources))
    return [Finding("unsourced-figure", None,
                    f"'{shown}' reads as a fact, but it is not in what the author said. "
                    "Where does it come from? Cite it, or leave it out.")
            for key, shown in sorted(_figures(record_text).items(), key=lambda kv: kv[1]) if key not in known]


def committed_text(record: Path, ref: str = "HEAD") -> str | None:
    """The record as committed at ref, or None when git cannot show it (new file, no repo)."""
    try:
        out = subprocess.run(["git", "show", f"{ref}:./{record.name}"], cwd=record.parent,
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.decode("utf-8", errors="replace").replace("\r\n", "\n")


def _read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")


def compare(draft: str, final: str, confirmed: frozenset[str] = frozenset(),
            label: str = "the approved draft") -> list[Finding]:
    """What changed between a baseline text (the approved draft, or the committed record) and the final
    record, beyond confirmed names."""
    found = []
    draft_spans, final_spans = set(_CODE_SPAN.findall(draft)), set(_CODE_SPAN.findall(final))
    final_numbers = set(_NUMBER.findall(final))
    vanished = sorted(draft_spans - final_spans) + sorted(
        n for n in set(_NUMBER.findall(draft)) - final_numbers if not any(n in s for s in final_spans)
    )
    for item in dict.fromkeys(vanished):
        found.append(Finding("vanished", None,
                             f"'{item}' was in {label} and is gone from the final record."))
    before, after = _claim_counts(draft), _claim_counts(final)
    if before != after:
        changes = ", ".join(f"'{w}' {before[w]} -> {after[w]}" for w in CLAIM_WORDS if before[w] != after[w])
        found.append(Finding("claim-word-changed", None,
                             f"Compared with {label}, words that set how strong the decision is "
                             f"changed ({changes}). "
                             "Was that intended?"))
    draft_figures = set(_figures(draft))
    for key, shown in sorted(_figures(final).items(), key=lambda kv: kv[1]):
        if key not in draft_figures:
            found.append(Finding("new-figure", None,
                                 f"'{shown}' is not in {label}. Where does it come from?"))
    for span in sorted(final_spans - draft_spans - confirmed):
        found.append(Finding("unconfirmed-name", None,
                             f"'{span}' is not in {label} and was not confirmed."))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Self-check an architecture decision record.")
    parser.add_argument("record", type=Path)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--adr-dir", type=Path)
    parser.add_argument("--intended", nargs="*", default=[], help="names of code that does not exist yet")
    parser.add_argument("--against", type=Path, help="the draft the author approved")
    parser.add_argument("--confirmed", nargs="*", default=[], help="names the author confirmed")
    parser.add_argument("--baseline", nargs="?", const="HEAD", metavar="REF",
                        help="amend mode: compare with the record as committed at REF (default HEAD); "
                             "the committed text also counts as a source for figures")
    parser.add_argument("--sources", nargs="*", type=Path, default=[],
                        help="the author's own words (interview notes); every figure must appear in them")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.record.is_file():
        print(f"cannot read {args.record}", file=sys.stderr)
        return 2
    findings = check(args.record, args.repo, args.adr_dir or args.record.parent, frozenset(args.intended))
    missing = [p for p in args.sources if not p.is_file()]
    if missing:
        print(f"cannot read {missing[0]}", file=sys.stderr)
        return 2
    author_words = "\n".join(_read_text(p) for p in args.sources)
    # A confirmed name is one the author gave. With notes to check against, a name that is not in
    # them stays unconfirmed, so --confirmed cannot be used to silence a finding.
    confirmed = frozenset(n for n in args.confirmed
                          if not args.sources or n.lower() in author_words.lower())
    baseline = None
    if args.baseline:
        baseline = committed_text(args.record, args.baseline)
        if baseline is None:
            print(f"{args.record} is not tracked at {args.baseline}; for a new record use --against "
                  "with the approved draft", file=sys.stderr)
            return 2
        findings += compare(baseline, _read_text(args.record), confirmed, label="the committed record")
    if args.sources:
        findings += unsourced_figures(_read_text(args.record), "\n".join([author_words, baseline or ""]))
    if args.against:
        if not args.against.is_file():
            print(f"cannot read {args.against}", file=sys.stderr)
            return 2
        if args.against.stat().st_mtime > args.record.stat().st_mtime:
            print(f"{args.against} is newer than the record, so it was made from the record; the comparison "
                  "would prove nothing. Save the approved draft before writing the record.", file=sys.stderr)
            return 2
        if _read_text(args.against) == _read_text(args.record):
            print("The record is identical to the approved draft; no revision was made.", file=sys.stderr)
        findings += compare(_read_text(args.against), _read_text(args.record), confirmed)
    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for f in findings:
            print(f"line {f.line}: {f.message}" if f.line else f.message)
        if not findings:
            print("Nothing to raise.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
