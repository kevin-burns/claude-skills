#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""azadvertizer — deterministic, offline-first lookups over AzAdvertizer's skill data file.

AzAdvertizer (https://www.azadvertizer.net, by Julian Hayward) publishes Azure Policy,
Policy Initiative and RBAC Role metadata, enriched with cross-references (which roles a
policy uses, which initiatives include a policy, which policies use a role) that exist
nowhere else in one place. It also publishes them as one combined, normalised JSON,
skillData/polPolsetRole.json (~1 MB gzip, ~7.7 MB raw, refreshed daily, ETag set), and a
compact index, vscode/index.json, that adds Entra ID roles, API permissions (Microsoft Graph
and every other first-party app) and resource types with their latest API versions.

This helper fetches each file ONCE into a provenance-stamped local cache (gzip on the wire,
decompressed at rest), validates it against a pinned shape, and answers lookups offline.
Stdlib only — no third-party dependencies. Output is a JSON envelope.

Design notes:
- The datasets are small (~22k entities and members, ~16k index rows); dict lookups are the
  whole job.
- The risk is reliability, not speed: an upstream that can change shape without notice. So
  ingest is atomic, shape-validated, and a stale snapshot is surfaced loudly in the
  envelope (never silently served as fresh).
- Output keeps the column names of the CSV exports this skill read until 2026-10
  (policyName, RoleActions, initiativePolicyId ...), so documented `--where` and `--fields`
  names and downstream consumers keep working. List-valued fields are always arrays now;
  `--split` is accepted and does nothing.
- Why the CSVs were dropped: their per-file list delimiters made two cross-references
  wrong. `policyUsedInPolicySet` entries end in ") BuiltIn;", which an anchored split never
  broke, so 1,723 of 4,574 policies reported one initiative instead of all of them; and an
  unused role's " ()" parsed as one blank item for 938 roles. The JSON carries ids as arrays.

Usage:
  azadvertizer fetch [--force] [--only core|index] [--cache-dir DIR]
  azadvertizer status [--cache-dir DIR]
  azadvertizer get <policy|role|initiative|entra-role|api-permission|resource-type> <id|name>
                   [--cache-dir DIR]
  azadvertizer search <dataset> [--where COL=SUBSTR]... [--name S]
                      [--limit N] [--offset N] [--fields a,b,c] [--cache-dir DIR]
  azadvertizer rel <policy-roles|policy-initiatives|role-policies|initiative-policies> <id>
                   [--cache-dir DIR]

Global: --max-age-days N (treat snapshot older than N as stale), --offline (never fetch).
Exit codes: 0 ok · 1 not-found/empty · 2 usage · 3 cache-missing · 4 fetch/schema error.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import http.client
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

HOST = "www.azadvertizer.net"
BASE = f"https://{HOST}"
DATA_PATH = "/skillData/polPolsetRole.json"
SOURCE_URL = BASE + DATA_PATH
SLUG = "polPolsetRole"
INDEX_PATH = "/vscode/index.json"
INDEX_SLUG = "vscodeIndex"
USER_AGENT = "azadvertizer-skill/2.0 (+https://github.com/kevin-burns/claude-skills)"
# Default freshness window. Azure governance metadata changes slowly, so a weekly refresh
# keeps facts current without hammering AzAdvertizer. Read commands auto-refresh a snapshot
# older than this (unless --offline). Tune with --max-age-days; disable refresh with --offline.
DEFAULT_MAX_AGE_DAYS = 7

# ---- Pinned shape of the upstream file. A mismatch refuses the download and keeps the cache.
FORMAT_VERSION = 1
TOP_KEYS = ("v", "generated", "attribution", "schema", "counts", "policies", "roles",
            "initiatives")
ENTITY_FIELDS = {
    "policies": ("name", "description", "version", "category", "mode", "type", "preview",
                 "deprecated", "effect", "allowedEffects", "roles", "initiatives", "added",
                 "clouds", "usGovVersion"),
    "roles": ("name", "description", "actions", "notActions", "dataActions",
              "notDataActions", "policies"),
    "initiatives": ("name", "description", "category", "version", "type", "clouds", "usGov",
                    "usGovVersion", "members"),
}
MEMBER_FIELDS = ("ref", "policy", "effect", "allowedEffects", "fixedEffect")
# Truncation guard: counts seen on 2026-10-18 were 4,574 / 986 / 249.
FLOORS = {"policies": 2000, "roles": 400, "initiatives": 100}

# ---- Pinned shape of vscode/index.json. Its rows are positional arrays, so the field order
# is pinned too: the file's own schema text for each entity must match these strings exactly.
# A reordered or added column changes that text, and the fetch is refused rather than read
# with every value shifted one place.
INDEX_TOP_KEYS = ("v", "generated", "schema", "entraRoles", "apiPermissions",
                  "apiPermissionNames", "apps", "resourceTypes")
INDEX_SCHEMA = {
    "entraRoles": "[displayName, privileged (1 / 0), EntraOps classification, "
                  "permissionsTotal, description (220 chars)]",
    "apiPermissions": "permission id -> [[appId, appName, value, permission type code, "
                      "adminConsentRequired (1 / 0), displayName (120 chars), "
                      "graphPrivilegeLevel], ...] (one entry per app the id belongs to)",
    "apps": "[appName, permissionCount]",
    "resourceTypes": "[displayName, latestStableApiVersion, latestPreviewApiVersion (only when "
                     "newer than the stable one), providerDisplayName, operationsCount, "
                     "policyAliasesCount]",
}
INDEX_ROW_LEN = {"entraRoles": 5, "apps": 2, "resourceTypes": 6}
API_ENTRY_LEN = 7
PERMISSION_TYPES = {"ar": "Application", "oa": "Delegated",
                    "rs": "Resource-specific (application)"}
# Truncation guard: counts seen on 2026-10-19 were 145 / 2,802 / 187 / 12,379.
INDEX_FLOORS = {"entraRoles": 100, "apiPermissions": 1500, "apps": 100, "resourceTypes": 8000}

# Dataset name (CLI) -> source file, entity key in the file, id column and name column.
DATASETS: dict[str, dict] = {
    "policy": {"source": "core", "entity": "policies", "key": "policyId",
               "name_col": "policyName"},
    "role": {"source": "core", "entity": "roles", "key": "RoleId", "name_col": "RoleName"},
    "initiative": {"source": "core", "entity": "initiatives", "key": "initiativeId",
                   "name_col": "initiativeName"},
    "entra-role": {"source": "index", "entity": "entraRoles", "key": "entraRoleId",
                   "name_col": "entraRoleName"},
    "api-permission": {"source": "index", "entity": "apiPermissions", "key": "permissionId",
                       "name_col": "permissionValue"},
    "resource-type": {"source": "index", "entity": "resourceTypes", "key": "resourceType",
                      "name_col": "resourceTypeName"},
}
# Page links, each checked against the live site with a made-up id as the 404 control, and
# matching the index's schema block since its 2026-10-20 publish. An API permission page is
# per app, <appId>_<permissionId>: the bare <permissionId>.html forwards to the Microsoft
# Graph permission, which is the wrong page for every other app (checked 2026-10-21).
PAGES = {
    "policy": "/azpolicyadvertizer/{}.html",
    "initiative": "/azpolicyinitiativesadvertizer/{}.html",
    "role": "/azrolesadvertizer/{}.html",
    "resource-type": "/azresourcetypes/{}.html",
    "entra-role": "/azentraidroles/{}.html",
    "api-permission": "/azentraidapipermissions/{}_{}.html",
}


def page(name, *ident):
    return BASE + PAGES[name].format(*ident)

INITIATIVE_COLS = (
    "initiativeId", "initiativeName", "initiativeDescription", "initiativeCategory",
    "initiativeVersion", "initiativeType", "initiativeCloudEnvs", "initiativeAzUSGov",
    "initiativeVersionAzUSGov",
)


# ----------------------------- envelope -----------------------------
def envelope(command, data=None, provenance=None, warnings=None, error=None):
    return {
        "ok": error is None,
        "command": command,
        "data": data,
        "provenance": provenance or {},
        "warnings": warnings or [],
        "error": error,
    }


def emit(env, code):
    json.dump(env, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return code


# ----------------------------- cache paths -----------------------------
def cache_root(args) -> Path:
    if args.cache_dir:
        return Path(args.cache_dir).expanduser()
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "azadvertizer"


def data_path(root: Path, slug: str = SLUG) -> Path:
    return root / f"{slug}.json"


def meta_path(root: Path, slug: str = SLUG) -> Path:
    return root / f"{slug}.meta.json"


# ----------------------------- fetch / ingest -----------------------------
def _download(etag: str | None = None, path: str = DATA_PATH) -> tuple[int, bytes, str | None]:
    """GET a data file. Returns (status, body, etag). http.client rather than urlopen:
    the host and scheme are fixed here, so there is no URL a caller could redirect.
    The server gzips whether or not it is asked to, so the header is sent and honoured."""
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    if etag:
        headers["If-None-Match"] = etag
    conn = http.client.HTTPSConnection(HOST, timeout=90)
    try:
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        if resp.status == 200 and resp.getheader("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return resp.status, raw, resp.getheader("ETag")
    finally:
        conn.close()


def validate(doc) -> str | None:
    """None if the document has the pinned shape, else a reason. Checks every entity and
    member, not a sample: a field dropped from some rows is exactly the drift to catch."""
    if not isinstance(doc, dict):
        return "schema drift: top level is not an object"
    missing = [k for k in TOP_KEYS if k not in doc]
    if missing:
        return f"schema drift: missing top-level keys {missing}"
    if doc["v"] != FORMAT_VERSION:
        return f"schema drift: format v{doc['v']}, pinned v{FORMAT_VERSION}"
    for ent, fields in ENTITY_FIELDS.items():
        rows = doc[ent]
        if not isinstance(rows, dict):
            return f"schema drift: {ent} is not an object keyed by id"
        if len(rows) < FLOORS[ent]:
            return (f"row floor: {ent} has {len(rows)}, expected >= {FLOORS[ent]} "
                    f"(possible truncated download)")
        for eid, row in rows.items():
            lost = [f for f in fields if f not in row]
            if lost:
                return f"schema drift: {ent}[{eid}] lacks {lost}"
            if ent == "initiatives":
                for m in row["members"]:
                    lost = [f for f in MEMBER_FIELDS if f not in m]
                    if lost:
                        return f"schema drift: initiative {eid} member lacks {lost}"
    return None


def validate_index(doc) -> str | None:
    """None if vscode/index.json has the pinned shape, else a reason. Every row is checked."""
    if not isinstance(doc, dict):
        return "schema drift: top level is not an object"
    missing = [k for k in INDEX_TOP_KEYS if k not in doc]
    if missing:
        return f"schema drift: missing top-level keys {missing}"
    if doc["v"] != FORMAT_VERSION:
        return f"schema drift: format v{doc['v']}, pinned v{FORMAT_VERSION}"
    schema = doc["schema"] if isinstance(doc["schema"], dict) else {}
    for ent, text in INDEX_SCHEMA.items():
        if schema.get(ent) != text:
            return f"schema drift: {ent} field order changed: {schema.get(ent)!r}"
    if (schema.get("codes") or {}).get("permissionType") != PERMISSION_TYPES:
        return "schema drift: permission type codes changed"
    for ent, floor in INDEX_FLOORS.items():
        rows = doc[ent]
        if not isinstance(rows, dict):
            return f"schema drift: {ent} is not an object keyed by id"
        if len(rows) < floor:
            return (f"row floor: {ent} has {len(rows)}, expected >= {floor} "
                    f"(possible truncated download)")
    for ent, width in INDEX_ROW_LEN.items():
        for eid, row in doc[ent].items():
            if not isinstance(row, list) or len(row) != width:
                return f"schema drift: {ent}[{eid}] is not a {width}-field row"
    for pid, entries in doc["apiPermissions"].items():
        for e in entries if isinstance(entries, list) else [None]:
            if not isinstance(e, list) or len(e) != API_ENTRY_LEN:
                return f"schema drift: apiPermissions[{pid}] entry is not {API_ENTRY_LEN} fields"
            if e[3] not in PERMISSION_TYPES:
                return f"schema drift: apiPermissions[{pid}] has type code {e[3]!r}"
    if not isinstance(doc["apiPermissionNames"], dict):
        return "schema drift: apiPermissionNames is not an object"
    return None


# Source name -> where it lives, its cache slug, its validator and the entities it counts.
SOURCES = {
    "core": {"path": DATA_PATH, "slug": SLUG, "validate": validate,
             "counted": tuple(ENTITY_FIELDS)},
    "index": {"path": INDEX_PATH, "slug": INDEX_SLUG, "validate": validate_index,
              "counted": tuple(INDEX_FLOORS)},
}


def fetch_one(root: Path, force: bool = True, source: str = "core") -> dict:
    src = SOURCES[source]
    slug = src["slug"]
    old = load_meta(root, slug) or {}
    have = data_path(root, slug).exists()
    try:
        status, raw, etag = _download(None if force or not have else old.get("etag"),
                                      src["path"])
    except Exception as exc:  # network — keep any existing snapshot
        return {"ok": False, "error": f"download failed: {exc}", "kept_existing": have}
    if status == 304 and have:
        old["fetched_at"] = datetime.now(UTC).isoformat()
        old["not_modified"] = True
        meta_path(root, slug).write_text(json.dumps(old, indent=2))
        return {"ok": True, "not_modified": True, "counts": old.get("counts")}
    if status != 200:
        return {"ok": False, "error": f"download failed: HTTP {status}", "kept_existing": have}
    try:
        doc = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"schema drift: not JSON ({exc})", "kept_existing": have}
    problem = src["validate"](doc)
    if problem:
        return {"ok": False, "error": problem, "kept_existing": have}

    root.mkdir(parents=True, exist_ok=True)
    tmp = data_path(root, slug).with_suffix(".json.tmp")
    with open(tmp, "wb") as f:  # atomic: temp -> fsync -> replace
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, data_path(root, slug))
    counts = {ent: len(doc[ent]) for ent in src["counted"]}
    meta = {
        "dataset": slug, "source_url": BASE + src["path"],
        "fetched_at": datetime.now(UTC).isoformat(),
        "generated": doc.get("generated"), "etag": etag,
        "sha256": hashlib.sha256(raw).hexdigest(), "counts": counts,
        "attribution": doc.get("attribution")
        or "Data from AzAdvertizer (Julian Hayward), https://www.azadvertizer.net",
    }
    meta_path(root, slug).write_text(json.dumps(meta, indent=2))
    return {"ok": True, "counts": counts}


# ----------------------------- load + provenance -----------------------------
def load_meta(root: Path, slug: str = SLUG) -> dict | None:
    mp = meta_path(root, slug)
    if not mp.exists():
        return None
    return json.loads(mp.read_text())


def snapshot_provenance(root: Path, max_age_days: int | None, slug: str = SLUG):
    meta = load_meta(root, slug)
    if not meta:
        return None, [f"no {slug} snapshot cached — run: azadvertizer fetch"]
    prov = dict(meta)
    warns = []
    try:
        fetched = datetime.fromisoformat(meta["fetched_at"])
        age = (datetime.now(UTC) - fetched).total_seconds() / 86400
        prov["snapshot_age_days"] = round(age, 2)
        prov["stale"] = bool(max_age_days is not None and age > max_age_days)
        if prov["stale"]:
            warns.append(f"snapshot is {age:.1f}d old (> --max-age-days {max_age_days}); "
                         f"re-run: azadvertizer fetch")
    except (KeyError, ValueError):
        prov["snapshot_age_days"] = None
        prov["stale"] = None
    return prov, warns


def load_doc(root: Path, slug: str = SLUG) -> dict:
    dp = data_path(root, slug)
    if not dp.exists():
        raise FileNotFoundError(slug)
    return json.loads(dp.read_text(encoding="utf-8-sig"))


# ----------------------------- rows in the legacy column names -----------------------------
def _ref(doc, ent, eid, with_source=False):
    row = doc[ent].get(eid) or {}
    item = {"name": row.get("name"), "id": eid}
    if with_source:
        item["source"] = row.get("type")
    return item


def policy_row(doc, pid):
    p = doc["policies"][pid]
    return {
        "policyName": p["name"], "policyDescription": p["description"], "policyId": pid,
        "policyVersion": p["version"], "policyCategory": p["category"],
        "policyMode": p["mode"], "policyType": p["type"], "policyPreview": p["preview"],
        "policyDeprecated": p["deprecated"], "policyEffect": p["effect"],
        "policyEffectAllowedValues": p["allowedEffects"],
        "policyRolesUsedCount": len(p["roles"]),
        "policyRolesUsed": [_ref(doc, "roles", r) for r in p["roles"]],
        "policyUsedInPolicySetCount": len(p["initiatives"]),
        "policyUsedInPolicySet": [_ref(doc, "initiatives", i, True) for i in p["initiatives"]],
        "dateAdded": p["added"], "cloudEnvs": p["clouds"], "azUSGovVersion": p["usGovVersion"],
        "page": page("policy", pid),
    }


def role_row(doc, rid):
    r = doc["roles"][rid]
    return {
        "RoleId": rid, "RoleName": r["name"], "RoleDescription": r["description"],
        "RoleActions": r["actions"], "RoleNotActions": r["notActions"],
        "RoleDataActions": r["dataActions"], "RoleNotDataActions": r["notDataActions"],
        "UsedInPolicyCount": len(r["policies"]),
        "UsedInPolicy": [_ref(doc, "policies", p) for p in r["policies"]],
        "page": page("role", rid),
    }


def initiative_meta(doc, iid):
    i = doc["initiatives"][iid]
    return {
        "initiativeId": iid, "initiativeName": i["name"],
        "initiativeDescription": i["description"], "initiativeCategory": i["category"],
        "initiativeVersion": i["version"], "initiativeType": i["type"],
        "initiativeCloudEnvs": i["clouds"], "initiativeAzUSGov": i["usGov"],
        "initiativeVersionAzUSGov": i["usGovVersion"], "page": page("initiative", iid),
    }


def initiative_full(doc, iid):
    meta = initiative_meta(doc, iid)
    members = []
    for m in doc["initiatives"][iid]["members"]:
        pol = doc["policies"].get(m["policy"]) or {}
        members.append({
            "policyReferenceId": m["ref"], "policyId": m["policy"],
            "policyName": pol.get("name"), "policyCategory": pol.get("category"),
            "effectDefault": m["effect"], "effectAllowed": m["allowedEffects"],
            "effectFixed": m["fixedEffect"],
        })
    meta["policyCount"] = len(members)
    meta["policies"] = members
    return sanitize(meta)


def entra_role_row(doc, rid):
    name, privileged, tier, total, desc = doc["entraRoles"][rid]
    return {
        "entraRoleId": rid, "entraRoleName": name, "privileged": bool(privileged),
        "entraOpsClassification": tier, "permissionsTotal": total,
        "entraRoleDescription": desc, "page": page("entra-role", rid),
    }


def api_permission_rows(doc, pid):
    """One row per entry: 64 ids carry two. 12 are shared by two apps; 52 are one app using
    the same GUID for its Application and Delegated permission (Graph's User.Export.All is
    one, and Microsoft's permissions reference lists it that way)."""
    out = []
    for app_id, app_name, value, kind, consent, display, graph_level in doc["apiPermissions"][pid]:
        out.append({
            "permissionId": pid, "permissionValue": value, "permissionDisplayName": display,
            "permissionType": PERMISSION_TYPES[kind], "adminConsentRequired": bool(consent),
            "graphPrivilegeLevel": graph_level, "appId": app_id, "appName": app_name,
            "page": page("api-permission", app_id, pid),
        })
    return out


def resource_type_row(doc, key):
    name, stable, preview, provider, ops, aliases = doc["resourceTypes"][key]
    return {
        "resourceType": key, "resourceTypeName": name, "latestStableApiVersion": stable,
        "latestPreviewApiVersion": preview, "providerDisplayName": provider,
        "operationsCount": ops, "policyAliasesCount": aliases,
        "page": page("resource-type", key.replace("/", "_")),
    }


ROW_BUILDERS = {"policy": policy_row, "role": role_row, "initiative": initiative_meta,
                "entra-role": entra_role_row, "resource-type": resource_type_row}


def iter_rows(doc, name):
    """Every row of a dataset in file order; api-permission yields one row per (id, app)."""
    for eid in doc[DATASETS[name]["entity"]]:
        if name == "api-permission":
            yield from api_permission_rows(doc, eid)
        else:
            yield ROW_BUILDERS[name](doc, eid)


def _name_of(doc, name, eid):
    row = doc[DATASETS[name]["entity"]][eid]
    return row.get("name") if isinstance(row, dict) else row[0]


def find_id(doc, name, ident):
    """Exact match on id (case-insensitive: ALZ initiative ids vary in case, the index keys
    are lower-cased) or on the display name."""
    ent = doc[DATASETS[name]["entity"]]
    if ident in ent:
        return ident
    low = ident.lower()
    for eid in ent:
        if eid.lower() == low or (name != "api-permission" and _name_of(doc, name, eid) == ident):
            return eid
    return None


def find_permission_ids(doc, ident):
    """A permission id, or a permission value such as User.Read.All. One value is usually
    several ids: Application and Delegated variants, and the same name on other apps."""
    if ident.lower() in doc["apiPermissions"]:
        return [ident.lower()]
    names = doc["apiPermissionNames"]
    if ident in names:
        return list(names[ident])
    low = ident.lower()
    return [pid for value, ids in names.items() if value.lower() == low for pid in ids]


# ----------------------------- sanitization -----------------------------
# A leading =, +, -, @ (or tab/CR) makes a cell a spreadsheet-formula-injection payload.
# Harmless in JSON, dangerous if re-exported to CSV/Excel or rendered. Neutralize on output.
_FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")


def sanitize(value):
    if isinstance(value, str) and value[:1] in _FORMULA_LEAD:
        return "'" + value
    if isinstance(value, list):
        return [sanitize(x) for x in value]
    if isinstance(value, dict):
        return {k: sanitize(x) for k, x in value.items()}
    return value


def _text(value) -> str:
    """What a --where substring is matched against: lists and refs flattened to text."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "; ".join(_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(f"{v}" for v in value.values() if v is not None)
    return str(value)


# ----------------------------- commands -----------------------------
def cmd_fetch(args) -> int:
    root = cache_root(args)
    warns = []
    wanted = list(SOURCES)
    if args.only in SOURCES:
        wanted = [args.only]
    elif args.only:
        warns.append(f"--only {args.only!r} ignored: the sources are {', '.join(SOURCES)}")
    results = {}
    for name in wanted:
        if not args.force and data_path(root, SOURCES[name]["slug"]).exists() \
                and not args.refresh:
            results[name] = {"ok": True, "skipped": "already cached (use --force)"}
        else:
            results[name] = fetch_one(root, force=args.force, source=name)
    env = envelope("fetch", data={"cache_dir": str(root), "result": results}, warnings=warns)
    failed = {n: r.get("error") for n, r in results.items() if not r["ok"]}
    if failed:
        env["ok"] = False
        env["error"] = "; ".join(f"{n}: {e}" for n, e in failed.items())
        return emit(env, 4)
    return emit(env, 0)


def cmd_status(args) -> int:
    root = cache_root(args)
    prov, warns = snapshot_provenance(root, args.max_age_days)
    sources = {"core": prov}
    for name, src in SOURCES.items():
        if name != "core":
            sources[name], w = snapshot_provenance(root, args.max_age_days, src["slug"])
            warns += w
    return emit(envelope("status", data={"cache_dir": str(root), "cached": prov is not None,
                                         "provenance": prov, "sources": sources},
                         warnings=warns), 0)


def _maybe_refresh(args, root, prov, warns, source="core"):
    """Auto-refresh a missing or stale snapshot unless --offline.

    Default freshness is one week (--max-age-days). Within that window nothing refreshes, so
    repeated calls in a session stay deterministic; past it, the next read pulls a fresh
    snapshot (a conditional GET on the stored ETag). --offline disables refresh entirely.
    Returns (prov, warns, err) where err is an emitted exit code (int) or None.
    """
    missing = prov is None
    stale = bool(prov and prov.get("stale"))
    if not (missing or stale):
        return prov, warns, None
    if args.offline:
        if missing:
            return prov, warns, emit(envelope(
                args.cmd, warnings=warns,
                error="cache missing and --offline set — run: azadvertizer fetch"), 3)
        return prov, warns + ["--offline: serving stale snapshot without refresh"], None
    r = fetch_one(root, force=missing, source=source)
    if r["ok"]:
        prov2, w2 = snapshot_provenance(root, args.max_age_days, SOURCES[source]["slug"])
        reason = "missing" if missing else f"older than {args.max_age_days}d"
        return prov2, w2 + [f"auto-refreshed ({reason})"], None
    if missing:
        return prov, warns, emit(envelope(
            args.cmd, warnings=warns,
            error=f"cache missing and refresh failed: {r.get('error')}"), 4)
    return prov, warns + [f"auto-refresh failed ({r.get('error')}); serving stale snapshot"], None


def _get_doc(args, source="core"):
    root = cache_root(args)
    slug = SOURCES[source]["slug"]
    prov, warns = snapshot_provenance(root, args.max_age_days, slug)
    prov, warns, err = _maybe_refresh(args, root, prov, warns, source)
    if err is not None:
        return None, None, warns, err
    try:
        doc = load_doc(root, slug)
    except FileNotFoundError:
        return None, None, warns, emit(
            envelope(args.cmd, error="data file missing — run: azadvertizer fetch"), 3)
    return doc, prov, warns, None


def cmd_get(args) -> int:
    name = args.dataset
    doc, prov, warns, err = _get_doc(args, DATASETS[name]["source"])
    if err is not None:
        return err
    if name == "api-permission":
        ids = find_permission_ids(doc, args.id)
        if not ids:
            return emit(envelope(args.cmd, provenance=prov, warnings=warns,
                                 error=f"no api-permission with id or value == {args.id!r}"), 1)
        rows = [row for pid in ids for row in api_permission_rows(doc, pid)]
        return emit(envelope(args.cmd, data=sanitize(rows), provenance=prov, warnings=warns), 0)
    eid = find_id(doc, name, args.id)
    if eid is None:
        return emit(envelope(args.cmd, provenance=prov, warnings=warns,
                             error=f"no {name} with id or name == {args.id!r}"), 1)
    data = initiative_full(doc, eid) if name == "initiative" else sanitize(
        ROW_BUILDERS[name](doc, eid))
    return emit(envelope(args.cmd, data=data, provenance=prov, warnings=warns), 0)


def cmd_search(args) -> int:
    name = args.dataset
    doc, prov, warns, err = _get_doc(args, DATASETS[name]["source"])
    if err is not None:
        return err
    preds = []
    for w in (args.where or []):
        if "=" not in w:
            return emit(envelope(args.cmd, error=f"--where must be COL=SUBSTR, got {w!r}"), 2)
        col, sub = w.split("=", 1)
        preds.append((col, sub.lower()))
    if args.name:
        preds.append((DATASETS[name]["name_col"], args.name.lower()))
    fields = args.fields.split(",") if args.fields else None
    out = []
    for row in iter_rows(doc, name):
        if all(sub in _text(row.get(col)).lower() for col, sub in preds):
            out.append(sanitize({k: row[k] for k in fields if k in row} if fields else row))
    total = len(out)
    # Pagination: results come from a local cache, so paging is a cheap slice. We return at
    # most --limit rows starting at --offset, and surface enough in provenance for the caller
    # to fetch the next page deterministically (matched/returned/offset/limit/has_more/next_offset).
    offset = max(0, args.offset or 0)
    limit = args.limit if args.limit and args.limit > 0 else None
    page = out[offset: offset + limit] if limit is not None else out[offset:]
    end = offset + len(page)
    prov2 = dict(prov)
    prov2["matched"] = total          # total hits across the whole snapshot
    prov2["returned"] = len(page)     # rows in this page
    prov2["offset"] = offset
    prov2["limit"] = limit
    prov2["has_more"] = end < total
    prov2["next_offset"] = end if end < total else None
    page_warns = list(warns)
    if prov2["has_more"]:
        page_warns.append(
            f"showing {len(page)} of {total} matches (offset {offset}); "
            f"pass --offset {end} for the next page, or raise --limit")
    code = 0 if total else 1
    return emit(envelope(args.cmd, data=page, provenance=prov2, warnings=page_warns), code)


def cmd_rel(args) -> int:
    rel = args.relation
    routing = {
        "policy-roles": ("policy", "policyRolesUsed"),
        "policy-initiatives": ("policy", "policyUsedInPolicySet"),
        "role-policies": ("role", "UsedInPolicy"),
    }
    if rel == "initiative-policies":
        args.dataset = "initiative"
        return cmd_get(args)
    name, col = routing[rel]
    doc, prov, warns, err = _get_doc(args)
    if err is not None:
        return err
    eid = find_id(doc, name, args.id)
    if eid is None:
        return emit(envelope("rel", provenance=prov, warnings=warns,
                             error=f"no {name} with id/name == {args.id!r}"), 1)
    row = ROW_BUILDERS[name](doc, eid)
    key = DATASETS[name]["key"]
    data = {
        "from": {key: eid, "name": row[DATASETS[name]["name_col"]]},
        "relation": rel,
        "items": sanitize(row[col]),
    }
    code = 0 if data["items"] else 1
    return emit(envelope("rel", data=data, provenance=prov, warnings=warns), code)


# ----------------------------- arg parsing -----------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="azadvertizer", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache-dir", help="override cache dir (default $XDG_CACHE_HOME/azadvertizer)")
    p.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS,
                   help=f"snapshot older than N days is stale; read commands auto-refresh it "
                        f"unless --offline (default {DEFAULT_MAX_AGE_DAYS})")
    p.add_argument("--offline", action="store_true",
                   help="never hit the network: serve the cached snapshot (flagged stale if old)")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="download + validate + cache the data file")
    f.add_argument("--only", help="fetch one source: core (policies, roles, initiatives) or "
                                  "index (Entra roles, API permissions, resource types)")
    f.add_argument("--force", action="store_true", help="re-download even if cached")
    f.add_argument("--refresh", action="store_true",
                   help="re-check if cached (conditional on the stored ETag)")
    f.set_defaults(func=cmd_fetch)

    s = sub.add_parser("status", help="show snapshot provenance + staleness")
    s.set_defaults(func=cmd_status)

    g = sub.add_parser("get", help="exact lookup by id or name")
    g.add_argument("dataset", choices=list(DATASETS))
    g.add_argument("id")
    g.add_argument("--split", action="store_true", help="no-op: lists are always arrays")
    g.set_defaults(func=cmd_get)

    se = sub.add_parser("search", help="substring filter (case-insensitive)")
    se.add_argument("dataset", choices=list(DATASETS))
    se.add_argument("--where", action="append", help="COL=SUBSTR (repeatable)")
    se.add_argument("--name", help="shorthand: match the dataset's name column")
    se.add_argument("--limit", type=int, default=50, help="max rows per page (default 50)")
    se.add_argument("--offset", type=int, default=0,
                    help="skip the first N matches (pagination; pair with --limit)")
    se.add_argument("--fields", help="comma list of columns to return")
    se.add_argument("--split", action="store_true", help="no-op: lists are always arrays")
    se.set_defaults(func=cmd_search)

    r = sub.add_parser("rel", help="resolve a cross-reference relationship")
    r.add_argument("relation", choices=["policy-roles", "policy-initiatives",
                                        "role-policies", "initiative-policies"])
    r.add_argument("id")
    r.add_argument("--split", action="store_true", help="no-op: lists are always arrays")
    r.set_defaults(func=cmd_rel)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "fetch" and args.offline:
        return emit(envelope("fetch", error="--offline set; refusing to fetch"), 2)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
