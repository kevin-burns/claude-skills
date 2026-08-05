# terraform-registry

Get accurate, current Terraform module and provider facts from the registry's JSON API —
without scraping HTML or dumping pages into context.

Part of [claude-skills](../README.md).

## What it does

`registry_helper.py` (stdlib-only) fetches the structured payload, filters it locally, and
returns only the slice you asked for. Provider-agnostic: AWS, `google`, `azurerm`,
GitLab, OpenStack, Kubernetes and the rest are just a path or query parameter.

```bash
tfreg search vpc --provider aws --limit 5
tfreg inspect-module terraform-aws-modules/vpc/aws --fields inputs --filter name~cidr
tfreg inspect-resource google_storage_bucket --filter name~location
```

`--fields` and `--filter` run on the *already-fetched* payload, so you pay tokens only for
the part you keep. That is the point of the skill: a module's full input list can be
hundreds of entries, and you usually want four of them.

Every fetch is cached as a provenance-stamped snapshot (`~/.cache/terraform-registry` by
default), so repeat calls are offline and token-free. `--offline` refuses to touch the
network at all; `--refresh` bypasses the cache.

### Two data planes, and the difference matters

| You want | Where it comes from | Command |
|---|---|---|
| A module's inputs, outputs, versions | Registry **v1 JSON API** | `search`, `inspect-module` |
| A resource type's attributes (`aws_s3_bucket`) | **`terraform providers schema -json`** | `refresh-schema`, then `inspect-resource` |

The registry API does **not** serve resource schemas. That half needs the `terraform` CLI
once per provider to populate the cache; afterwards lookups are offline.

## What it does NOT do

- **It does not write, edit or apply Terraform.** It reads the registry and returns facts.
- **It does not scrape.** If a call fails, the fix is the runner or the path — never
  falling back to `registry.terraform.io`'s HTML, which defeats the entire design.
- **It does not judge module quality.** Search returns what the registry ranks; whether a
  module is well maintained is your call.
- **It holds no org-specific logic.** Catalog audits, scaffolding and house conventions
  belong in your own repo, calling this as a generic client.

## Requirements

- `uv` preferred, but the script is stdlib-only so `python3` works identically.
- The `terraform` CLI, **only** for `refresh-schema` — the module side needs nothing.
- Network access on first fetch of any given payload; everything after that can be
  `--offline`.

Call the script by **absolute path**. You will normally be working inside some other
repo, where a relative path silently fails to resolve. [`SKILL.md`](./SKILL.md) has the
`tfreg` shell-function recipe and explains why it is a function rather than a variable.

## Output contract

`--format json` emits a stable envelope with a `provenance` block carrying `source_url`,
`source_kind`, `retrieved_at` and whether the answer came from cache — so a fact can be
cited rather than asserted. `--format text` (the default) is for humans. Exit codes:
`0` ok, `1` not found, `2` usage, `3` network or registry error.

## How it fits

It is a concrete **producer** for [`source-snapshot`](../source-snapshot) — its cached
payloads *are* snapshots — and a citable source for fact-checking IaC claims. Pin
behaviour by inspecting a specific version (`.../aws/5.8.1`) and committing the cached
payload; that snapshot becomes a stable, quotable fact.

Tests: `cd evals && uv run python grade.py` — offline, deterministic, multi-provider.
