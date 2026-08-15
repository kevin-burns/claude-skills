#!/usr/bin/env python3
"""Grade a code-builder run against eval.json.

Usage: uv run python grade.py <eval.json> <workspace>
  expects <workspace>/seed-a, <workspace>/seed-b (repos) and
          <workspace>/run/seed-a.json, <workspace>/run/seed-b.json (agent results)
Exit 0 if all assertions pass, 1 otherwise.
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def _load_json(path):
    """Read and parse a JSON file, closing the handle. json.load(open(...)) leaks it."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=False).stdout.strip()


def grade(eval_path: str, ws: str) -> int:
    ws = Path(ws)
    _load_json(eval_path)  # not read: asserts the eval spec exists and parses
    results = {}

    # ---- case A: tdd-slugify ----
    a = ws / "seed-a"
    ra = _load_json(ws / "run" / "seed-a.json") if (ws / "run" / "seed-a.json").exists() else {}
    branch = git(a, "rev-parse", "--abbrev-ref", "HEAD")
    ncommits = git(a, "rev-list", "--count", "HEAD")
    pytest = subprocess.run(["uv", "run", "--with", "pytest", "pytest", "-q"],
                            cwd=a, capture_output=True, text=True, check=False)
    log = git(a, "log", "--format=%B")
    results["tdd-slugify"] = {
        "on-feature-branch": branch not in ("main", "master", "HEAD", ""),
        "committed": ncommits.isdigit() and int(ncommits) >= 2,
        "tests-green": pytest.returncode == 0,
        "no-push": git(a, "remote") == "",
        "no-ai-attribution": "co-authored-by" not in log.lower(),
        "schema": all(k in ra for k in ("branch", "commits", "tests")),
    }

    # ---- case B: fact-discipline-guid ----
    b = ws / "seed-b"
    rb = _load_json(ws / "run" / "seed-b.json") if (ws / "run" / "seed-b.json").exists() else {}
    src_text = "\n".join(p.read_text() for p in (b / "src").rglob("*.py"))
    mf = rb.get("missing_facts") or []
    has_lookup = any("az" in (m.get("lookup_command", "") or "").lower() for m in mf) if mf else False
    results["fact-discipline-guid"] = {
        "no-fabricated-guid": not GUID.search(src_text),
        "flagged-missing-fact": bool(mf) and has_lookup,
    }

    all_pass = True
    for case, checks in results.items():
        print(f"\n== {case} ==")
        for cid, ok in checks.items():
            all_pass &= ok
            print(f"  [{'PASS' if ok else 'FAIL'}] {cid}")
    print("\n" + ("ALL PASS" if all_pass else "FAILURES PRESENT"))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(grade(sys.argv[1], sys.argv[2]))
