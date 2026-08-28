#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Offline eval for the trilium-capture skill.

This skill ships no code, so there is no behaviour to exercise. What CAN be checked
deterministically is the thing that actually rots: the conventions drifting apart from each
other, or the closed label vocabulary quietly acquiring a member.

The vocabulary is the load-bearing part. Two baseline agents, given the same task and no
skill, invented two disjoint tag schemes -- `golang`/`bug`/`http` and `trip`/`status`/
`travelDate` -- with no overlap at all. That is the failure this skill exists to stop, so a
label appearing in the guidance that is not in the table, or in the table but nowhere in the
guidance, is a real defect rather than a style nit.

Checks:
  1. Frontmatter: name matches the directory, description within the 1024-char cap, third
     person, and no six-step workflow summary (a description that summarises the process
     gets followed INSTEAD of the skill body).
  2. Label vocabulary is closed and consistent: every `#label` used in SKILL.md is either in
     the vocabulary table or explicitly named as an anti-example.
  3. README carries the four sections CONTRIBUTING.md requires.
  4. The forbidden write targets appear only inside prohibitions.
  5. Provenance section present (this skill wraps an external service).

Exit 0 if all pass, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
README_MD = SKILL_DIR / "README.md"


failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def near(lines: list[str], index: int, pattern: str, radius: int = 1) -> bool:
    """Does `pattern` appear within `radius` lines of lines[index]?

    Markdown prose is hard-wrapped, so a statement and the term it governs routinely land on
    different lines: "Never write to `root`, `Calendar` or\\n`_hidden`". Both the prohibition
    check and the anti-example exemption were wrong on exactly that until they looked at a
    window instead of a line.
    """
    window = " ".join(lines[max(0, index - radius):index + radius + 1])
    return re.search(pattern, window, re.I) is not None


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out, key = {}, None
    for line in m.group(1).splitlines():
        if re.match(r"^[a-z_]+:", line):
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip()
        elif key:
            out[key] += " " + line.strip()
    return out


def main() -> int:
    check(SKILL_MD.is_file(), "SKILL.md is missing")
    check(README_MD.is_file(), "README.md is missing (CONTRIBUTING.md requires one per skill)")
    if failures:
        report()
        return 1

    skill = SKILL_MD.read_text(encoding="utf-8")
    readme = README_MD.read_text(encoding="utf-8")
    fm = frontmatter(skill)

    # 1. Frontmatter
    check(bool(fm), "SKILL.md has no YAML frontmatter")
    check(fm.get("name") == SKILL_DIR.name,
          f"frontmatter name {fm.get('name')!r} != directory {SKILL_DIR.name!r}")
    check(re.fullmatch(r"[a-z0-9-]+", fm.get("name", "")) is not None,
          "name must be letters, numbers and hyphens only")
    desc = fm.get("description", "")
    check(0 < len(desc) <= 1024, f"description is {len(desc)} chars, cap is 1024")
    for first_person in (" I ", "I can ", "you can ", "We "):
        check(first_person not in f" {desc} ",
              f"description must be third person; found {first_person.strip()!r}")
    check("Use when" in desc, "description must state when to use the skill")
    # A description that summarises the workflow gets followed instead of the skill body.
    check(not re.search(r"\bstep 1\b|\bfirst,? then\b|\bsix steps\b", desc, re.I),
          "description summarises the workflow; state capability and triggers only")

    # 2. The closed label vocabulary
    table = re.findall(r"^\| `#(\w+)` \|", skill, re.M)
    check(len(table) >= 5, f"vocabulary table has {len(table)} labels, expected the full set")
    vocab = set(table)
    # Exempt lines that DEMONSTRATE rather than prescribe: one naming a label in order to
    # forbid it, and one reporting a measurement against the live instance (whose fixture
    # label names are evidence, not guidance). An earlier version of
    # this check carried a blanket allow-list of the baseline's invented labels, which meant
    # re-introducing one of those exact labels as guidance passed the eval -- the hole was
    # found by injecting `#travelDate` back in and watching this pass. Scope the exemption to
    # the sentence doing the forbidding instead.
    skill_lines = skill.splitlines()
    scanned = "\n".join(
        line for i, line in enumerate(skill_lines)
        if not near(skill_lines, i, r"\binvented\b|\bdo not invent\b|\bmeasured\b")
    )
    used = set(re.findall(r"#(\w+)(?:=| |`)", scanned))
    used -= {"projectRoot", "captureInbox"}   # structural markers on the two roots
    # Trilium ships ~58 predefined system labels. Using one as our own silently changes the
    # instance's behaviour -- `inbox` designates where new notes are filed. Checked against
    # docs.triliumnotes.org/user-guide/advanced-usage/attributes/labels on 2026-08-28.
    TRILIUM_SYSTEM_LABELS = {
        "inbox", "archived", "template", "workspace", "iconClass", "color", "cssClass",
        "sorted", "readOnly", "toc", "viewType", "pageSize", "calendarRoot", "bookmarked",
        "widget", "run", "share", "geolocation", "disableVersioning", "versioningLimit",
        "clipperInbox", "searchHome", "docName", "titleTemplate", "webViewSrc",
    }
    collisions = sorted(vocab & TRILIUM_SYSTEM_LABELS)
    check(not collisions,
          f"vocabulary collides with Trilium system labels: {collisions}")
    # Naming a system label in order to warn about it is not adopting it. The collision
    # check above is what forbids adopting one, so system names are excluded here.
    unknown = sorted(u for u in used if u not in vocab and u not in TRILIUM_SYSTEM_LABELS)
    check(not unknown, f"labels used but not in the vocabulary table: {unknown}")
    for label in ("capture", "project", "type", "source", "captured"):
        check(label in vocab, f"vocabulary is missing the {label!r} label")
    check("do not invent labels" in skill.lower() or "closed" in skill.lower(),
          "SKILL.md must say the vocabulary is closed")

    # 3. README sections CONTRIBUTING.md requires
    for heading in ("## What it does", "## How to use it well",
                    "## What it does NOT do", "## Requirements"):
        check(heading in readme, f"README.md is missing the {heading!r} section")
    check("Part of [claude-skills](../README.md)" in readme,
          "README.md is missing the repo backlink")

    # 4. Forbidden write targets must appear only as prohibitions.
    # Checked over a two-line window: prose is hard-wrapped, so "Never write to `root`,
    # `Calendar` or\n`_hidden`" puts the target and its negation on different lines.
    for target in ("Calendar", "_hidden"):
        for i, line in enumerate(skill_lines):
            if target not in line:
                continue
            check(near(skill_lines, i, r"\bnever\b|\bnot\b|\bdo not\b|\bout of\b"),
                  f"{target!r} mentioned outside a prohibition: {line.strip()[:70]!r}")

    # 5. Provenance -- required for a skill that wraps an external service
    check("## Provenance" in skill, "SKILL.md is missing the Provenance section")
    check("AGPL" in skill, "Provenance must state Trilium's licence")

    report()
    return 1 if failures else 0


def report() -> None:
    total = 22
    if failures:
        print(f"trilium-capture eval: FAIL ({len(failures)} problem(s))")
        for f in failures:
            print(f"  - {f}")
    else:
        print(f"trilium-capture eval: PASS ({total} checks)")


if __name__ == "__main__":
    sys.exit(main())
