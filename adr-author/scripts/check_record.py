#!/usr/bin/env python3
"""Self-check one architecture decision record, in plain words, with no model and no network.

Every finding is a question for the author, not an automatic fix: a hedge may be a deliberate
preference, and a name missing from the repo may be code not written yet.

Usage:
    check_record.py RECORD [--repo DIR] [--adr-dir DIR] [--intended NAME ...] [--json]

Exit codes: 0 nothing found, 1 findings, 2 usage error or unreadable record.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
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


@dataclass(frozen=True)
class Finding:
    kind: str
    line: int | None
    message: str


def looks_like_name(span: str) -> bool:
    """Is this code span a path or an identifier the code could carry, not a value or a flag?"""
    span = span.strip()
    if not span or span[0] in "-$" or span[0].isdigit() or " " in span:
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


def name_exists(name: str, repo: Path, exclude: Path) -> bool:
    """A name exists if it is a path in the repo, or a whole word in a readable file outside the ADRs."""
    if "*" in name:
        if any(repo.glob(name)):
            return True
    elif (repo / name).exists():
        return True
    pattern = re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])")
    exclude = exclude.resolve()
    for path in _candidate_files(repo):
        try:
            if path.resolve().is_relative_to(exclude) or path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if pattern.search(text):
            return True
    return False


def _binding_lines(rec: Record) -> list[tuple[int, str]]:
    return [pair for role in BINDING_ROLES for pair in rec.sections.get(role, [])]


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
    if not _binding_lines(rec):
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
    by_number = {o.number: o for o in others if o.number is not None}
    found = []
    for n in rec.supersedes:
        old = by_number.get(n)
        if old is None:
            found.append(Finding("supersede-link", None, f"It replaces record {n}, which does not exist."))
        elif old.status != "Superseded" or old.superseded_by != rec.number:
            found.append(Finding("supersede-link", None,
                                 f"It replaces record {n}, but record {n} does not yet say it was replaced "
                                 f"by record {rec.number}. Change both in the same commit."))
    if rec.status == "Superseded":
        if rec.superseded_by is None:
            found.append(Finding("supersede-link", None,
                                 "The record says it was replaced but not by which record."))
        elif rec.superseded_by not in by_number:
            found.append(Finding("supersede-link", None,
                                 f"The record says record {rec.superseded_by} replaced it, but that record "
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Self-check an architecture decision record.")
    parser.add_argument("record", type=Path)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--adr-dir", type=Path)
    parser.add_argument("--intended", nargs="*", default=[], help="names of code that does not exist yet")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.record.is_file():
        print(f"cannot read {args.record}", file=sys.stderr)
        return 2
    findings = check(args.record, args.repo, args.adr_dir or args.record.parent, frozenset(args.intended))
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
