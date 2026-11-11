"""The tickets.md format: front matter, increments, slices.

The person edits this file by hand, so the parser is forgiving: a missing or malformed field is
reported as a problem with its line number and left empty, and parsing carries on. The checks then
run on whatever parsed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

SIZE_POINTS = {"S": 1, "M": 2, "L": 4}
MOSCOW = ("Must", "Should", "Could", "Won't")
KINDS = ("slice", "prefactor", "expand", "migrate", "contract")
REQUIRED = ("moscow", "size", "layers", "kind")

_INCREMENT = re.compile(r"^##\s+Increment\s+(\d+)\s*(?:[—:-]\s*(.*))?$", re.IGNORECASE)
_SLICE = re.compile(r"^###\s+(\S+)\s*(?:[—:-]\s*(.*))?$")
_FIELD = re.compile(r"^-\s+([A-Za-z][A-Za-z ]*?)\s*:\s*(.*)$")
_CRITERION = re.compile(r"^\s+[-*]\s+(.*?)\s*(?:\(proves:\s*(.*?)\)\s*)?$")
_LIST = re.compile(r"^\[(.*)\]$")


@dataclass(frozen=True)
class Criterion:
    text: str
    proves: str


@dataclass(frozen=True)
class Slice:
    id: str
    title: str
    moscow: str = ""
    size: str = ""
    layers: tuple[str, ...] = ()
    kind: str = ""
    traces: str = ""
    blocked_by: tuple[str, ...] = ()
    parallel: bool | None = None
    acceptance: tuple[Criterion, ...] = ()
    note: str = ""
    line: int = 0


@dataclass(frozen=True)
class Increment:
    number: int
    title: str
    slices: tuple[Slice, ...] = ()


@dataclass(frozen=True)
class Tickets:
    front: dict[str, object] = field(default_factory=dict)
    increments: tuple[Increment, ...] = ()
    accepted: tuple[dict, ...] = ()

    def slices(self) -> list[Slice]:
        return [s for inc in self.increments for s in inc.slices]


def _list(value: str) -> list[str] | None:
    match = _LIST.match(value.strip())
    if not match:
        return None
    return [part.strip().strip("'\"") for part in match.group(1).split(",") if part.strip()]


def _moscow(value: str) -> str:
    key = value.strip().lower().replace("’", "'").replace(" ", "")
    return {"must": "Must", "should": "Should", "could": "Could", "won't": "Won't", "wont": "Won't"}.get(key, "")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _front(lines: list[str], problems: list[str]) -> tuple[dict[str, object], tuple[dict, ...], int]:
    front: dict[str, object] = {}
    accepted: list[dict] = []
    if not lines or lines[0].strip() != "---":
        return front, (), 0
    current = None
    for number, raw in enumerate(lines[1:], start=2):
        if raw.strip() == "---":
            return front, tuple(accepted), number
        if current == "accepted" and raw.startswith((" ", "\t")) and raw.strip().startswith("-"):
            try:
                entry = json.loads(raw.strip()[1:].strip())
                if not isinstance(entry, dict):
                    raise ValueError("not an object")
                accepted.append(entry)
            except ValueError:
                problems.append(f"line {number}: accepted entry is not a JSON object")
            continue
        key, _, value = raw.partition(":")
        key, value = key.strip(), value.strip()
        if not key:
            continue
        current = key
        listed = _list(value)
        if key == "layers" and listed is None:
            problems.append(f"line {number}: front matter layers must be a [bracketed, list]")
            listed = []
        front[key] = listed if listed is not None else value
    problems.append("line 1: front matter is not closed with ---")
    return front, tuple(accepted), len(lines)


def _finish(raw: dict, problems: list[str]) -> Slice:
    for key in REQUIRED:
        if not raw.get(key):
            problems.append(f"line {raw['line']}: slice {raw['id']} has no valid {key}")
    return Slice(id=raw["id"], title=raw["title"], moscow=raw.get("moscow", ""), size=raw.get("size", ""),
                 layers=tuple(raw.get("layers", ())), kind=raw.get("kind", ""), traces=raw.get("traces", ""),
                 blocked_by=tuple(raw.get("blocked by", ())), parallel=raw.get("parallel"),
                 acceptance=tuple(raw.get("acceptance", ())), note=raw.get("note", ""), line=raw["line"])


def _field(raw: dict, key: str, value: str, number: int, problems: list[str]) -> None:
    key = key.lower()
    if key == "moscow":
        raw["moscow"] = _moscow(value)
        if not raw["moscow"]:
            problems.append(f"line {number}: moscow must be one of {', '.join(MOSCOW)}")
    elif key == "size":
        raw["size"] = value.strip().upper() if value.strip().upper() in SIZE_POINTS else ""
        if not raw["size"]:
            problems.append(f"line {number}: size must be S, M or L")
    elif key == "kind":
        raw["kind"] = value.strip().lower() if value.strip().lower() in KINDS else ""
        if not raw["kind"]:
            problems.append(f"line {number}: kind must be one of {', '.join(KINDS)}")
    elif key in ("layers", "blocked by"):
        listed = _list(value)
        if listed is None:
            problems.append(f"line {number}: {key} must be a [bracketed, list]")
        raw[key] = listed or []
    elif key == "parallel":
        raw["parallel"] = {"yes": True, "no": False}.get(value.strip().lower())
    elif key == "acceptance":
        raw["acceptance"] = []
    elif key in ("traces", "note"):
        raw[key] = _unquote(value)
    else:
        problems.append(f"line {number}: unknown field {key!r}")


def parse(text: str) -> tuple[Tickets, list[str]]:
    problems: list[str] = []
    lines = text.splitlines()
    front, accepted, start = _front(lines, problems)
    increments: list[Increment] = []
    inc_number, inc_title, slices = None, "", []
    raw: dict | None = None
    in_acceptance = False

    def close_slice() -> None:
        nonlocal raw
        if raw is not None:
            slices.append(_finish(raw, problems))
            raw = None

    def close_increment() -> None:
        nonlocal slices
        close_slice()
        if inc_number is not None:
            increments.append(Increment(inc_number, inc_title, tuple(slices)))
        slices = []

    for number, line in enumerate(lines[start:], start=start + 1):
        if not line.strip():
            continue
        if match := _INCREMENT.match(line):
            close_increment()
            inc_number, inc_title, in_acceptance = int(match.group(1)), (match.group(2) or "").strip(), False
            continue
        if match := _SLICE.match(line):
            close_slice()
            if inc_number is None:
                problems.append(f"line {number}: slice {match.group(1)} is outside any increment")
                inc_number, inc_title = 0, ""
            raw = {"id": match.group(1), "title": (match.group(2) or "").strip(), "line": number}
            in_acceptance = False
            continue
        if raw is None:
            continue  # prose between headings is allowed
        if in_acceptance and line.startswith((" ", "\t")):
            if crit := _CRITERION.match(line):
                raw["acceptance"].append(Criterion(crit.group(1).strip(), (crit.group(2) or "").strip()))
            continue
        if match := _FIELD.match(line):
            _field(raw, match.group(1), match.group(2), number, problems)
            in_acceptance = match.group(1).strip().lower() == "acceptance"
            continue
        in_acceptance = False
        problems.append(f"line {number}: unexpected line in slice {raw['id']}: {line.strip()[:60]}")
    close_increment()
    tickets = Tickets(front, tuple(increments), accepted)
    problems.extend(_consistency(tickets))
    return tickets, problems


def _consistency(tickets: Tickets) -> list[str]:
    """Ids are unique, and a slice names each layer once and only layers the front matter declares."""
    problems = []
    declared = set(tickets.front.get("layers") or [])
    seen: set[str] = set()
    for s in tickets.slices():
        if s.id in seen:
            problems.append(f"line {s.line}: duplicate slice id {s.id}")
        seen.add(s.id)
        if len(set(s.layers)) != len(s.layers):
            problems.append(f"line {s.line}: slice {s.id} has a duplicate layer")
        for layer in sorted(set(s.layers) - declared) if declared else ():
            problems.append(f"line {s.line}: slice {s.id} uses undeclared layer {layer!r}")
    return problems
