#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Behavioral eval for the azadvertizer skill — fully offline.

Two layers:
  1. CLI checks: call main() in-process against the committed fixtures (real slices of
     skillData/polPolsetRole.json, plus one synthetic formula-injection policy, and of
     vscode/index.json) and assert on
     the JSON envelope (lookup, search, cross-references, grouping, staleness, sanitization,
     error/exit codes). Two checks pin the bugs the CSV parser had.
  2. Ingest fail-safe checks: monkeypatch the network and assert fetch_one refuses to
     overwrite a good cache on drift / row-floor / non-JSON, writes atomically on success,
     and keeps the file on a 304; for the index, that a changed field order is refused.

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

# --- K2. index datasets: Entra roles, API permissions, resource types ---
GA = "62e90394-69f5-4237-9190-012177145e10"
code, env = run(C + ["status"])
check("status lists the index source with counts",
      ((env["data"]["sources"].get("index") or {}).get("counts") or {}).get("entraRoles") == 2,
      str(env["data"].get("sources", {}).get("index")))
code, env = run(C + ["get", "entra-role", "Global Administrator"])
d = env.get("data") or {}
check("entra-role by name: positional row decoded",
      env["ok"] and d.get("entraRoleId") == GA and d.get("privileged") is True
      and d.get("entraOpsClassification") == "ControlPlane" and d.get("permissionsTotal") == 317,
      str(d))
code, env = run(C + ["get", "entra-role", GA.upper()])
check("entra-role by id, case-insensitive", env["ok"] and env["data"]["entraRoleName"]
      == "Global Administrator")
code, env = run(C + ["get", "entra-role", "88d8e3e3-8f55-4a1e-953a-9b9898b8876b"])
check("non-privileged role is privileged=false", env["ok"] and env["data"]["privileged"] is False)
check("entra-role page uses azentraidroles/ (the schema's pattern 404s)",
      env["data"]["page"].endswith("/azentraidroles/88d8e3e3-8f55-4a1e-953a-9b9898b8876b.html"))

code, env = run(C + ["get", "api-permission", "User.Read.All"])
rows = env.get("data") or []
graph = {r["permissionType"]: r for r in rows if r["appName"] == "Microsoft Graph"}
check("api-permission by value: every app and id",
      env["ok"] and len(rows) == 11 and len({r["permissionId"] for r in rows}) == 10,
      f"{len(rows)} rows")
check("Graph User.Read.All: Application + Delegated, admin consent, level 3",
      set(graph) == {"Application", "Delegated"}
      and graph["Application"]["permissionId"] == "df021288-bdef-4463-88db-98f22de89214"
      and all(r["adminConsentRequired"] is True and r["graphPrivilegeLevel"] == 3
              for r in graph.values()), str(graph)[:300])
code, env = run(C + ["get", "api-permission", "user.read.all"])
check("api-permission value lookup is case-insensitive", env["ok"] and len(env["data"]) == 11)
check("api-permission page is per app: azentraidapipermissions/<appId>_<permissionId>",
      graph["Application"]["page"].endswith("/azentraidapipermissions/"
          "00000003-0000-0000-c000-000000000000_df021288-bdef-4463-88db-98f22de89214.html"))
code, env = run(C + ["get", "api-permission", "df021288-bdef-4463-88db-98f22de89214"])
check("one permission id shared by two apps -> two rows",
      env["ok"] and {r["appName"] for r in env["data"]}
      == {"Microsoft Graph", "Office 365 SharePoint Online"}, str(env.get("data"))[:200])
check("a shared id links each app to its own page, not the Graph one",
      env["ok"] and all(r["page"].endswith(f"/{r['appId']}_{r['permissionId']}.html")
                        for r in env["data"])
      and len({r["page"] for r in env["data"]}) == 2, str(env.get("data"))[:200])
code, env = run(C + ["search", "api-permission", "--where", "appName=Microsoft Graph"])
check("search api-permission flattens per app", env["ok"]
      and env["provenance"]["matched"] == 2, str(env["provenance"].get("matched")))
code, env = run(C + ["get", "api-permission", "Not.A.Permission"])
check("unknown api-permission -> exit 1", code == 1 and env["ok"] is False)

code, env = run(C + ["get", "resource-type", "Microsoft.KeyVault/vaults"])
d = env.get("data") or {}
check("resource-type by mixed-case name: API versions",
      env["ok"] and d.get("latestStableApiVersion") == "2026-05-15"
      and d.get("latestPreviewApiVersion") == "2026-06-01-preview", str(d))
code, env = run(C + ["get", "resource-type", "microsoft.network/virtualnetworks/subnets"])
check("nested resource-type page uses underscores",
      env["ok"] and env["data"]["page"].endswith(
          "/azresourcetypes/microsoft.network_virtualnetworks_subnets.html"))
code, env = run(C + ["search", "resource-type", "--where", "resourceType=resilience"])
check("a type with no API version keeps null, not a string",
      env["ok"] and env["data"][0]["latestStableApiVersion"] is None, str(env.get("data")))
code, env = run(C + ["get", "initiative", "enforce-guardrails-apim"])
check("initiative page keeps the original-case id",
      env["data"]["page"].endswith("/azpolicyinitiativesadvertizer/Enforce-Guardrails-APIM.html"))

# --- L. cache missing + --offline -> exit 3 (won't auto-fetch when offline) ---
with tempfile.TemporaryDirectory() as empty:
    code, env = run(["--cache-dir", empty, "--offline", "get", "policy", "x"])
    check("cache-missing+offline exit 3", code == 3 and env["ok"] is False, env.get("error", ""))
with tempfile.TemporaryDirectory() as only_core:  # core cached, index not: index reads exit 3
    for f in ("polPolsetRole.json", "polPolsetRole.meta.json"):
        (Path(only_core) / f).write_bytes((FIX / f).read_bytes())
    code, env = run(["--cache-dir", only_core, "--offline", "get", "entra-role", "x"])
    check("index missing+offline exit 3, core unaffected", code == 3, env.get("error", ""))
    code, env = run(["--cache-dir", only_core, "--offline", "get", "policy", DINE_POLICY])
    check("core still answers without the index", code == 0 and env["ok"])

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


def serve(body, status=200, etag='"e1"', paths=None):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()

    def fake(etag_in=None, path=None):
        if paths is not None:
            paths.append(path)
        return status, raw, etag
    return fake


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

    def not_modified(etag_in=None, path=None):
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

    def _boom(etag_in=None, path=None):
        raise AssertionError("network should not be touched for a fresh snapshot")

    az._download = _boom
    code, env = run(["--cache-dir", str(root), "get", "policy", DINE_POLICY])
    check("fresh snapshot: no refresh, no network", env["ok"] and code == 0,
          str(env.get("error")))

# R. index ingest: a valid index is written under its own name; drift is refused


def make_index():
    fx = json.loads((FIX / "vscodeIndex.json").read_text(encoding="utf-8"))
    for ent, floor in az.INDEX_FLOORS.items():
        sample = next(iter(fx[ent].values()))
        fx[ent] = {f"k{i}": json.loads(json.dumps(sample)) for i in range(floor)}
    return fx


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    asked = []
    az._download = serve(make_index(), paths=asked)
    r = az.fetch_one(root, force=True, source="index")
    m = az.load_meta(root, az.INDEX_SLUG) or {}
    check("index: fetched from vscode/index.json into its own file",
          r["ok"] and asked == [az.INDEX_PATH] and (root / "vscodeIndex.json").exists()
          and not (root / DATA).exists() and m.get("counts", {}).get("entraRoles") == 100,
          r.get("error", ""))

    (root / "vscodeIndex.json").write_text("sentinel")
    moved = make_index()
    moved["schema"]["entraRoles"] = "[privileged (1 / 0), displayName, EntraOps classification, " \
                                    "permissionsTotal, description (220 chars)]"
    az._download = serve(moved)
    r = az.fetch_one(root, force=True, source="index")
    check("index: reordered fields refused, cache kept",
          not r["ok"] and "field order" in r.get("error", "")
          and (root / "vscodeIndex.json").read_text() == "sentinel", r.get("error", ""))

    short = make_index()
    short["entraRoles"]["k3"] = short["entraRoles"]["k3"][:4]
    az._download = serve(short)
    r = az.fetch_one(root, force=True, source="index")
    check("index: a short row refused", not r["ok"] and "5-field" in r.get("error", ""),
          r.get("error", ""))

    code = make_index()
    first = next(iter(code["apiPermissions"]))
    code["apiPermissions"][first][0][3] = "zz"
    az._download = serve(code)
    r = az.fetch_one(root, force=True, source="index")
    check("index: unknown permission type code refused",
          not r["ok"] and "'zz'" in r.get("error", ""), r.get("error", ""))

    az._download = serve(dict(make_index(), resourceTypes={}))
    r = az.fetch_one(root, force=True, source="index")
    check("index: row floor refused", not r["ok"] and "row floor" in r.get("error", ""))

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
