"""Publish gate: what ships in adr-author must be safe to publish and must stand alone.

Two things can leak into a public skill without anyone noticing: personal data (a home path, an
email, a host name) and the internals of a companion tool the skill is meant not to depend on.
Both are checked here on every run.

Machine- or person-specific patterns are deliberately NOT written in this file: a screening list
is itself a fact about whoever it screens for. Put them, one regex per line, in an untracked file
and point ADR_AUTHOR_PRIVATE_PATTERNS at it; that part of the test skips when it is unset.
"""

import ast
import os
import re
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".toml", ".yaml", ".yml", ".sh"}

PERSONAL = [
    re.compile(r"/Users/"),
    re.compile(r"/home/\w+"),
    re.compile(r"~/"),
    re.compile(r"[\w.+-]+@(?!example\.invalid\b)[\w-]+\.[\w.]+"),
]
# Words that belong to a checker's internals, not to a record a person reads.
INTERNALS = ["obligation", "anchor", "adr-overtaken", "unclear", "must_not", "map.toml", ".adrcheck",
             "adr-exception", "prompt_version", "applies to:"]


def shipped_files(include_evals: bool = True) -> list[Path]:
    files = []
    for path in SKILL.rglob("*"):
        parts = path.relative_to(SKILL).parts
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if parts[0] == "tests" or "__pycache__" in parts or parts[:2] == ("evals", "runs"):
            continue
        if not include_evals and parts[0] == "evals":
            continue
        files.append(path)
    return files


def hits(files: list[Path], patterns: list[re.Pattern]) -> list[str]:
    found = []
    for path in files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern in patterns:
                if pattern.search(line):
                    found.append(f"{path.relative_to(SKILL)}:{line_no}: {pattern.pattern}")
    return found


def test_there_is_something_to_check():
    assert any(p.name == "records.py" for p in shipped_files())


def test_no_personal_data():
    assert hits(shipped_files(), PERSONAL) == []


def test_no_private_patterns():
    source = os.environ.get("ADR_AUTHOR_PRIVATE_PATTERNS")
    if not source:
        pytest.skip("ADR_AUTHOR_PRIVATE_PATTERNS not set")
    lines = Path(source).read_text(encoding="utf-8").splitlines()
    patterns = [re.compile(p, re.IGNORECASE) for p in lines if p.strip() and not p.startswith("#")]
    assert hits(shipped_files(), patterns) == []


def test_no_checker_internals():
    patterns = [re.compile(re.escape(w), re.IGNORECASE) for w in INTERNALS]
    assert hits(shipped_files(include_evals=False), patterns) == []


def test_adrcheck_named_at_most_once_each():
    named = re.compile(r"adrcheck", re.IGNORECASE)
    counts = {}
    for path in shipped_files():
        rel = str(path.relative_to(SKILL))
        n = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if named.search(line))
        if n:
            counts[rel] = n
    allowed = {"SKILL.md": 1, "README.md": 1}
    assert all(rel in allowed and n <= allowed[rel] for rel, n in counts.items()), counts


def test_scripts_are_stdlib_only():
    scripts = sorted((SKILL / "scripts").glob("*.py")) + sorted((SKILL / "evals").glob("*.py"))
    siblings = {p.stem for p in scripts}
    for path in scripts:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            else:
                continue
            for name in names:
                assert name in sys.stdlib_module_names or name in siblings, f"{path.name} imports {name}"
