#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""azadvertizer — deterministic, offline-first lookups over AzAdvertizer's CSV exports.

AzAdvertizer (https://www.azadvertizer.net, by Julian Hayward) publishes gzip-served CSV
exports of Azure Policy, Policy Initiative, and RBAC Role metadata — enriched with
cross-references (which roles a policy uses, which initiatives include a policy, which
policies a role is used by) that exist nowhere else in one place. There is no API.

This helper fetches each CSV ONCE into a provenance-stamped local cache (gzip on the wire,
decompressed at rest), validates the header against a pinned schema, and answers lookups
offline. Stdlib only — no third-party dependencies. Output is a JSON envelope.

Design notes (decided by a design-council review of the mechanics):
- The dataset is tiny (~22k rows total); a linear scan with csv.DictReader is the whole
  job. No pandas/polars/DuckDB. sqlite3 is the documented escalation IF cross-file
  relational queries ever become a real requirement — not before.
- The risk is reliability, not speed: an undocumented upstream that can change columns
  without notice. So ingest is atomic, header-validated, and a stale snapshot is surfaced
  loudly in the envelope (never silently served as fresh).
- List-valued cells use DIFFERENT delimiters per file (verified against real rows):
  policy file -> "; " ; role file -> ", " ; cloudEnvs -> ";". See DATASETS below.

Usage:
  azadvertizer fetch [--only policy,role,initiative] [--force] [--cache-dir DIR]
  azadvertizer status [--cache-dir DIR]
  azadvertizer get <policy|role|initiative> <id> [--split] [--cache-dir DIR]
  azadvertizer search <policy|role|initiative> [--where COL=SUBSTR]... [--name S]
                      [--limit N] [--offset N] [--fields a,b,c] [--split] [--cache-dir DIR]
  azadvertizer rel <policy-roles|policy-initiatives|role-policies|initiative-policies> <id>
                   [--cache-dir DIR]

Global: --max-age-days N (treat snapshot older than N as an error), --offline (never fetch).
Exit codes: 0 ok · 1 not-found/empty · 2 usage · 3 cache-missing · 4 fetch/schema error.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

csv.field_size_limit(10_000_000)

BASE = "https://www.azadvertizer.net"
USER_AGENT = "azadvertizer-skill/1.0 (+https://github.com/kevin-burns/claude-skills)"
# Default freshness window. Azure governance metadata changes slowly, so a weekly refresh
# keeps facts current without hammering AzAdvertizer. Read commands auto-refresh a snapshot
# older than this (unless --offline). Tune with --max-age-days; disable refresh with --offline.
DEFAULT_MAX_AGE_DAYS = 7

# ---- Field map / schema (the documented "tribal knowledge", verified against real rows) --
# delim modes: "token" = plain values; "nameid" = "Name (id)"; "nameid_src" = "Name (id) Source"
DATASETS: dict[str, dict] = {
    "policy": {
        "slug": "azpolicyadvertizer-comma",
        "key": "policyId",
        "name_col": "policyName",
        "row_floor": 2000,
        "grain": "entity",  # one row per policyId
        "header": (
            "policyName", "policyDescription", "policyId", "policyVersion",
            "policyCategory", "policyMode", "policyType", "policyPreview",
            "policyDeprecated", "policyEffect", "policyEffectAllowedValues",
            "policyRolesUsedCount", "policyRolesUsed", "policyUsedInPolicySetCount",
            "policyUsedInPolicySet", "dateAdded", "cloudEnvs", "azUSGovVersion",
        ),
        "list_cols": {
            "policyEffectAllowedValues": ("; ", "token"),
            "policyRolesUsed": ("; ", "nameid"),
            "policyUsedInPolicySet": ("; ", "nameid_src"),
            "cloudEnvs": (";", "token"),
        },
    },
    "role": {
        "slug": "azrolesadvertizer-comma",
        "key": "RoleId",
        "name_col": "RoleName",
        "row_floor": 400,
        "grain": "entity",  # one row per RoleId
        "header": (
            "RoleId", "RoleName", "RoleDescription", "RoleActions", "RoleNotActions",
            "RoleDataActions", "RoleNotDataActions", "UsedInPolicyCount", "UsedInPolicy",
        ),
        # Role file uses ", " for EVERY list column. UsedInPolicy holds "Name (id)" where
        # the name may itself contain ", ", so its split is anchored on the trailing ")".
        "list_cols": {
            "RoleActions": (", ", "token"),
            "RoleNotActions": (", ", "token"),
            "RoleDataActions": (", ", "token"),
            "RoleNotDataActions": (", ", "token"),
            "UsedInPolicy": (", ", "nameid"),
        },
    },
    "initiative": {
        "slug": "azpolicyinitiativesadvertizer-comma",
        "key": "initiativeId",
        "name_col": "initiativeName",
        "row_floor": 5000,
        "grain": "fact",  # DENORMALIZED: many rows per initiativeId (one per member policy)
        "header": (
            "initiativeId", "initiativeName", "initiativeDescription", "initiativeCategory",
            "initiativeVersion", "initiativeType", "initiativeCloudEnvs", "initiativeAzUSGov",
            "initiativeVersionAzUSGov", "initiativePolicyReferenceId", "initiativePolicyId",
            "initiativePolicyName", "initiativePolicyDescription", "initiativePolicyCategory",
            "initiativePolicyVersion", "initiativePolicyMode", "initiativePolicyType",
            "initiativePolicyCloudEnvs", "initiativePolicyAzUSGov",
            "initiativePolicyVersionAzUSGov", "initiativePolicyPreview",
            "initiativePolicyDeprecated", "initiativePolicyEffectDefault",
            "initiativePolicyEffectAllowed", "initiativePolicyEffectFixed",
        ),
        "list_cols": {
            "initiativeCloudEnvs": (";", "token"),
            "initiativePolicyEffectAllowed": ("; ", "token"),
        },
        # Columns describing the initiative itself (repeat on every member row).
        "initiative_cols": (
            "initiativeId", "initiativeName", "initiativeDescription", "initiativeCategory",
            "initiativeVersion", "initiativeType", "initiativeCloudEnvs", "initiativeAzUSGov",
            "initiativeVersionAzUSGov",
        ),
    },
}

NAMEID_RE = re.compile(r"^(?P<name>.*?)\s*\((?P<id>[^()]*)\)(?:\s+(?P<src>\S+))?\s*$")


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


def csv_path(root: Path, name: str) -> Path:
    return root / f"{DATASETS[name]['slug']}.csv"


def meta_path(root: Path, name: str) -> Path:
    return root / f"{DATASETS[name]['slug']}.meta.json"


# ----------------------------- fetch / ingest -----------------------------
def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=90) as resp:  # noqa: S310 (https only, fixed host)
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw


def fetch_one(root: Path, name: str, force: bool) -> dict:
    spec = DATASETS[name]
    url = f"{BASE}/{spec['slug']}.csv"
    warnings = []
    try:
        raw = _download(url)
    except Exception as exc:  # network/HTTP — keep any existing snapshot
        return {"name": name, "ok": False, "error": f"download failed: {exc}",
                "kept_existing": csv_path(root, name).exists()}

    text = raw.decode("utf-8-sig")
    reader = csv.reader(text.splitlines())
    try:
        header = tuple(next(reader))
    except StopIteration:
        return {"name": name, "ok": False, "error": "empty download",
                "kept_existing": csv_path(root, name).exists()}

    # --- schema validation: refuse to overwrite a good cache with a drifted file ---
    if header != spec["header"]:
        return {"name": name, "ok": False,
                "error": "schema drift: header does not match pinned schema",
                "expected": list(spec["header"]), "got": list(header),
                "kept_existing": csv_path(root, name).exists()}

    rows = sum(1 for _ in reader)
    if rows < spec["row_floor"]:
        return {"name": name, "ok": False,
                "error": f"row floor: got {rows} rows, expected >= {spec['row_floor']} "
                         f"(possible truncated download)",
                "kept_existing": csv_path(root, name).exists()}

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    root.mkdir(parents=True, exist_ok=True)
    # --- atomic write: temp -> fsync -> replace ---
    tmp = csv_path(root, name).with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, csv_path(root, name))
    meta = {
        "dataset": name, "source_url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha, "rows": rows, "cols": len(header),
        "attribution": "Data from AzAdvertizer (Julian Hayward), https://www.azadvertizer.net",
    }
    meta_path(root, name).write_text(json.dumps(meta, indent=2))
    return {"name": name, "ok": True, "rows": rows, "warnings": warnings}


# ----------------------------- load + provenance -----------------------------
def load_meta(root: Path, name: str) -> dict | None:
    mp = meta_path(root, name)
    if not mp.exists():
        return None
    return json.loads(mp.read_text())


def snapshot_provenance(root: Path, name: str, max_age_days: int | None):
    meta = load_meta(root, name)
    if not meta:
        return None, ["no snapshot cached — run: azadvertizer fetch"]
    prov = dict(meta)
    warns = []
    try:
        fetched = datetime.fromisoformat(meta["fetched_at"])
        age = (datetime.now(timezone.utc) - fetched).total_seconds() / 86400
        prov["snapshot_age_days"] = round(age, 2)
        prov["stale"] = bool(max_age_days is not None and age > max_age_days)
        if prov["stale"]:
            warns.append(f"snapshot is {age:.1f}d old (> --max-age-days {max_age_days}); "
                         f"re-run: azadvertizer fetch")
    except (KeyError, ValueError):
        prov["snapshot_age_days"] = None
        prov["stale"] = None
    return prov, warns


def load_rows(root: Path, name: str) -> list[dict]:
    cp = csv_path(root, name)
    if not cp.exists():
        raise FileNotFoundError(name)
    with open(cp, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ----------------------------- list splitting + sanitization -----------------------------
def split_cell(name: str, col: str, value: str):
    """Split a list-valued cell using the per-column delimiter/mode from DATASETS."""
    spec = DATASETS[name].get("list_cols", {})
    if col not in spec or value is None:
        return value
    delim, mode = spec[col]
    v = value.strip()
    if v == "" or v.lower() == "empty":
        return []
    # Anchor name/id splits on the closing ")" so names containing the delimiter don't
    # over-split (verified necessary for role UsedInPolicy).
    if mode in ("nameid", "nameid_src"):
        parts = re.split(r"(?<=\))" + re.escape(delim.rstrip()), v)
        out = []
        for p in parts:
            p = p.strip().rstrip(delim.strip()).strip()
            if not p:
                continue
            m = NAMEID_RE.match(p)
            if m:
                item = {"name": m.group("name").strip(), "id": m.group("id").strip()}
                if mode == "nameid_src" and m.group("src"):
                    item["source"] = m.group("src").strip()
                out.append(item)
            else:
                out.append({"name": p, "id": None})
        return out
    return [s.strip() for s in v.split(delim) if s.strip()]


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


def project(name: str, row: dict, fields: list[str] | None, do_split: bool) -> dict:
    cols = fields if fields else list(row.keys())
    out = {}
    for c in cols:
        if c not in row:
            continue
        out[c] = split_cell(name, c, row[c]) if do_split else row[c]
    return {k: sanitize(v) for k, v in out.items()}


# ----------------------------- commands -----------------------------
def cmd_fetch(args) -> int:
    root = cache_root(args)
    names = args.only.split(",") if args.only else list(DATASETS)
    results, any_err = [], False
    for n in names:
        n = n.strip()
        if n not in DATASETS:
            return emit(envelope("fetch", error=f"unknown dataset: {n}"), 2)
        if not args.force and csv_path(root, n).exists() and not args.refresh:
            results.append({"name": n, "ok": True, "skipped": "already cached (use --force)"})
            continue
        r = fetch_one(root, n, args.force)
        any_err = any_err or not r["ok"]
        results.append(r)
    env = envelope("fetch", data={"cache_dir": str(root), "results": results})
    if any_err:
        env["ok"] = False
        env["error"] = "one or more datasets failed schema/row/download validation"
        return emit(env, 4)
    return emit(env, 0)


def cmd_status(args) -> int:
    root = cache_root(args)
    out = {}
    for n in DATASETS:
        prov, warns = snapshot_provenance(root, n, args.max_age_days)
        out[n] = {"cached": prov is not None, "provenance": prov, "warnings": warns}
    return emit(envelope("status", data={"cache_dir": str(root), "datasets": out}), 0)


def _maybe_refresh(args, root, name, prov, warns):
    """Auto-refresh a missing or stale dataset unless --offline.

    Default freshness is one week (--max-age-days). Within that window nothing refreshes, so
    repeated calls in a session stay deterministic; past it, the next read pulls a fresh
    snapshot. --offline disables refresh entirely (serves the cached snapshot, flagged stale).
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
    r = fetch_one(root, name, force=True)
    if r["ok"]:
        prov2, w2 = snapshot_provenance(root, name, args.max_age_days)
        reason = "missing" if missing else f"older than {args.max_age_days}d"
        return prov2, w2 + [f"auto-refreshed ({reason})"], None
    if missing:
        return prov, warns, emit(envelope(
            args.cmd, warnings=warns,
            error=f"cache missing and refresh failed: {r.get('error')}"), 4)
    return prov, warns + [f"auto-refresh failed ({r.get('error')}); serving stale snapshot"], None


def _get_rows(args, name):
    root = cache_root(args)
    prov, warns = snapshot_provenance(root, name, args.max_age_days)
    prov, warns, err = _maybe_refresh(args, root, name, prov, warns)
    if err is not None:
        return None, None, warns, err
    try:
        rows = load_rows(root, name)
    except FileNotFoundError:
        return None, None, warns, emit(
            envelope(args.cmd, error=f"{name} csv missing — run: azadvertizer fetch"), 3)
    return rows, prov, warns, None


def cmd_get(args) -> int:
    name = args.dataset
    rows, prov, warns, err = _get_rows(args, name)
    if err is not None:
        return err
    key = DATASETS[name]["key"]
    matches = [r for r in rows if r.get(key) == args.id or
               r.get(DATASETS[name]["name_col"]) == args.id]
    if not matches:
        return emit(envelope(args.cmd, provenance=prov, warnings=warns,
                             error=f"no {name} with {key} or name == {args.id!r}"), 1)
    if name == "initiative":
        data = _assemble_initiative(matches)
    else:
        data = project(name, matches[0], None, args.split)
    return emit(envelope(args.cmd, data=data, provenance=prov, warnings=warns), 0)


def _assemble_initiative(member_rows: list[dict]) -> dict:
    first = member_rows[0]
    meta = {c: first.get(c) for c in DATASETS["initiative"]["initiative_cols"]}
    meta = {k: sanitize(v) for k, v in meta.items()}
    members = []
    for r in member_rows:
        member = {
            "policyReferenceId": r.get("initiativePolicyReferenceId"),
            "policyId": r.get("initiativePolicyId"),
            "policyName": r.get("initiativePolicyName"),
            "policyCategory": r.get("initiativePolicyCategory"),
            "effectDefault": r.get("initiativePolicyEffectDefault"),
            "effectAllowed": split_cell("initiative", "initiativePolicyEffectAllowed",
                                        r.get("initiativePolicyEffectAllowed", "")),
            "effectFixed": r.get("initiativePolicyEffectFixed"),
        }
        members.append({k: sanitize(v) for k, v in member.items()})
    meta["policyCount"] = len(members)
    meta["policies"] = members
    return meta


def cmd_search(args) -> int:
    name = args.dataset
    rows, prov, warns, err = _get_rows(args, name)
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

    def hit(r):
        for col, sub in preds:
            if sub not in (r.get(col, "") or "").lower():
                return False
        return True

    fields = args.fields.split(",") if args.fields else None
    if name == "initiative":
        # search over distinct initiatives (match on any member row), return initiative meta
        seen, out = set(), []
        for r in rows:
            iid = r.get("initiativeId")
            if iid in seen or not hit(r):
                continue
            seen.add(iid)
            meta = {c: sanitize(r.get(c)) for c in DATASETS["initiative"]["initiative_cols"]}
            out.append({k: meta[k] for k in (fields or meta)} if fields else meta)
    else:
        out = [project(name, r, fields, args.split) for r in rows if hit(r)]
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
        # reuse the grouped initiative assembly
        args.dataset = "initiative"
        return cmd_get(args)
    if rel not in routing:
        return emit(envelope("rel", error=f"unknown relation: {rel}"), 2)
    name, col = routing[rel]
    rows, prov, warns, err = _get_rows(args, name)
    if err is not None:
        return err
    key = DATASETS[name]["key"]
    match = next((r for r in rows if r.get(key) == args.id or
                  r.get(DATASETS[name]["name_col"]) == args.id), None)
    if match is None:
        return emit(envelope("rel", provenance=prov, warnings=warns,
                             error=f"no {name} with id/name == {args.id!r}"), 1)
    data = {
        "from": {key: match.get(key), "name": match.get(DATASETS[name]["name_col"])},
        "relation": rel,
        "items": sanitize(split_cell(name, col, match.get(col, ""))),
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

    f = sub.add_parser("fetch", help="download + validate + cache the CSVs")
    f.add_argument("--only", help="comma list of datasets (policy,role,initiative)")
    f.add_argument("--force", action="store_true", help="re-download even if cached")
    f.add_argument("--refresh", action="store_true", help="alias for re-download if cached")
    f.set_defaults(func=cmd_fetch)

    s = sub.add_parser("status", help="show snapshot provenance + staleness")
    s.set_defaults(func=cmd_status)

    g = sub.add_parser("get", help="exact lookup by id or name")
    g.add_argument("dataset", choices=list(DATASETS))
    g.add_argument("id")
    g.add_argument("--split", action="store_true", help="split list-valued cells")
    g.set_defaults(func=cmd_get)

    se = sub.add_parser("search", help="substring filter (case-insensitive)")
    se.add_argument("dataset", choices=list(DATASETS))
    se.add_argument("--where", action="append", help="COL=SUBSTR (repeatable)")
    se.add_argument("--name", help="shorthand: match the dataset's name column")
    se.add_argument("--limit", type=int, default=50, help="max rows per page (default 50)")
    se.add_argument("--offset", type=int, default=0,
                    help="skip the first N matches (pagination; pair with --limit)")
    se.add_argument("--fields", help="comma list of columns to return")
    se.add_argument("--split", action="store_true", help="split list-valued cells")
    se.set_defaults(func=cmd_search)

    r = sub.add_parser("rel", help="resolve a cross-reference relationship")
    r.add_argument("relation", choices=["policy-roles", "policy-initiatives",
                                        "role-policies", "initiative-policies"])
    r.add_argument("id")
    r.add_argument("--split", action="store_true", help="(initiative-policies only)")
    r.set_defaults(func=cmd_rel)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "fetch" and args.offline:
        return emit(envelope("fetch", error="--offline set; refusing to fetch"), 2)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
