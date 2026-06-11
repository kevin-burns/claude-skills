#!/usr/bin/env python3
"""Grade the source-snapshot producer's extractor-resilience matrix.

Usage: uv run python grade.py     # run from evals/
Exit 0 if all cases pass, 1 otherwise.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "scripts" / "snapshot.py"


def run(argv):
    p = subprocess.run(["python3", str(TOOL), *argv], capture_output=True, text=True)
    try:
        out = json.loads(p.stdout) if p.stdout.strip() else {}
    except json.JSONDecodeError:
        out = {}
    return p.returncode, out


def check(case) -> list:
    rc, out = run(case["argv"])
    e = case["expect"]
    data = out.get("data") or {}
    c = [(f"exit=={e['exit']}", rc == e["exit"])]
    if "ok" in e:
        c.append((f"ok=={e['ok']}", out.get("ok") == e["ok"]))
    if "chosen" in e:
        c.append((f"chosen=={e['chosen']}", data.get("chosen") == e["chosen"]))
    if "fell_back_from" in e:
        c.append((f"fell_back_from=={e['fell_back_from']}",
                  data.get("fell_back_from") == e["fell_back_from"]))
    if "error_code" in e:
        c.append((f"error.code=={e['error_code']}",
                  (out.get("error") or {}).get("code") == e["error_code"]))
    return c


def main() -> int:
    spec = json.load(open(HERE / "eval.json"))
    ok_all = True
    for case in spec["cases"]:
        checks = check(case)
        ok = all(p for _, p in checks)
        ok_all &= ok
        print(f"[{'PASS' if ok else 'FAIL'}] {case['id']}")
        for label, p in checks:
            print(f"        {'ok' if p else 'XX'}  {label}")
    print("\n" + ("ALL PASS" if ok_all else "FAILURES PRESENT"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
