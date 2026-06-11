#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Behavioral eval for the azadvertizer skill — fully offline.

Two layers:
  1. CLI checks: call main() in-process against the committed fixtures cache-dir and assert
     on the JSON envelope (lookup, search, relationship parsing, grouping, staleness,
     sanitization, error/exit codes).
  2. Ingest fail-safe checks: monkeypatch the network and assert fetch_one refuses to
     overwrite a good cache on schema drift / row-floor failure, and writes atomically on
     success.

Exit 0 if all pass, 1 otherwise.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
SCRIPT = HERE.parent / "scripts" / "azadvertizer.py"

spec = importlib.util.spec_from_file_location("azadv", SCRIPT)
az = importlib.util.module_from_spec(spec)
spec.loader.exec_module(az)

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))


def run(argv):
    """Call main() in-process, capture stdout JSON + exit code."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = az.main(argv)
    out = buf.getvalue()
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        return code, {"_raw": out}


# Read assertions run --offline so the eval is hermetic (no network) and deterministic:
# the fixtures carry an ancient date, so without --offline the new auto-refresh would fire.
C = ["--cache-dir", str(FIX), "--offline"]

# --- A. status: 3 datasets, provenance present ---
code, env = run(C + ["status"])
ds = env.get("data", {}).get("datasets", {})
check("status ok + 3 datasets", env["ok"] and len(ds) == 3 and code == 0)
check("status carries provenance rows", ds.get("policy", {}).get("provenance", {}).get("rows") == 12)

# --- B. staleness surfaced loudly (fixed 2020 fixture date, max-age 1) ---
code, env = run(C + ["--max-age-days", "1", "status"])
pol = env["data"]["datasets"]["policy"]
check("stale flag true for ancient snapshot", pol["provenance"].get("stale") is True)
check("stale warning present", any("stale" in w or "old" in w for w in pol.get("warnings", [])))

# --- C/D. get policy by id and by name ---
code, env = run(C + ["get", "policy", "7ca8c8ac-3a6e-493d-99ba-c5fa35347ff2"])
check("get policy by id", env["ok"] and "API Management" in env["data"]["policyName"], env.get("error", ""))
name = env["data"]["policyName"]
code, env = run(C + ["get", "policy", name])
check("get policy by name", env["ok"] and env["data"]["policyId"] == "7ca8c8ac-3a6e-493d-99ba-c5fa35347ff2")

# --- E. search filters (substring, case-insensitive) ---
code, env = run(C + ["search", "policy", "--where", "policyCategory=storage", "--fields", "policyId,policyCategory"])
rows = env["data"]
check("search storage matched>=1", env["ok"] and env["provenance"]["matched"] >= 1)
check("search storage all-Storage", all(r["policyCategory"] == "Storage" for r in rows), str(rows[:1]))

# --- F. rel policy-roles: nameid parse (name + guid) ---
code, env = run(C + ["rel", "policy-roles", "7ca8c8ac-3a6e-493d-99ba-c5fa35347ff2"])
items = env["data"]["items"]
check("policy-roles parsed nameid",
      env["ok"] and items and items[0].get("id") == "312a565d-c81f-4fd8-895a-4e21e48d571c",
      str(items[:1]))

# --- G. role get + --split: actions list; 'empty' -> [] ---
code, env = run(C + ["get", "role", "b24988ac-6180-42a0-ab88-20f7382dd24c", "--split"])
d = env["data"]
check("role actions split to list", env["ok"] and d["RoleActions"] == ["*"], str(d.get("RoleActions")))
# find a role whose RoleDataActions was the literal 'empty' -> should become []
code, env = run(C + ["search", "role", "--where", "RoleId=", "--split"])  # all roles
empties = [r for r in env["data"] if r.get("RoleDataActions") == []]
check("literal 'empty' -> [] on split", len(empties) >= 1)

# --- H. rel role-policies: comma-delim nameid, anchored split, >=2 items ---
code, env = run(C + ["search", "role", "--where", "UsedInPolicy=("])  # a role with refs
multi = next((r for r in env["data"] if r.get("UsedInPolicy", "").count("(") >= 2), None)
if multi:
    code, env = run(C + ["rel", "role-policies", multi["RoleId"]])
    its = env["data"]["items"]
    check("role-policies parsed >=2 nameid", env["ok"] and len(its) >= 2 and all("id" in i for i in its),
          str(its[:1]))
else:
    check("role-policies parsed >=2 nameid", False, "no multi-UsedInPolicy role in fixture")

# --- I. initiative get: grouped fact table ---
code, env = run(C + ["search", "initiative", "--fields", "initiativeId"])
iid = env["data"][0]["initiativeId"]
code, env = run(C + ["get", "initiative", iid])
check("initiative grouped policyCount==members",
      env["ok"] and env["data"]["policyCount"] == 5 and len(env["data"]["policies"]) == 5,
      str(env["data"].get("policyCount")))

# --- J. output sanitization: formula-injection cell gets a leading quote ---
code, env = run(C + ["get", "policy", "00000000-0000-0000-0000-000000000001"])
check("formula-injection name neutralized",
      env["ok"] and env["data"]["policyName"].startswith("'="),
      env["data"].get("policyName"))
check("formula-injection desc neutralized", env["data"]["policyDescription"].startswith("'+"))

# --- K. not-found -> ok false, exit 1 ---
code, env = run(C + ["get", "policy", "does-not-exist"])
check("not-found exit 1 + ok false", code == 1 and env["ok"] is False)

# --- L. cache missing + --offline -> exit 3 (won't auto-fetch when offline) ---
with tempfile.TemporaryDirectory() as empty:
    code, env = run(["--cache-dir", empty, "--offline", "get", "policy", "x"])
    check("cache-missing+offline exit 3", code == 3 and env["ok"] is False, env.get("error", ""))

# ============ Ingest fail-safe unit checks (monkeypatched network) ============
GOOD_HEADER = ",".join(az.DATASETS["policy"]["header"])


def make_csv(header_fields, n_rows):
    body = "\n".join(",".join(f"v{i}" for i in range(len(header_fields))) for _ in range(n_rows))
    return ",".join(header_fields) + "\n" + body + "\n"


orig_download = az._download

# M. schema drift -> refuse, keep existing
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / f"{az.DATASETS['policy']['slug']}.csv").write_text("sentinel")  # pretend good cache
    az._download = lambda url: make_csv(["wrong", "header"], 5000).encode()
    r = az.fetch_one(root, "policy", force=True)
    kept = (root / f"{az.DATASETS['policy']['slug']}.csv").read_text() == "sentinel"
    check("drift: fetch refused", r["ok"] is False and "schema drift" in r.get("error", ""))
    check("drift: kept existing cache (no overwrite)", kept)

# N. row floor -> refuse
with tempfile.TemporaryDirectory() as tmp:
    az._download = lambda url: make_csv(list(az.DATASETS["policy"]["header"]), 10).encode()
    r = az.fetch_one(Path(tmp), "policy", force=True)
    check("row-floor: fetch refused", r["ok"] is False and "row floor" in r.get("error", ""))

# O. happy path -> writes csv + meta, sha present
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    az._download = lambda url: make_csv(list(az.DATASETS["policy"]["header"]), 2500).encode()
    r = az.fetch_one(root, "policy", force=True)
    meta_ok = (root / f"{az.DATASETS['policy']['slug']}.meta.json").exists()
    m = az.load_meta(root, "policy") or {}
    check("happy: fetch ok + meta written", r["ok"] and meta_ok and len(m.get("sha256", "")) == 64,
          r.get("error", ""))
    check("happy: no leftover tmp file",
          not list(root.glob("*.tmp")))

# P. auto-refresh fires when a snapshot is stale (not offline) — weekly cadence behavior
SLUG = az.DATASETS["policy"]["slug"]


def _seed(root: Path, fetched_at: str):
    (root / f"{SLUG}.csv").write_text((FIX / f"{SLUG}.csv").read_text(encoding="utf-8"),
                                      encoding="utf-8")
    (root / f"{SLUG}.meta.json").write_text(json.dumps({
        "dataset": "policy", "source_url": "x", "fetched_at": fetched_at,
        "sha256": "seed", "rows": 12, "cols": 18}))


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    _seed(root, "2020-01-01T00:00:00+00:00")  # ancient -> stale under default 7d
    az._download = lambda url: make_csv(list(az.DATASETS["policy"]["header"]), 2500).encode()
    code, env = run(["--cache-dir", str(root), "get", "policy",
                     "7ca8c8ac-3a6e-493d-99ba-c5fa35347ff2"])
    refreshed = any("auto-refresh" in w for w in env.get("warnings", []))
    age = (env.get("provenance") or {}).get("snapshot_age_days")
    check("auto-refresh fires on stale (non-offline)",
          refreshed and age is not None and age < 1, str(env.get("warnings")))

# Q. within the freshness window, NO refresh happens (no network touched)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    _seed(root, datetime.now(timezone.utc).isoformat())  # fresh -> within 7d

    def _boom(url):
        raise AssertionError("network should not be touched for a fresh snapshot")

    az._download = _boom
    code, env = run(["--cache-dir", str(root), "get", "policy",
                     "7ca8c8ac-3a6e-493d-99ba-c5fa35347ff2"])
    check("fresh snapshot: no refresh, no network", env["ok"] and code == 0,
          str(env.get("error")))

az._download = orig_download

# ----------------------------- report -----------------------------
passed = sum(1 for _, ok, _ in RESULTS if ok)
print(f"\n== azadvertizer eval: {passed}/{len(RESULTS)} passed ==\n")
for name, ok, detail in RESULTS:
    mark = "PASS" if ok else "FAIL"
    line = f"[{mark}] {name}"
    if not ok and detail:
        line += f"  -- {detail}"
    print(line)

sys.exit(0 if passed == len(RESULTS) else 1)
