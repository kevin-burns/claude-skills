#!/usr/bin/env python3
"""Grade the terraform-registry CLI against eval.json (offline, deterministic).

Usage: uv run python grade.py            # run from the evals/ directory
Exit 0 if all cases pass, 1 otherwise.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE.parent / "registry_helper.py"
CACHE = HERE / "fixtures" / "cache"


def run(argv):
    proc = subprocess.run(
        ["python3", str(CLI), "--cache-dir", str(CACHE), *argv],
        capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    return proc.returncode, payload


def check_case(case) -> list:
    rc, out = run(case["argv"])
    e = case["expect"]
    data = out.get("data") or {}
    prov = out.get("provenance") or {}
    c = []
    c.append((f"exit=={e['exit']}", rc == e["exit"]))
    if "ok" in e:
        c.append((f"ok=={e['ok']}", out.get("ok") == e["ok"]))
    if "command" in e:
        c.append((f"command=={e['command']}", out.get("command") == e["command"]))
    if "min_count" in e:
        c.append(("min_count", (data.get("count") or 0) >= e["min_count"]))
    if "all_modules_provider" in e:
        c.append((f"all provider={e['all_modules_provider']}",
                  bool(data.get("modules")) and all(m.get("provider") == e["all_modules_provider"]
                                                    for m in data["modules"])))
    if "provider" in e:
        c.append((f"provider=={e['provider']}", data.get("provider") == e["provider"]))
    if "min_inputs" in e:
        c.append(("min_inputs", len(data.get("inputs", [])) >= e["min_inputs"]))
    if "min_outputs" in e:
        c.append(("min_outputs", len(data.get("outputs", [])) >= e["min_outputs"]))
    if "inputs_all_contain" in e:
        ins = data.get("inputs", [])
        c.append((f"inputs all ~{e['inputs_all_contain']}",
                  bool(ins) and all(e["inputs_all_contain"] in (i.get("name", "")) for i in ins)))
    if "inputs_count" in e:
        c.append(("inputs_count", len(data.get("inputs", [])) == e["inputs_count"]))
    if "absent_keys" in e:
        c.append((f"absent {e['absent_keys']}", all(k not in data for k in e["absent_keys"])))
    if "source_kind" in e:
        c.append((f"source_kind=={e['source_kind']}", prov.get("source_kind") == e["source_kind"]))
    if "cached" in e:
        c.append((f"cached=={e['cached']}", prov.get("cached") == e["cached"]))
    if "error_code" in e:
        c.append((f"error.code=={e['error_code']}",
                  (out.get("error") or {}).get("code") == e["error_code"]))
    return c


def main() -> int:
    spec = json.load(open(HERE / "eval.json"))
    all_pass = True
    for case in spec["cases"]:
        checks = check_case(case)
        ok = all(p for _, p in checks)
        all_pass &= ok
        print(f"[{'PASS' if ok else 'FAIL'}] {case['id']}")
        for label, p in checks:
            print(f"        {'ok' if p else 'XX'}  {label}")
    print("\n" + ("ALL PASS" if all_pass else "FAILURES PRESENT"))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
