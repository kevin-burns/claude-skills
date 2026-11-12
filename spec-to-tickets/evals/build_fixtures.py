#!/usr/bin/env python3
"""Build spec-to-tickets eval fixtures: per case, a git repository holding the PRD, spec and
readiness.json (when the fixture has one), plus the case's starting breakdown (if any).

The dictation PRD and spec were written by spec-ready in its 2026-11-11 eval (scenario S8); the rota
PRD and spec were written by hand for T4, a Must-heavy breakdown. Neither contains personal data.

Usage: build_fixtures.py OUT_DIR
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
EVALS = HERE / "evals.json"
GIT_DATE = "2026-11-01T12:00:00+00:00"
READMES = {"dictation": "# dictation\n\nA small Mac dictation app.\n",
           "rota": "# rota\n\nA volunteer rota for a food bank.\n"}


def _git(repo: Path, *args: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_DATE": GIT_DATE, "GIT_COMMITTER_DATE": GIT_DATE,
           "GIT_AUTHOR_NAME": "Eval", "GIT_AUTHOR_EMAIL": "eval@example.invalid",
           "GIT_COMMITTER_NAME": "Eval", "GIT_COMMITTER_EMAIL": "eval@example.invalid"}
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def build(out: Path) -> dict[str, Path]:
    built = {}
    for case in json.loads(EVALS.read_text(encoding="utf-8"))["evals"]:
        repo = out / case["id"] / "repo"
        fixture = case.get("fixture", "dictation")
        specs = repo / "docs" / "specs" / fixture
        specs.mkdir(parents=True, exist_ok=True)
        for name in ("prd.md", "spec.md", "readiness.json"):
            if (FIXTURES / fixture / name).exists():
                shutil.copy(FIXTURES / fixture / name, specs / name)
        for item in case["setup"]:
            source = FIXTURES / item
            if source.is_dir():
                shutil.copytree(source, repo / "docs" / item, dirs_exist_ok=True)
            else:
                shutil.copy(source, repo / "docs" / item)
        (repo / "README.md").write_text(READMES[fixture], encoding="utf-8")
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "--no-verify", "-m", "Initial commit")
        built[case["id"]] = repo
    return built


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip().splitlines()[-1])
    for case_id, path in build(Path(sys.argv[1])).items():
        print(case_id, path)
