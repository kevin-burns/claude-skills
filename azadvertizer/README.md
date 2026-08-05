# azadvertizer

Deterministic, offline lookups over Azure **Policy**, **Initiative** and **RBAC Role**
metadata — including the cross-references that exist nowhere else in one place.

Part of [claude-skills](../README.md).

## What it does

[AzAdvertizer](https://www.azadvertizer.net) publishes Azure governance metadata as
downloadable CSV exports. There is **no API**. This skill fetches those CSVs once,
validates them, caches them with provenance, and then answers queries entirely offline.

The unique value is the **cross-references** AzAdvertizer computes, which raw Azure
sources do not give you together:

```bash
azadv rel policy-roles <policyId>        # which roles a policy assigns
azadv rel policy-initiatives <policyId>  # which policy sets include it
azadv rel role-policies <roleId>         # which policies rely on a role
```

That first one is the everyday case: a `deployIfNotExists` or `modify` policy needs a role
assignment to work, and this tells you which role — before you write the
`policyAssignment`, rather than after it fails.

Also: `get policy|role|initiative <id|name>` for definitions, effects, allowed effects and
role actions; `search <type> --where COL=SUBSTR` for finding candidates by category or
effect, with `--limit`/`--offset` paging.

**Freshness is automatic.** Read commands auto-refresh a snapshot older than a week
(`--max-age-days 7`), so facts do not silently rot and you rarely call `fetch` yourself.
`--offline` disables refresh entirely and serves the cached snapshot flagged `stale` — use
it for hermetic runs. If a refresh fails, the last good snapshot is served with a warning
rather than a hard failure mid-query.

## What it does NOT do

- **It is not authoritative for definitions.** This is second-hand data. Where licensing or
  authority matters, prefer Azure's own sources — `az policy definition list`,
  `az role definition list`, the `Azure/azure-policy` repo. Use this skill for the
  *enriched, cross-referenced* view.
- **It does not scrape.** The site serves no JSON; scraping its HTML would defeat the
  entire design. If a call fails, fix the runner or the path — never fall back to fetching
  pages. Every fact surfaced must come from the helper's JSON envelope.
- **It does not write or apply Azure configuration.** Read-only lookups.
- **It does not survive schema drift silently.** The source is undocumented and
  unversioned; column names and file slugs can change without notice. The helper pins a
  per-CSV schema and **refuses to overwrite a good cache on drift**. A fetch failing with
  "schema drift" means upstream changed and the field map needs updating — that is the
  design working, not a bug.

## Requirements

- `uv` preferred (it pins the right Python via inline metadata). The script is stdlib-only
  and needs **Python ≥ 3.12**, so plain `python3` works if it is new enough.
- Network access on first fetch and on weekly refresh; everything else is offline.
- No Azure credentials, no subscription, no `az login` — this reads published CSVs.

Run the helper by **absolute path**, and note the shell function is called `azadv`, **not
`az`** — `az` is the Azure CLI, which you almost certainly have installed in this context,
and shadowing it would be its own bug. [`SKILL.md`](./SKILL.md) has the recipe.

## Worth knowing

**Cache aggressively.** This is a free personal project by one person, and the initiatives
CSV is roughly 14 MB. Never fetch per query. The cache lives in
`$XDG_CACHE_HOME/azadvertizer`; fetches are gzipped on the wire, atomic (temp→rename), and
validated against a header schema and a row floor before replacing anything.

**Output is a stable JSON envelope** with `ok`, `data`, a `provenance` block
(`source_url`, `fetched_at`, `sha256`, `rows`, `snapshot_age_days`, `stale`), `warnings`
and `error`. Exit codes: `0` ok, `1` not found, `2` usage, `3` cache missing, `4`
fetch/schema/row-floor error. Cell values are sanitised on output — a leading `=`, `+`,
`-` or `@` is prefixed with `'` so results are safe to paste into a spreadsheet.

## Attribution

Data © Julian Hayward / [AzAdvertizer](https://www.azadvertizer.net). Snapshots are
provenance-stamped mirrors for local use — do not republish them as your own.

Tests: `cd evals && uv run python grade.py` — offline, and it covers the fail-safe
behaviour (schema drift and row-floor failures must not overwrite a good cache).
