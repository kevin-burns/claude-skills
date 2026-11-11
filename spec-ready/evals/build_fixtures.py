#!/usr/bin/env python3
"""Build spec-ready eval fixtures: per scenario a tiny git repo, a synthetic Claude Code
transcript of the person's turns, and the proposals an ideal agent would make.

The transcript lets the gate be evaluated on its own (verifiers included) without running a
session; behaviour runs (run_cases.sh) replay the same turns into a real session instead.

Usage: build_fixtures.py OUT_DIR
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE / "evals.json"
GIT_DATE = "2026-11-01T12:00:00+00:00"


def _git(repo: Path, *args: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_DATE": GIT_DATE, "GIT_COMMITTER_DATE": GIT_DATE,
           "GIT_AUTHOR_NAME": "Eval", "GIT_AUTHOR_EMAIL": "eval@example.invalid",
           "GIT_COMMITTER_NAME": "Eval", "GIT_COMMITTER_EMAIL": "eval@example.invalid"}
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def _repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "README.md").write_text("# dictation\n\nA small Mac dictation app.\n", encoding="utf-8")
    _git(path, "init", "-q", "-b", "main")
    _git(path, "add", "README.md")
    _git(path, "commit", "-q", "--no-verify", "-m", "Initial commit")


def _transcript(case: dict) -> list[dict]:
    records = []
    for n, text in enumerate(case["turns"]):
        records.append({"type": "user", "uuid": f"{case['id']}-u{n}", "message": {"role": "user", "content": text}})
        records.append({"type": "assistant", "uuid": f"{case['id']}-a{n}",
                        "message": {"role": "assistant", "content": [{"type": "text", "text": "Noted."}]}})
    return records


def _proposals(case: dict) -> list[dict]:
    return [{"item": item, "turn": f"{case['id']}-u{index}", "status": "settled",
             "statement": case["turns"][index]} for item, index in case["item_turns"].items()]


def build(out: Path) -> dict[str, Path]:
    cases = json.loads(EVALS.read_text(encoding="utf-8"))["evals"]
    built = {}
    for case in cases:
        root = out / case["id"]
        _repo(root / "repo")
        (root / "transcript.jsonl").write_text("".join(json.dumps(r) + "\n" for r in _transcript(case)),
                                               encoding="utf-8")
        (root / "proposals.json").write_text(json.dumps(_proposals(case), indent=1), encoding="utf-8")
        built[case["id"]] = root
    return built


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip().splitlines()[-1])
    for case_id, path in build(Path(sys.argv[1])).items():
        print(case_id, path)
