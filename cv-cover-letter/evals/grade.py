#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Offline eval for the cv-cover-letter skill.

This skill ships no code, so there is no behaviour to exercise offline. What CAN be checked is
whether the documents still say what the evidence supports -- because the two things most likely
to creep back in are the two the baseline runs produced unprompted, and the folklore this skill
exists to refuse.

The folklore check is the load-bearing one. "250-400 words" is prescribed by the popular
cover-letter skill and by most career sites, and 89 sources contained no study supporting it. A
future edit that reintroduces a word target, or that starts quoting recruiter surveys, has
quietly turned this back into the thing it was written to replace.

Checks:
  1. Frontmatter: name matches the directory, description within the 1024-char cap, third
     person, states when to use, and does not summarise the six-step workflow (a description
     that summarises the process gets followed INSTEAD of the skill body).
  2. No folklore: no word-count target, no recruiter-survey percentages presented as fact.
  3. The evidence claims carry citations, and the citations are named authors and years rather
     than "studies show".
  4. The refusals the baseline showed are needed are all present.
  5. README carries the four sections CONTRIBUTING.md requires, plus the repo backlink.
  6. references/evidence.md exists and grades its sources.

Exit 0 if all pass, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
README_MD = SKILL_DIR / "README.md"
EVIDENCE_MD = SKILL_DIR / "references" / "evidence.md"

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def near(lines: list[str], index: int, pattern: str, radius: int = 2) -> bool:
    """Does `pattern` appear within `radius` lines of lines[index]?

    Prose is hard-wrapped, so a claim and the caveat governing it routinely land on different
    lines. Radius 2 rather than 1 because these paragraphs are longer than trilium-capture's.
    """
    window = " ".join(lines[max(0, index - radius):index + radius + 1])
    return re.search(pattern, window, re.I) is not None


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        if re.match(r"^[a-z_]+:", line):
            key, _, val = line.partition(":")
            key = key.strip()
            out[key] = val.strip().lstrip(">").strip()
        elif key:
            out[key] += " " + line.strip()
    return out


def main() -> int:
    for f in (SKILL_MD, README_MD, EVIDENCE_MD):
        check(f.is_file(), f"{f.relative_to(SKILL_DIR)} is missing")
    if failures:
        report()
        return 1

    skill = SKILL_MD.read_text(encoding="utf-8")
    readme = README_MD.read_text(encoding="utf-8")
    evidence = EVIDENCE_MD.read_text(encoding="utf-8")
    lines = skill.splitlines()
    fm = frontmatter(skill)

    # 1. Frontmatter
    check(fm.get("name") == SKILL_DIR.name,
          f"frontmatter name {fm.get('name')!r} != directory {SKILL_DIR.name!r}")
    check(re.fullmatch(r"[a-z0-9-]+", fm.get("name", "")) is not None,
          "name must be letters, numbers and hyphens only")
    desc = fm.get("description", "")
    check(0 < len(desc) <= 1024, f"description is {len(desc)} chars, cap is 1024")
    check("Use when" in desc, "description must state when to use the skill")
    for first_person in (" I ", "I can ", "you can ", " We "):
        check(first_person not in f" {desc} ",
              f"description must be third person; found {first_person.strip()!r}")
    check(not re.search(r"\bstep 1\b|\bsix steps\b|\bfirst,? then\b", desc, re.I),
          "description summarises the workflow; state capability and triggers only")

    # 2. No folklore. A word target anywhere outside a sentence rejecting it is a regression.
    for i, line in enumerate(lines):
        if re.search(r"\b\d{3}\s*[-–]\s*\d{3}\s+words?\b|\b\d{3}\s+words?\b", line, re.I):
            check(near(lines, i, r"\bno empirical\b|\bfolklore\b|\bnot\b|\bno support\b|"
                                 r"\bdeliberately\b|\bno target\b|\bno word count\b"),
                  f"a word target appears without being rejected: {line.strip()[:70]!r}")
    check(re.search(r"no word count|no target length|ends when the (sourced )?claims end",
                    skill, re.I) is not None,
          "SKILL.md must state that there is no target length")
    for i, line in enumerate(lines):
        if re.search(r"\b\d{2}%\s+of\s+(recruiters|hiring managers)", line, re.I):
            check(near(lines, i, r"\bdo not cite\b|\bunusable\b|\bselling\b|\brange\b"),
                  f"a recruiter-survey figure appears as fact: {line.strip()[:70]!r}")

    # 3. Citations are named, not "studies show"
    for source in ("Wingate", "Cui", "Spence", "Galdin"):
        check(source in skill, f"SKILL.md no longer cites {source}")
    check(re.search(r"\b(19|20)\d{2}\b", skill) is not None, "citations must carry years")
    check("studies show" not in skill.lower() and "research shows" not in skill.lower(),
          "unattributed appeals to research -- name the study")

    # 4. The refusals the baselines proved are needed
    required = {
        "derived": r"\bderived\b",
        "stated-vs-derived": r"stated.{0,20}derived|derived.{0,20}stated",
        "no employer diagnosis": r"diagnos",
        "hard requirement triage": r"hard requirement",
        "coherence with the CV": r"coheren",
        "register / clear-and-human": r"clear-and-human",
    }
    for label, pattern in required.items():
        check(re.search(pattern, skill, re.I) is not None,
              f"SKILL.md no longer covers: {label}")
    check("## What this skill does NOT do" in skill,
          "SKILL.md is missing its boundaries section")

    # 5. README shape required by CONTRIBUTING.md
    for heading in ("## What it does", "## How to use it well",
                    "## What it does NOT do", "## Requirements"):
        check(heading in readme, f"README.md is missing the {heading!r} section")
    check("Part of [claude-skills](../README.md)" in readme,
          "README.md is missing the repo backlink")

    # 6. The evidence file grades its sources rather than just listing them
    check("tier" in evidence.lower(), "references/evidence.md must grade its sources")
    check("Murdoch" in evidence,
          "references/evidence.md must keep the false-positive citation warning")
    for source in ("Wingate", "Kristof-Brown", "Spence", "Galdin", "Cui"):
        check(source in evidence, f"references/evidence.md no longer cites {source}")

    report()
    return 1 if failures else 0


def report() -> None:
    if failures:
        print(f"cv-cover-letter eval: FAIL ({len(failures)} problem(s))")
        for f in failures:
            print(f"  - {f}")
    else:
        print("cv-cover-letter eval: PASS (34 checks)")


if __name__ == "__main__":
    sys.exit(main())
