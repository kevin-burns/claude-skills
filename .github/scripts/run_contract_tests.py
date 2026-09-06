#!/usr/bin/env python3
"""Run every skill's contract tests as a pre-commit gate.

WHY THIS HOOK EXISTS. On 2026-09-06 a description edit passed every local gate
and turned main red. check-conventions enforced the LENGTH of the description it
changed; the repo's semantic contract for that same description --
cv-and-human/tests/test_skill_contract.py, which pins four LinkedIn trigger
phrases a routing harness had scored 54/54 -- ran only in CI. Two green checks,
neither reaching the thing that broke.

WHY IT IS NOT FILE-SCOPED. cv-and-human's contract asserts on its NEIGHBOURS'
descriptions, so editing clear-and-human can break cv-and-human's suite. A hook
that only ran the suites belonging to staged files would miss precisely that.
Same reasoning as check-conventions above it, and the whole thing is under two
seconds.

IT MUST NOT PASS WHEN IT CANNOT RUN. If no runner is available this exits
non-zero and says so. A gate that silently skips is worse than no gate: it
reports green for a check that never happened, which is the failure mode this
repo keeps re-learning.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def runner():
    """The first available way to run pytest, or None."""
    try:
        import pytest  # noqa: F401,PLC0415
        return [sys.executable, "-m", "pytest"]
    except ImportError:
        pass
    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "--quiet", "--with", "pytest", "python3", "-m", "pytest"]
    return None


def main() -> int:
    suites = sorted(ROOT.glob("*/tests/test_skill_contract.py"))
    if not suites:
        print("::error::no skill contract tests found — has the glob or the layout changed?")
        return 1

    cmd = runner()
    if cmd is None:
        print("cannot run the skill contract tests: neither pytest nor uv is available.")
        print("Install uv (https://docs.astral.sh/uv/) or `pip install pytest`.")
        print("Refusing to report success for a check that did not run.")
        return 1

    failed = []
    for suite in suites:
        skill = suite.parents[1]
        result = subprocess.run(
            [*cmd, f"tests/{suite.name}", "-q"],
            cwd=skill, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            failed.append(skill.name)
            print(f"--- {skill.name} ---")
            for line in (result.stdout + result.stderr).splitlines():
                if line.startswith("FAILED") or "AssertionError" in line:
                    print(f"  {line}")

    print(f"contract tests: {len(suites) - len(failed)}/{len(suites)} skill(s) pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
