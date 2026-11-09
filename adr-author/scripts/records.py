"""Read an ADR directory into records: number, title, status, supersede links and sections.

Standard library only. Written from common Nygard and MADR practice. A record's sections are
kept as (line number, text) pairs so every finding can point the author at a line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROLES = ("context", "decision", "consequences", "options", "other")
SKIPPED_NAMES = {"readme", "index", "template"}

# Order matters: the first role whose words appear in a heading wins.
_ROLE_WORDS = (
    ("options", ("option", "alternative")),
    ("consequences", ("consequence",)),
    ("decision", ("decision outcome", "decision")),
    ("context", ("context", "problem", "driver", "background", "forces")),
)
# "Decision Drivers" names the forces behind a decision, not the decision itself.
_CONTEXT_OVERRIDES = ("driver",)

_TITLE_NUMBER = re.compile(
    r"^#\s*(?:\[?\s*ADR[-\s]?(\d+)\s*\]?[:.\s-]|(\d+)\s*[.:-])", re.IGNORECASE
)
_DATE_PREFIX = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|\d{8})(?:\D|$)")
_FILE_NUMBER = re.compile(r"^(?:adr[-_]?)?(\d+)(?:[-_.]|$)", re.IGNORECASE)
_ADR_REF = re.compile(r"(?:ADR[-\s]?)?(\d+)", re.IGNORECASE)
_STATUS_WORDS = ("proposed", "accepted", "deprecated", "superseded", "rejected")


@dataclass(frozen=True)
class Record:
    path: Path
    number: int | None
    title: str
    status: str | None
    superseded_by: int | None
    supersedes: tuple[int, ...]
    sections: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    # Repos that name records by date link them by file, not number ("Supersedes: 2026-01-10-x.md").
    superseded_by_file: str | None = None
    supersedes_files: tuple[str, ...] = ()


def section_role(heading: str) -> str:
    """Map a section heading to the part it plays in a record."""
    text = heading.lower()
    if any(word in text for word in _CONTEXT_OVERRIDES):
        return "context"
    for role, words in _ROLE_WORDS:
        if any(word in text for word in words):
            return role
    return "other"


def filename_scheme(path: Path) -> str:
    """Name the filename pattern a record follows, so two schemes in one directory can be seen."""
    stem = path.stem
    if _DATE_PREFIX.match(stem):
        return "date-slug"
    if re.match(r"^ADR-\d+-", stem, re.IGNORECASE):
        return "ADR-NNN-slug"
    if re.match(r"^adr_\d+_", stem, re.IGNORECASE):
        return "adr_NNN_slug"
    if re.match(r"^\d+-", stem):
        return "NNNN-slug"
    return "other"


def _read_lines(path: Path) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _front_matter(lines: list[str]) -> tuple[dict[str, str], int]:
    """Return simple `key: value` pairs from leading front matter and the first body line index."""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    pairs: dict[str, str] = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return pairs, i + 1
        key, sep, value = lines[i].partition(":")
        if sep:
            pairs[key.strip().lower()] = value.strip().strip("\"'")
    return {}, 0


def _header_value(line: str, key: str) -> str | None:
    """Read `Key: value`, `**Key:** value`, `**Key**: value` or `| Key | value |`."""
    stripped = line.strip()
    table = re.match(rf"^\|\s*\**{key}\**\s*\|\s*(.*?)\s*\|", stripped, re.IGNORECASE)
    if table:
        return table.group(1)
    plain = re.match(rf"^[-*]?\s*\**{key}\**\s*:\s*\**\s*(.*)$", stripped, re.IGNORECASE)
    if plain:
        return plain.group(1).strip()
    return None


def _status_word(value: str) -> str | None:
    low = value.lower()
    for word in _STATUS_WORDS:
        if word in low:
            return word.title()
    return None


def _file_refs(value: str) -> tuple[str, ...]:
    """Record files a header line points at: Markdown link targets or bare `name.md` tokens."""
    targets = re.findall(r"\]\(([^)\s]+\.md)\)", value) or re.findall(r"([\w./-]+\.md)\b", value)
    return tuple(Path(t).name for t in targets)


def _refs(value: str) -> tuple[int, ...]:
    """Record numbers a header line points at, unless it points at files (then numbers are dates)."""
    if _file_refs(value):
        return ()
    return tuple(int(n) for n in _ADR_REF.findall(value))


def _number_from_filename(path: Path) -> int | None:
    stem = path.stem
    if _DATE_PREFIX.match(stem):
        return None
    match = _FILE_NUMBER.match(stem)
    return int(match.group(1)) if match else None


def parse_record(path: Path) -> Record:
    """Parse one record. Never raises on odd structure; a record without headings is all 'other'."""
    lines = _read_lines(path)
    meta, start = _front_matter(lines)
    title, number = "", None
    status_value = meta.get("status")
    supersedes_value = meta.get("supersedes", "")
    sections: dict[str, list[tuple[int, str]]] = {}
    role = "other"
    status_heading = False
    in_fence = False

    for index in range(start, len(lines)):
        line_no, line = index + 1, lines[index]
        stripped = line.strip()
        # Code is not prose: a '# comment' or 'Status:' inside a fence is neither a heading nor a header.
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("# ") and not title:
            body = stripped[1:].strip()
            if _DATE_PREFIX.match(body):
                title = body
                continue
            title = re.sub(r"^(?:\[?\s*ADR[-\s]?\d+\s*\]?[:.\s-]*|\d+\s*[.:-]\s*)", "",
                           body, flags=re.IGNORECASE).strip()
            match = _TITLE_NUMBER.match(stripped)
            if match:
                number = int(match.group(1) or match.group(2))
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            status_heading = heading.lower() == "status"
            role = "other" if status_heading else section_role(heading)
            continue
        if not stripped:
            continue
        if status_heading and status_value is None:
            status_value = stripped
            continue
        value = _header_value(line, "status")
        if value is not None and status_value is None:
            status_value = value
            continue
        value = _header_value(line, "supersedes")
        if value is not None:
            supersedes_value = value
            continue
        sections.setdefault(role, []).append((line_no, stripped))

    status = _status_word(status_value) if status_value else None
    superseded_by, superseded_by_file = None, None
    if status == "Superseded" and status_value:
        refs, files = _refs(status_value), _file_refs(status_value)
        superseded_by = refs[0] if refs else None
        superseded_by_file = files[0] if files else None
    if number is None:
        number = _number_from_filename(path)
    return Record(
        path=path,
        number=number,
        title=title,
        status=status,
        superseded_by=superseded_by,
        supersedes=_refs(supersedes_value) if supersedes_value else (),
        sections=sections,
        superseded_by_file=superseded_by_file,
        supersedes_files=_file_refs(supersedes_value) if supersedes_value else (),
    )


def load_records(adr_dir: Path) -> list[Record]:
    """Every Markdown file in the directory is a record, except README, index and template."""
    paths = sorted(p for p in adr_dir.glob("*.md") if p.stem.lower() not in SKIPPED_NAMES)
    return [parse_record(p) for p in paths]
