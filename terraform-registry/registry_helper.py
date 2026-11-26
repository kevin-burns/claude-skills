#!/usr/bin/env python3
"""terraform-registry — provider-agnostic CLI over the Terraform Registry API.

Targeted search/inspect against the Registry's JSON API (any provider: aws, google,
azurerm, gitlab, openstack, ...) — fetch the payload, strip it locally, return only
what was asked for. No web-page scraping, no full-text crawl.

Two data planes:
  * Modules        -> Registry v1 JSON API (search, inputs/outputs/versions).
  * Resource schema -> NOT in the registry API; comes from a cached
                       `terraform providers schema -json` dump (see `refresh-schema`).

Every command emits a JSON envelope with provenance and caches payloads on disk so
repeat calls are offline and token-free (the source-snapshot pattern).

Examples:
  registry_helper.py search vpc --provider aws --limit 5
  registry_helper.py inspect-module terraform-aws-modules/vpc/aws --fields inputs --filter name~cidr
  registry_helper.py inspect-module Azure/avm-res-keyvault-vault/azurerm
  registry_helper.py inspect-resource aws_s3_bucket --provider aws   # needs cached schema
  registry_helper.py refresh-schema --provider google

Exit codes: 0 ok | 1 not-found | 2 usage | 3 network/registry error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_HOST = "registry.terraform.io"
DEFAULT_CACHE = Path.home() / ".cache" / "terraform-registry"
EXIT_OK, EXIT_NOT_FOUND, EXIT_USAGE, EXIT_NET = 0, 1, 2, 3

# Convenience: resource-type prefix -> registry provider name. Not exhaustive; pass
# --provider to be explicit. Multi-cloud "trinity" plus a couple of common others.
PREFIX_PROVIDER = {
    "aws_": "aws", "google_": "google", "azurerm_": "azurerm",
    "azuread_": "azuread", "gitlab_": "gitlab", "openstack_": "openstack",
    "kubernetes_": "kubernetes", "helm_": "helm",
}


class RegistryError(Exception):
    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cache_key(path: str, params: dict, host: str = DEFAULT_HOST) -> str:
    """File name for a payload. A non-default host gets its own prefix, so a private
    registry is never answered from the public registry's entry for the same path; the
    default host keeps the bare name, so existing caches and fixtures stay valid."""
    slug = re.sub(r"[^A-Za-z0-9._-]", "-", path.strip("/").replace("/", "_"))
    if host != DEFAULT_HOST:
        slug = re.sub(r"[^A-Za-z0-9._-]", "-", host) + "__" + slug
    if params:
        q = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        slug += "__" + re.sub(r"[^A-Za-z0-9._=&-]", "-", q)
    return slug + ".json"


def _age_hours(retrieved_at: str | None) -> float | None:
    try:
        then = datetime.strptime(retrieved_at or "", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    return (datetime.now(UTC) - then).total_seconds() / 3600


def api_get(path: str, params: dict, *, host: str, cache_dir: Path,
            offline: bool, refresh: bool, max_age_h: float | None = None) -> tuple[dict, dict]:
    """Return (body, provenance). Reads/writes an on-disk snapshot cache.

    max_age_h=None marks an immutable path (a pinned module version): its cache never
    expires. A moving path (search, unversioned module = "latest") passes a TTL; past it
    the payload is re-fetched, except --offline, which serves it and reports its age.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / _cache_key(path, params, host)
    url = f"https://{host}/{path.lstrip('/')}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    stale_env = None
    if cache_file.exists() and not refresh:
        env = json.loads(cache_file.read_text())
        age = _age_hours(env.get("retrieved_at"))
        expired = max_age_h is not None and (age is None or age > max_age_h)
        if not expired or offline:
            prov = {"source_url": env.get("source_url", url), "source_kind": "registry_module_api",
                    "retrieved_at": env.get("retrieved_at"), "cached": True,
                    "age_hours": None if age is None else round(age, 1),
                    "moving": max_age_h is not None}
            return env["body"], prov
        stale_env = env

    if offline:
        raise RegistryError(f"offline: no cached payload for {url} ({cache_file.name})",
                            EXIT_NOT_FOUND)

    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "terraform-registry-cli"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RegistryError(f"registry returned HTTP {e.code} for {url}",
                            EXIT_NOT_FOUND if e.code == 404 else EXIT_NET) from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        hint = (f"; a cached copy from {stale_env.get('retrieved_at')} is past its TTL, "
                "pass --offline to use it anyway" if stale_env else "")
        raise RegistryError(f"failed to fetch {url}: {e}{hint}", EXIT_NET) from e

    retrieved = _now()
    cache_file.write_text(json.dumps({"source_url": url, "retrieved_at": retrieved,
                                      "body": body}, indent=2))
    return body, {"source_url": url, "source_kind": "registry_module_api",
                  "retrieved_at": retrieved, "cached": False, "age_hours": 0.0,
                  "moving": max_age_h is not None}


def _cache_warnings(prov: dict) -> list:
    """A moving path served from cache says how old it is: 'latest' may have moved on."""
    if prov.get("cached") and prov.get("moving"):
        age = prov.get("age_hours")
        return [f"cache age {'unknown' if age is None else f'{age:.1f}h'} "
                f"(retrieved {prov.get('retrieved_at')}): this is a moving path ('latest' or "
                "search), so the registry may have changed since; --refresh re-fetches"]
    return []


def emit(command: str, data, provenance: dict | None, warnings: list, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps({"ok": True, "command": command, "data": data,
                          "provenance": provenance, "warnings": warnings, "error": None},
                         indent=2))
    else:
        print(_render_text(command, data, provenance, warnings))


def fail(command: str, err: RegistryError, fmt: str) -> int:
    if fmt == "json":
        print(json.dumps({"ok": False, "command": command, "data": None,
                          "provenance": None, "warnings": [],
                          "error": {"message": str(err), "code": err.code}}, indent=2))
    else:
        print(f"error: {err}", file=sys.stderr)
    return err.code


# ---------- commands ----------

def cmd_search(args) -> int:
    params = {"q": args.query, "limit": str(args.limit)}
    if args.provider:
        params["provider"] = args.provider
    if args.namespace:
        params["namespace"] = args.namespace
    try:
        body, prov = api_get("v1/modules/search", params, host=args.host,
                             cache_dir=Path(args.cache_dir), offline=args.offline,
                             refresh=args.refresh, max_age_h=args.max_age_hours)
    except RegistryError as e:
        return fail("search", e, args.format)
    mods = [{
        "id": m.get("id"), "namespace": m.get("namespace"), "name": m.get("name"),
        "provider": m.get("provider"), "version": m.get("version"),
        "description": m.get("description"), "downloads": m.get("downloads"),
        "verified": m.get("verified"), "source": m.get("source"),
    } for m in body.get("modules", [])]
    emit("search", {"query": args.query, "provider": args.provider,
                    "count": len(mods), "modules": mods}, prov, _cache_warnings(prov),
         args.format)
    return EXIT_OK


def _resolve_module(target: str) -> tuple[str, dict]:
    """Accept 'ns/name/provider[/version][//sub/dir]' (Terraform's own // submodule syntax).

    Returns (api path, info). info["submodule"] is the path after //, if any; a version of
    'latest' is dropped (the registry 404s on .../latest) and noted in info["latest"].
    """
    mod, _, sub = target.strip("/").partition("//")
    parts = mod.strip("/").split("/")
    info_extra = {"submodule": sub.strip("/") or None, "latest": False}
    if len(parts) == 4 and parts[3].lower() == "latest":
        parts, info_extra["latest"] = parts[:3], True
    if len(parts) == 3:
        ns, name, provider = parts
        return (f"v1/modules/{ns}/{name}/{provider}",
                {"namespace": ns, "name": name, "provider": provider, **info_extra})
    if len(parts) == 4:
        ns, name, provider, ver = parts
        return (f"v1/modules/{ns}/{name}/{provider}/{ver}",
                {"namespace": ns, "name": name, "provider": provider, "version": ver, **info_extra})
    raise RegistryError(
        f"module target must be 'namespace/name/provider[/version][//modules/x]', got '{target}'",
        EXIT_USAGE)


def _apply_filter(items: list, flt: str | None) -> list:
    if not flt:
        return items
    m = re.match(r"\s*name\s*~\s*(.+)$", flt)
    needle = (m.group(1) if m else flt).strip().lower()
    return [i for i in items if needle in (i.get("name", "") or "").lower()]


def cmd_inspect_module(args) -> int:
    try:
        path, info = _resolve_module(args.target)
        body, prov = api_get(path, {}, host=args.host, cache_dir=Path(args.cache_dir),
                             offline=args.offline, refresh=args.refresh,
                             max_age_h=None if info.get("version") else args.max_age_hours)
    except RegistryError as e:
        return fail("inspect-module", e, args.format)

    warnings = _cache_warnings(prov)
    if info["latest"]:
        warnings.insert(0, "'latest' is not a registry version (the API 404s on it); "
                           "used the unversioned path, which returns the newest release")
    if body.get("deprecation"):
        warnings.append(f"module is deprecated: {json.dumps(body['deprecation'])}")
    sub_paths = [m.get("path") for m in body.get("submodules", []) or []]
    root = body.get("root", {}) or {}
    if info["submodule"]:
        root = next((m for m in body.get("submodules", []) or []
                     if (m.get("path") or "").strip("/") == info["submodule"]), None)
        if root is None:
            return fail("inspect-module", RegistryError(
                f"no submodule '{info['submodule']}' in {path}; available: "
                + (", ".join(sub_paths) or "none"), EXIT_NOT_FOUND), args.format)
    inputs = [{"name": i.get("name"), "type": i.get("type"), "required": i.get("required"),
               "default": i.get("default"), "description": i.get("description")}
              for i in root.get("inputs", [])]
    outputs = [{"name": o.get("name"), "description": o.get("description")}
               for o in root.get("outputs", [])]
    inputs = _apply_filter(inputs, args.filter)
    outputs = _apply_filter(outputs, args.filter)

    full = {
        "id": body.get("id"), "source": body.get("source"),
        "namespace": info["namespace"], "name": info["name"], "provider": info["provider"],
        "version": body.get("version") or info.get("version"),
        "description": body.get("description"),
        "inputs": inputs, "outputs": outputs,
        "versions": body.get("versions", []),
        "submodule": info["submodule"],
        "submodules": sub_paths,
        "counts": {"inputs": len(inputs), "outputs": len(outputs)},
    }
    if args.fields:
        wanted = {f.strip() for f in args.fields.split(",")}
        meta_keys = {"id", "source", "namespace", "name", "provider", "version", "description",
                     "submodule", "submodules"}
        data = {k: v for k, v in full.items()
                if k in wanted or (k in meta_keys and "meta" in wanted)}
        data.setdefault("namespace", info["namespace"])
        data.setdefault("name", info["name"])
        data.setdefault("provider", info["provider"])
    else:
        data = full
    emit("inspect-module", data, prov, warnings, args.format)
    return EXIT_OK


def cmd_inspect_resource(args) -> int:
    provider = args.provider or next(
        (p for pre, p in PREFIX_PROVIDER.items() if args.resource.startswith(pre)), None)
    if not provider:
        return fail("inspect-resource",
                    RegistryError(f"cannot infer provider from '{args.resource}'; pass --provider",
                                  EXIT_USAGE), args.format)
    schema_file = Path(args.cache_dir) / "schemas" / f"{provider}.json"
    if not schema_file.exists():
        return fail("inspect-resource", RegistryError(
            f"no cached schema for provider '{provider}'. Run: "
            f"registry_helper.py refresh-schema --provider {provider}", EXIT_NOT_FOUND),
            args.format)
    schema = json.loads(schema_file.read_text())
    res = (schema.get("resources", {}) or {}).get(args.resource)
    if res is None:
        return fail("inspect-resource",
                    RegistryError(f"resource '{args.resource}' not in cached {provider} schema",
                                  EXIT_NOT_FOUND), args.format)
    attrs = [{"name": k, "type": v.get("type"), "required": bool(v.get("required")),
              "optional": bool(v.get("optional")), "computed": bool(v.get("computed"))}
             for k, v in sorted((res.get("attributes", {}) or {}).items())]
    attrs = _apply_filter(attrs, args.filter)
    prov = {"source_url": str(schema_file), "source_kind": "terraform_provider_schema",
            "retrieved_at": schema.get("_retrieved_at"), "cached": True}
    emit("inspect-resource", {"resource": args.resource, "provider": provider,
                              "attributes": attrs, "count": len(attrs)}, prov, [], args.format)
    return EXIT_OK


def cmd_refresh_schema(args) -> int:
    """Dump and cache a provider's resource schema via the terraform CLI."""
    import subprocess
    import tempfile

    provider = args.provider
    ns = args.namespace
    cache_dir = Path(args.cache_dir) / "schemas"
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{provider}.json"

    with tempfile.TemporaryDirectory() as td:
        Path(td, "main.tf").write_text(
            f'terraform {{\n  required_providers {{\n    {provider} = {{\n'
            f'      source = "{ns}/{provider}"\n    }}\n  }}\n}}\n')
        try:
            subprocess.run(["terraform", "init", "-input=false", "-no-color"],
                           cwd=td, check=True, capture_output=True, text=True)
            res = subprocess.run(["terraform", "providers", "schema", "-json"],
                                 cwd=td, check=True, capture_output=True, text=True)
        except FileNotFoundError:
            return fail("refresh-schema",
                        RegistryError("terraform CLI not found on PATH", EXIT_NET), args.format)
        except subprocess.CalledProcessError as e:
            return fail("refresh-schema",
                        RegistryError(f"terraform failed: {e.stderr.strip()[:300]}", EXIT_NET),
                        args.format)

    raw = json.loads(res.stdout)
    # flatten to {resources, data_sources} for the matching provider source key
    prov_schemas = raw.get("provider_schemas", {})
    key = next((k for k in prov_schemas if k.endswith(f"/{provider}")), None)
    ps = prov_schemas.get(key, {}) if key else {}
    flat = {
        "_provider": provider, "_source": key, "_retrieved_at": _now(),
        "resources": {k: v.get("block", {}) for k, v in ps.get("resource_schemas", {}).items()},
        "data_sources": {k: v.get("block", {}) for k, v in ps.get("data_source_schemas", {}).items()},
    }
    out.write_text(json.dumps(flat, indent=2))
    emit("refresh-schema",
         {"provider": provider, "resources": len(flat["resources"]),
          "data_sources": len(flat["data_sources"]), "path": str(out)},
         {"source_url": key, "source_kind": "terraform_provider_schema",
          "retrieved_at": flat["_retrieved_at"], "cached": False}, [], args.format)
    return EXIT_OK


def _render_text(command, data, provenance, warnings) -> str:
    lines = []
    if command == "search":
        lines.append(f"{data['count']} module(s) for '{data['query']}'"
                     + (f" [provider={data['provider']}]" if data.get("provider") else ""))
        for m in data["modules"]:
            lines.append(f"  {m['id']}  v{m['version']}  ↓{m.get('downloads', '?')}"
                         + ("  ✓verified" if m.get("verified") else ""))
            if m.get("description"):
                lines.append(f"      {m['description']}")
    elif command == "inspect-module":
        hdr = f"{data.get('namespace')}/{data.get('name')}/{data.get('provider')}"
        if data.get("version"):
            hdr += f"  v{data['version']}"
        if data.get("submodule"):
            hdr += f"  //{data['submodule']}"
        lines.append(hdr)
        for i in data.get("inputs", []):
            req = "required" if i.get("required") else "optional"
            lines.append(f"  in  {i['name']}: {i.get('type')} [{req}]")
        for o in data.get("outputs", []):
            lines.append(f"  out {o['name']}")
    elif command == "inspect-resource":
        lines.append(f"{data['resource']} ({data['provider']}): {data['count']} attribute(s)")
        for a in data["attributes"]:
            flags = ",".join(f for f in ("required", "optional", "computed") if a.get(f))
            lines.append(f"  {a['name']}: {a.get('type')} [{flags}]")
    elif command == "refresh-schema":
        lines.append(f"{data['provider']}: {data['resources']} resources, "
                     f"{data['data_sources']} data sources -> {data['path']}")
    if provenance:
        lines.append(f"  ({'cache' if provenance.get('cached') else 'live'}: "
                     f"{provenance.get('source_url')})")
    lines.extend(f"  warning: {w}" for w in warnings)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Provider-agnostic Terraform Registry CLI")
    p.add_argument("--host", default=DEFAULT_HOST, help="registry host (for private registries)")
    p.add_argument("--cache-dir", default=str(DEFAULT_CACHE), help="snapshot cache directory")
    p.add_argument("--offline", action="store_true", help="use cache only; never hit the network")
    p.add_argument("--refresh", action="store_true", help="bypass cache and re-fetch")
    p.add_argument("--max-age-hours", type=float, default=24.0,
                   help="TTL for moving paths (search, unversioned module); pinned versions never expire")
    p.add_argument("--format", choices=["text", "json"], default="text")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="search modules (any provider)")
    s.add_argument("query")
    s.add_argument("--provider", help="filter by provider, e.g. aws/google/azurerm")
    s.add_argument("--namespace", help="filter by namespace")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_search)

    im = sub.add_parser("inspect-module", help="inspect a module's inputs/outputs/versions")
    im.add_argument("target", help="namespace/name/provider[/version][//modules/x]")
    im.add_argument("--fields", help="comma list: inputs,outputs,versions,meta")
    im.add_argument("--filter", help="filter inputs/outputs by name, e.g. name~cidr")
    im.set_defaults(func=cmd_inspect_module)

    ir = sub.add_parser("inspect-resource", help="inspect a resource's attributes (cached schema)")
    ir.add_argument("resource", help="resource type, e.g. aws_s3_bucket")
    ir.add_argument("--provider", help="provider name (inferred from prefix if omitted)")
    ir.add_argument("--filter", help="filter attributes by name")
    ir.set_defaults(func=cmd_inspect_resource)

    rs = sub.add_parser("refresh-schema", help="cache a provider schema via the terraform CLI")
    rs.add_argument("--provider", default="aws")
    rs.add_argument("--namespace", default="hashicorp", help="provider namespace, e.g. hashicorp")
    rs.set_defaults(func=cmd_refresh_schema)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
