---
name: terraform-registry
description: Provider-agnostic CLI for targeted search and inspection of the Terraform Registry via its JSON API — any provider (AWS, GCP/google, Azure/azurerm, GitLab, OpenStack, Kubernetes, ...). Use to find modules by keyword, inspect a module's inputs/outputs/versions, or look up a resource type's attributes, WITHOUT web-scraping or dumping pages into context — it fetches the JSON payload, strips it locally, and returns only what you asked for. Caches every payload as a provenance-stamped snapshot so repeat calls are offline and token-free. Use whenever you need accurate, current Terraform module/provider facts for writing or reviewing IaC.
license: MIT
---

# terraform-registry

A self-contained CLI (`registry_helper.py`, stdlib-only) that queries the Terraform
Registry's JSON API directly. It exists so an agent can get **accurate, current**
module/provider facts deterministically — fetch the structured payload, filter to the
slice you need, return that. No HTML, no full-text crawl, no page-dump into context.

Run it with `uv run python registry_helper.py <command>` (or `python3` — it needs only
the standard library).

## Two data planes (important)

| You want | Source | Command |
|---|---|---|
| Find a module / its inputs, outputs, versions | Registry **v1 JSON API** (provider-agnostic) | `search`, `inspect-module` |
| A resource type's attributes (e.g. `aws_s3_bucket`) | **`terraform providers schema -json`** dump (the registry API does **not** serve schemas) | `refresh-schema`, then `inspect-resource` |

The module side works for any provider with no special-casing — the provider is just a
path/query parameter. The resource-schema side needs the `terraform` CLI once to cache a
provider's schema; after that, lookups are offline.

## Commands

```bash
# Search modules (any provider). --provider/--namespace narrow it; --limit caps results.
registry_helper.py search vpc --provider aws --limit 5
registry_helper.py search network --provider google
registry_helper.py search keyvault --provider azurerm

# Inspect a module: namespace/name/provider[/version]. Project + filter to stay small.
registry_helper.py inspect-module terraform-aws-modules/vpc/aws --fields inputs --filter name~cidr
registry_helper.py inspect-module Azure/avm-res-keyvault-vault/azurerm --fields meta,outputs

# Resource attributes (needs a cached schema first):
registry_helper.py refresh-schema --provider google --namespace hashicorp
registry_helper.py inspect-resource google_storage_bucket --filter name~location
```

### Token-efficiency levers
- `--fields inputs,outputs,versions,meta` — return only the sections you need.
- `--filter name~<substr>` — keep only inputs/outputs/attributes whose name matches.
- These run **locally on the fetched payload**, so you pay tokens only for the slice.

## Determinism & caching (the source-snapshot pattern)

Every fetch is written to an on-disk snapshot cache (`--cache-dir`, default
`~/.cache/terraform-registry`) and re-read on the next call.

- `--offline` — use the cache only; never touch the network. Errors if a payload isn't cached.
- `--refresh` — bypass the cache and re-fetch (then re-cache).
- Pin behavior by inspecting a specific version (`.../aws/5.8.1`) and committing the cached
  payload — that snapshot becomes a stable, citable fact. See the `source-snapshot` skill.

## Output contract

`--format json` (for agents) emits a stable envelope:

```json
{ "ok": true, "command": "...", "data": {...},
  "provenance": { "source_url": "...", "source_kind": "registry_module_api|terraform_provider_schema",
                  "retrieved_at": "...", "cached": true },
  "warnings": [], "error": null }
```

`--format text` (default) is human-readable. Exit codes: `0` ok · `1` not-found · `2`
usage · `3` network/registry error. On error with `--format json`, `ok` is `false` and
`error` carries `{message, code}`.

## How it fits the fleet

- A concrete **producer** for the `source-snapshot` skill (its cached payloads are the
  snapshots).
- A **tier-1/2 source** for the `fact-verifier` agent: it can cite a module input or a
  resource attribute from a cached payload — deterministically and offline — instead of
  guessing or scraping.
- Keep project-specific logic (catalog audit, scaffolding, org conventions) in your
  project repo and have it call this generic client.

## Scope

This is the generic registry client only. It does not edit code, write Terraform, or
apply anything — it reads the registry and returns facts. Tests: `evals/` (offline,
deterministic, multi-provider) — `cd evals && uv run python grade.py`.
