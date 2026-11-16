#!/usr/bin/env python3
"""Refuse a commit that adds a private term to this public repository.

On 2026-09-05 screening rules that together triangulated a person reached this repo, and
gitleaks and every pre-commit hook passed them: they look for credentials, not for facts
about someone. The term list is private data itself, so it lives outside the repository
(default ~/.config/claude-skills/private-terms.txt): one term per line, matched
case-insensitively; a line starting `re:` is a regular expression; `#` starts a comment.

Only lines the staged diff adds are checked. A hit prints the file and line, never the
term, so the hook's own output cannot leak the list. A missing list fails closed (exit 2).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TERMS = Path.home() / ".config" / "claude-skills" / "private-terms.txt"


@dataclass(frozen=True)
class Hit:
    path: str
    line: int


def load_terms(path: Path) -> list[re.Pattern[str]]:
    patterns = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("re:"):
            patterns.append(re.compile(line[3:], re.IGNORECASE))
        else:
            patterns.append(re.compile(re.escape(line), re.IGNORECASE))
    return patterns


def added_hits(repo: str | Path, terms: list[re.Pattern[str]]) -> list[Hit]:
    diff = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "-U0", "--no-color", "--diff-filter=AM"],
        check=True, capture_output=True, text=True,
    ).stdout
    hits: list[Hit] = []
    path, lineno = "", 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else ""
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            lineno = int(m.group(1)) if m else 0
        elif raw.startswith("+") and path:
            if any(t.search(raw[1:]) for t in terms):
                hits.append(Hit(path, lineno))
            lineno += 1
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--terms", default=str(DEFAULT_TERMS))
    args = ap.parse_args(argv)
    terms_path = Path(args.terms)
    if not terms_path.is_file():
        print(f"private-terms: no term list at {terms_path}; refusing to commit to a public "
              "repo without it (create it, one term per line)", file=sys.stderr)
        return 2
    hits = added_hits(args.repo, load_terms(terms_path))
    for h in hits:
        print(f"{h.path}:{h.line}: matches a private term", file=sys.stderr)
    if hits:
        print("private-terms: this repo is PUBLIC. Remove the private detail, or move the "
              "file to a private repo.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
