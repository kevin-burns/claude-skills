#!/usr/bin/env python3
"""Refuse a commit that adds a lint or security suppression.

Kevin, 2026-09-24: "Don't introduce exclusions in code smells." An inline `noqa: S310` on a
urlopen hid a finding that bandit still raised, and public CI went red. Fix what the linter
points at, or put a reviewed exception in the bandit baseline with the reason in the commit.

Only lines the staged diff ADDS are checked, so the suppressions already in the tree do not
block unrelated work. Prose and data files are not code, so a sentence about noqa is fine.
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import tokenize
from dataclasses import dataclass

CODE_SUFFIXES = (".py", ".sh", ".bash", ".js", ".ts", ".tsx", ".go", ".rs", ".tf", ".hcl")
CONFIG_NAMES = ("pyproject.toml", "ruff.toml", ".ruff.toml", "setup.cfg", ".flake8", "tox.ini")
INLINE = re.compile(r"#\s*(noqa|nosec)\b|//\s*nolint\b|#\s*type:\s*ignore\b", re.IGNORECASE)
CONFIG = re.compile(r"per-file-ignores|extend-ignore|^\s*ignore\s*=|^\s*skips\s*=", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    text: str


def _python_comment_lines(repo: str, path: str) -> set[int] | None:
    """Line numbers of real comments in the staged copy of a Python file, or None if it
    does not tokenize (then the plain-text match is used instead)."""
    blob = subprocess.run(["git", "-C", str(repo), "show", f":{path}"],
                          capture_output=True, text=True, check=False)
    if blob.returncode != 0:
        return None
    try:
        return {tok.start[0] for tok in tokenize.generate_tokens(io.StringIO(blob.stdout).readline)
                if tok.type == tokenize.COMMENT and INLINE.search(tok.string)}
    except (tokenize.TokenError, SyntaxError):
        return None


def added_suppressions(repo: str = ".") -> list[Finding]:
    """Suppressions on lines the staged diff adds."""
    diff = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "-U0", "--no-color", "--diff-filter=AM"],
        check=True, capture_output=True, text=True,
    ).stdout
    found: list[Finding] = []
    comments: dict[str, set[int] | None] = {}
    path, lineno = "", 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else ""
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            lineno = int(m.group(1)) if m else 0
        elif raw.startswith("+") and path:
            text = raw[1:]
            name = path.rsplit("/", 1)[-1]
            if path.endswith(".py") and INLINE.search(text):
                if path not in comments:
                    comments[path] = _python_comment_lines(repo, path)
                hit = comments[path] is None or lineno in comments[path]
            else:
                hit = (path.endswith(CODE_SUFFIXES) and bool(INLINE.search(text))) or (
                    name in CONFIG_NAMES and bool(CONFIG.search(text)))
            if hit:
                found.append(Finding(path, lineno, text.strip()))
            lineno += 1
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    args = ap.parse_args(argv)
    found = added_suppressions(args.repo)
    for f in found:
        print(f"{f.path}:{f.line}: new suppression: {f.text}", file=sys.stderr)
    if found:
        print("no-new-suppressions: fix what the linter points at instead "
              "(see the no-suppressions rule). A reviewed bandit exception goes in "
              ".bandit-baseline.json with the reason in the commit message.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
