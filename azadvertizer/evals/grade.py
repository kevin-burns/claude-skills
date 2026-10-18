#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Behavioral eval for the azadvertizer skill — fully offline.

Two layers:
  1. CLI checks: call main() in-process against the committed fixture (a real slice of
     skillData/polPolsetRole.json plus one synthetic formula-injection policy) and assert on
     the JSON envelope (lookup, search, cross-references, grouping, staleness, sanitization,
     error/exit codes). Two checks pin the bugs the CSV parser had.
  2. Ingest fail-safe checks: monkeypatch the network and assert fetch_one refuses to
     overwrite a good cache on drift / row-floor / non-JSON, writes atomically on success,
     and keeps the file on a 304.

Exit 0 if all pass, 1 otherwise.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
from datetime import UTC, datetime
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
# the fixture carries an ancient date, so without --offline the auto-refresh would fire.
C = ["--cache-dir", str(FIX), "--offline"]
DINE_POLICY = "7ca8c8ac-3a6e-493d-99ba-c5fa35347ff2"
FHIR = "1ee56206-5dd1-42ab-b02d-8aae8b1634ce"  # in 15 initiatives; the CSV parse gave 1
UNUSED_ROLE = "849de3f8-3686-489c-bd02-732984d0c145"  # used by no policy; CSV gave [blank]

# --- A. status: provenance present ---
code, env = run(C + ["status"])
prov = env.get("data", {}).get("provenance") or {}
check("status ok + cached", env["ok"] and env["data"]["cached"] and code == 0)
check("status carries provenance counts", (prov.get("counts") or {}).get("policies") == 14,
      str(prov.get("counts")))

# --- B. staleness surfaced loudly (fixed 2020 fixture date, max-age 1) ---
code, env = run(C + ["--max-age-days", "1", "status"])
check("stale flag true for ancient snapshot", env["data"]["provenance"].get("stale") is True)
check("stale warning present", any("old" in w for w in env.get("warnings", [])))

# --- C/D. get policy by id and by name ---
code, env = run(C + ["get", "policy", DINE_POLICY])
check("get policy by id", env["ok"] and "API Management" in env["data"]["policyName"],
      env.get("error", ""))
name = env["data"]["policyName"]
code, env = run(C + ["get", "policy", name])
check("get policy by name", env["ok"] and env["data"]["policyId"] == DINE_POLICY)
check("allowed effects are an array", env["data"]["policyEffectAllowedValues"]
      == ["DeployIfNotExists", "Disabled"], str(env["data"]["policyEffectAllowedValues"]))

# --- E. search filters (substring, case-insensitive) ---
code, env = run(C + ["search", "policy", "--where", "policyCategory=storage",
                     "--fields", "policyId,policyCategory"])
rows = env["data"]
check("search storage matched>=1", env["ok"] and env["provenance"]["matched"] >= 1)
check("search storage all-Storage", all(r["policyCategory"] == "Storage" for r in rows),
      str(rows[:1]))
code, env = run(C + ["search", "policy", "--where", "policyDeprecated=false",
                     "--fields", "policyDeprecated"])
check("search matches booleans as text", env["ok"] and all(
    r["policyDeprecated"] is False for r in env["data"]))

# --- E2. pagination: page through ALL policies (policyId= matches every row) ---
code, env = run(C + ["search", "policy", "--where", "policyId=", "--fields", "policyId",
                     "--limit", "5", "--offset", "0"])
p = env["provenance"]
total_pol = p["matched"]
check("pagination page1 metadata",
      env["ok"] and p["returned"] == 5 and p["offset"] == 0 and p["limit"] == 5
      and p["has_more"] is True and p["next_offset"] == 5, str(p))
seen, off = [r["policyId"] for r in env["data"]], p["next_offset"]
while off is not None:
    code, env = run(C + ["search", "policy", "--where", "policyId=", "--fields", "policyId",
                         "--limit", "5", "--offset", str(off)])
    seen += [r["policyId"] for r in env["data"]]
    off = env["provenance"]["next_offset"]
check("pagination covers all rows, no overlap",
      len(seen) == total_pol and len(set(seen)) == total_pol,
      f"{len(seen)} seen vs {total_pol} matched")
code, env = run(C + ["search", "policy", "--where", "policyId=", "--limit", "5",
                     "--offset", "9999"])
p = env["provenance"]
check("pagination offset past end -> empty page, no next",
      p["returned"] == 0 and p["has_more"] is False and p["next_offset"] is None, str(p))

# --- F. rel policy-roles: ids resolved to names ---
code, env = run(C + ["rel", "policy-roles", DINE_POLICY])
items = env["data"]["items"]
check("policy-roles resolves id + name",
      env["ok"] and items and items[0]["id"] == "312a565d-c81f-4fd8-895a-4e21e48d571c"
      and items[0]["name"], str(items[:1]))

# --- F2. REGRESSION: every initiative of a policy, not just the last one ---
code, env = run(C + ["rel", "policy-initiatives", FHIR])
its = env["data"]["items"]
check("policy-initiatives returns all 15, distinct ids",
      env["ok"] and len(its) == 15 and len({i["id"] for i in its}) == 15
      and all(i["id"] and i["name"] and ") BuiltIn" not in i["name"] for i in its),
      f"{len(its)} items: {str(its[:1])[:200]}")
check("policy-initiatives carries the source type", all(i.get("source") for i in its))

# --- G. role get: actions arrays; an empty list stays [] ---
code, env = run(C + ["get", "role", "Contributor"])
d = env["data"]
check("role actions are a list", env["ok"] and d["RoleActions"] == ["*"],
      str(d.get("RoleActions")))
code, env = run(C + ["search", "role", "--where", "RoleId="])
check("an empty dataActions is []", any(r.get("RoleDataActions") == [] for r in env["data"]))

# --- H. rel role-policies: >=2 refs, all with ids ---
code, env = run(C + ["rel", "role-policies", "cd570a14-e51a-42ad-bac8-bafd67325302"])
its = env["data"]["items"]
check("role-policies >=2 refs with ids", env["ok"] and len(its) >= 2
      and all(i["id"] and i["name"] for i in its), str(its[:1]))

# --- H2. REGRESSION: an unused role has no policies, not one blank one ---
code, env = run(C + ["rel", "role-policies", UNUSED_ROLE])
check("unused role -> [] and exit 1", code == 1 and env["data"]["items"] == [],
      str(env["data"]["items"]))

# --- I. initiative get: meta + member policies with per-reference effects ---
code, env = run(C + ["get", "initiative", "0d1b56c6-6d1f-4a5d-8695-b15efbea6b49"])
d = env["data"]
check("initiative grouped policyCount==members",
      env["ok"] and d["policyCount"] == 5 and len(d["policies"]) == 5, str(d.get("policyCount")))
check("initiative members carry names + effect fields",
      all(m["policyName"] and "effectAllowed" in m and "effectFixed" in m
          for m in d["policies"]))
code, env = run(C + ["get", "initiative", "enforce-guardrails-apim"])
check("initiative id lookup is case-insensitive",
      env["ok"] and env["data"]["initiativeId"] == "Enforce-Guardrails-APIM", env.get("error", ""))

# --- J. output sanitization: formula-injection cell gets a leading quote ---
code, env = run(C + ["get", "policy", "00000000-0000-0000-0000-000000000001"])
check("formula-injection name neutralized",
      env["ok"] and env["data"]["policyName"].startswith("'="), env["data"].get("policyName"))
check("formula-injection desc neutralized", env["data"]["policyDescription"].startswith("'+"))

# --- K. not-found -> ok false, exit 1 ---
code, env = run(C + ["get", "policy", "does-not-exist"])
check("not-found exit 1 + ok false", code == 1 and env["ok"] is False)

# --- L. cache missing + --offline -> exit 3 (won't auto-fetch when offline) ---
with tempfile.TemporaryDirectory() as empty:
    code, env = run(["--cache-dir", empty, "--offline", "get", "policy", "x"])
    check("cache-missing+offline exit 3", code == 3 and env["ok"] is False, env.get("error", ""))

# ============ Ingest fail-safe unit checks (monkeypatched network) ============


def make_doc(n_pol=2100, n_role=450, n_ini=120):
    pol = dict.fromkeys(az.ENTITY_FIELDS["policies"], None)
    role = dict.fromkeys(az.ENTITY_FIELDS["roles"], None)
    ini = dict(dict.fromkeys(az.ENTITY_FIELDS["initiatives"], None),
               members=[dict.fromkeys(az.MEMBER_FIELDS, None)])
    return {"v": 1, "generated": "2026-10-18T00:00:00Z", "attribution": "x", "schema": {},
            "counts": {}, "policies": {f"p{i}": dict(pol) for i in range(n_pol)},
            "roles": {f"r{i}": dict(role) for i in range(n_role)},
            "initiatives": {f"i{i}": dict(ini) for i in range(n_ini)}}


def serve(body, status=200, etag='"e1"'):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    return lambda etag_in=None: (status, raw, etag)


orig_download = az._download
DATA = f"{az.SLUG}.json"

# M. drift (a field dropped from one policy) -> refuse, keep existing
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / DATA).write_text("sentinel")
    bad = make_doc()
    del bad["policies"]["p7"]["roles"]
    az._download = serve(bad)
    r = az.fetch_one(root, force=True)
    check("drift: fetch refused", r["ok"] is False and "schema drift" in r.get("error", ""),
          r.get("error", ""))
    check("drift: kept existing cache (no overwrite)", (root / DATA).read_text() == "sentinel")

# M2. format version bump -> refuse
with tempfile.TemporaryDirectory() as tmp:
    az._download = serve(dict(make_doc(), v=2))
    r = az.fetch_one(Path(tmp), force=True)
    check("version bump refused", r["ok"] is False and "v2" in r.get("error", ""))

# M3. not JSON (e.g. an HTML error page with 200) -> refuse
with tempfile.TemporaryDirectory() as tmp:
    az._download = serve(b"<html>oops</html>")
    r = az.fetch_one(Path(tmp), force=True)
    check("non-JSON refused", r["ok"] is False and "not JSON" in r.get("error", ""))

# N. row floor -> refuse
with tempfile.TemporaryDirectory() as tmp:
    az._download = serve(make_doc(n_pol=10))
    r = az.fetch_one(Path(tmp), force=True)
    check("row-floor: fetch refused", r["ok"] is False and "row floor" in r.get("error", ""))

# O. happy path -> writes data + meta (sha, etag, counts), no tmp left
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    az._download = serve(make_doc())
    r = az.fetch_one(root, force=True)
    m = az.load_meta(root) or {}
    check("happy: fetch ok + meta written",
          r["ok"] and len(m.get("sha256", "")) == 64 and m.get("etag") == '"e1"'
          and m.get("counts", {}).get("policies") == 2100, r.get("error", ""))
    check("happy: no leftover tmp file", not list(root.glob("*.tmp")))

    # O2. 304 on the stored ETag -> file kept, fetched_at bumped
    before = (root / DATA).read_bytes()
    seen_etag = []

    def not_modified(etag_in=None):
        seen_etag.append(etag_in)
        return 304, b"", '"e1"'

    az._download = not_modified
    r = az.fetch_one(root, force=False)
    check("304: sends stored ETag, keeps file",
          r.get("not_modified") and seen_etag == ['"e1"'] and (root / DATA).read_bytes() == before)

# P. auto-refresh fires when a snapshot is stale (not offline) — weekly cadence behavior


def _seed(root: Path, fetched_at: str):
    (root / DATA).write_text((FIX / DATA).read_text(encoding="utf-8"), encoding="utf-8")
    (root / f"{az.SLUG}.meta.json").write_text(json.dumps({
        "dataset": az.SLUG, "source_url": "x", "fetched_at": fetched_at, "etag": '"old"',
        "sha256": "seed", "counts": {}}))


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    _seed(root, "2020-01-01T00:00:00+00:00")  # ancient -> stale under default 7d
    big = make_doc()
    big["policies"][DINE_POLICY] = json.loads((FIX / DATA).read_text())["policies"][DINE_POLICY]
    big["policies"][DINE_POLICY]["roles"] = []
    big["policies"][DINE_POLICY]["initiatives"] = []
    az._download = serve(big)
    code, env = run(["--cache-dir", str(root), "get", "policy", DINE_POLICY])
    refreshed = any("auto-refresh" in w for w in env.get("warnings", []))
    age = (env.get("provenance") or {}).get("snapshot_age_days")
    check("auto-refresh fires on stale (non-offline)",
          refreshed and age is not None and age < 1, str(env.get("warnings")))

# Q. within the freshness window, NO refresh happens (no network touched)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    _seed(root, datetime.now(UTC).isoformat())  # fresh -> within 7d

    def _boom(etag_in=None):
        raise AssertionError("network should not be touched for a fresh snapshot")

    az._download = _boom
    code, env = run(["--cache-dir", str(root), "get", "policy", DINE_POLICY])
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
