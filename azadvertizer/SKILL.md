---
name: azadvertizer
description: Deterministic, offline-first lookups over Azure Policy, Policy Initiative, and RBAC Role metadata sourced from AzAdvertizer's CSV exports — including the cross-references that exist nowhere else in one place (which roles a policy uses, which initiatives include a policy, which policies a role is used by). Use whenever you need accurate current facts about an Azure built-in policy, initiative/policy-set, or RBAC role — definitions, effects, allowed effect values, categories, role actions/dataActions, or the policy↔role and policy↔initiative relationships — for writing or reviewing Azure IaC, governance, or landing-zone work. Fetches each CSV once into a provenance-stamped cache and answers queries offline; stdlib only, JSON envelope output. Pairs with terragrunt-skill, azure-architect, and fact-verifier (snapshots become tier-1 sources).
license: MIT
---

# azadvertizer

[AzAdvertizer](https://www.azadvertizer.net) (by Julian Hayward) tracks Azure governance
capabilities — Policies, Initiatives (policy sets), and RBAC Roles — and publishes them as
**downloadable CSV exports**. There is **no API**. This skill turns those CSVs into
deterministic offline lookups: fetch once, validate, cache with provenance, then query
without touching the network.

The unique value is the **cross-references** AzAdvertizer computes that raw Azure sources
don't give you in one place: `policyRolesUsed`, `policyUsedInPolicySet`, and (per role)
`UsedInPolicy`. For canonical *definitions* where licensing/authority matters, prefer
Azure's own sources (`az policy definition list`, `az role definition list`, the
`Azure/azure-policy` repo) — use this skill for the enriched, cross-referenced view.

## How you'll usually use it

In most cases this skill answers a concrete Azure-governance question that came up while
writing or reviewing IaC (Terraform/Terragrunt/Bicep), designing a landing zone, or doing
a least-privilege review. The common shapes:

1. **"What does this policy do — its effect, allowed effects, and what roles does it
   assign?"** → `get policy <id|name>` then `rel policy-roles <id>`. Typical before adding
   a `policyAssignment` (a `deployIfNotExists`/`modify` policy needs the right role, and
   this tells you which).
2. **"What's in this initiative / which built-in initiative includes this policy?"** →
   `get initiative <id>` or `rel policy-initiatives <policyId>`. Typical for compliance
   set-building (NIST, CIS, ALZ) and landing-zone governance.
3. **"What actions does this RBAC role grant, and which policies rely on it?"** →
   `get role <id|name> --split` then `rel role-policies <id>`. Typical for least-privilege
   and custom-role design.
4. **"Find candidate policies by category/effect."** → `search policy --where
   policyCategory=… --where policyEffect=…`. Typical when assembling or auditing a set.

The lifecycle is **fetch once, query many, refresh weekly — automatically**. Read commands
(`get`/`search`/`rel`) **auto-refresh a snapshot older than one week** (the default
`--max-age-days 7`); within that window nothing is re-downloaded, so repeated calls in a
session stay fast and deterministic. So in practice you often don't call `fetch` at all —
the first query of the week refreshes, the rest are offline. The JSON envelope is built to
be consumed by **azure-architect** (design decisions), **terragrunt-skill** (IaC
generation/review), and **fact-verifier** (each cached snapshot is a citeable tier-1
source).

## Honest caveats (read before relying on it)

- **Undocumented, unversioned source.** Column names/file slugs can change without notice.
  The helper pins a per-CSV schema and **refuses to overwrite a good cache on drift** —
  if a fetch starts failing with "schema drift", the upstream changed; update the field map.
- **It's a free personal project.** Cache aggressively; never fetch the 14 MB initiatives
  file per query. Snapshots are point-in-time — refresh on a cadence, not live-per-run.
- **Second-hand data.** Treat snapshots as provenance-stamped mirrors, not ground truth.
- **Attribution.** Data © Julian Hayward / AzAdvertizer. Don't republish it as your own.

## Setup: fetch once

**Run the helper by its absolute path — never a relative one.** The script sits next to this
SKILL.md, inside the base directory announced when the skill loads (usually
`~/.claude/skills/azadvertizer`, or a plugin path if installed that way). You'll normally be
working inside some *other* repo — an Azure IaC / landing-zone project — so a bare relative
path like `azadvertizer/scripts/azadvertizer.py` will **not** resolve and the script never
runs.

Define an `azadv` shell function at the **start of each command block**, then call it. Two
deliberate choices here: (1) a function rather than a `VAR="…"; $VAR` string, because a plain
`$VAR` does **not** word-split in zsh — `$VAR status` becomes one bogus command name and emits
no JSON; a function passes arguments correctly under both bash and zsh. (2) the name `azadv`,
**not** `az` — `az` is the Azure CLI, which you almost certainly have installed in this context,
and a function named `az` would shadow it. Shell state does not persist between separate tool
calls, so re-declare `azadv` in every block (or just write the full `uv run <path> …`).

```bash
# uv is the preferred runner (it pins the right Python via the script's inline metadata).
# Resolve uv even when it's not on a bare PATH — non-interactive shells sometimes drop
# ~/.local/bin or the Homebrew bin, which is the usual cause of `uv: command not found`:
UV="$(command -v uv || ls "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)"
azadv() { "$UV" run "$HOME/.claude/skills/azadvertizer/scripts/azadvertizer.py" "$@"; }   # use the announced base dir

azadv status                # offline; confirms the runner + path resolve and shows cache state
azadv fetch                 # downloads policy, role, initiative CSVs into the cache
azadv fetch --only policy   # or just one
```

The script is stdlib-only and needs Python ≥3.12, so if (and only if) uv is genuinely not
installed you can swap the runner for plain python3 — same arguments:
`azadv() { python3 "$HOME/.claude/skills/azadvertizer/scripts/azadvertizer.py" "$@"; }` (python3 ≥3.12).

If a call fails with `command not found` (uv unresolved) or `No such file or directory` (wrong
path), fix the runner/path — re-resolve uv as above, or use the announced base directory.
**Do not** fall back to fetching azadvertizer.net's pages directly: the site serves **no
JSON**, and scraping its HTML defeats the entire point of this skill. Every fact you surface
must come from the helper's JSON envelope, full stop.

Cache lives in `$XDG_CACHE_HOME/azadvertizer` (override with `--cache-dir`). Fetch is
gzip-on-the-wire, decompressed-at-rest, **atomic** (temp→rename), and **validated**
(header schema + row floor) before it replaces anything. No third-party dependencies —
`uv run` handles the stdlib-only script.

## Query (all offline, JSON envelope)

`azadv` is the function defined in Setup above (named to avoid clashing with the Azure CLI's
`az`) — re-declare it at the top of the block if this is a fresh command (shell state doesn't
carry over between tool calls).

```bash
# exact lookup by id OR name
azadv get policy 7ca8c8ac-3a6e-493d-99ba-c5fa35347ff2
azadv get role "Contributor" --split          # --split expands list-valued cells
azadv get initiative <initiativeId>            # grouped: initiative meta + member policies

# substring search (case-insensitive, repeatable --where COL=SUBSTR)
azadv search policy --where policyCategory=Storage --where policyEffect=Deny \
   --fields policyName,policyEffect,policyId --limit 20
azadv search role --name "Reader"
azadv search initiative --name "NIST"

# pagination: searches can match a lot (e.g. "Defender" -> 100+ policies). search returns at
# most --limit rows (default 50) starting at --offset (default 0); page with --offset:
azadv search policy --name "Defender" --fields policyName,policyId --limit 50            # page 1
azadv search policy --name "Defender" --fields policyName,policyId --limit 50 --offset 50  # next page

# resolve cross-references (the unique value)
azadv rel policy-roles <policyId>        # roles a policy assigns: [{name, id}]
azadv rel policy-initiatives <policyId>  # policy sets a policy belongs to: [{name, id, source}]
azadv rel role-policies <roleId>         # policies that use a role: [{name, id}]
azadv rel initiative-policies <id>       # member policies of an initiative
```

**Freshness is automatic.** A snapshot older than `--max-age-days` (**default 7**) is
considered stale, and read commands **auto-refresh it before answering** — so facts never
silently rot. Tune the window with `--max-age-days N` (e.g. `0` forces a refresh every
call; a large number effectively pins the snapshot). Pass **`--offline`** to disable
refresh entirely: the cached snapshot is served and flagged `stale` in the envelope rather
than re-fetched — use this for hermetic/deterministic runs or when the network is
unavailable. If a refresh fails, the last good snapshot is served with a warning (never a
hard failure mid-query).

## Output contract

Every command prints one JSON object:

```json
{
  "ok": true,
  "command": "rel",
  "data": { "...": "command-specific" },
  "provenance": { "source_url": "...", "fetched_at": "...", "sha256": "...",
                  "rows": 4512, "snapshot_age_days": 2.1, "stale": false },
  "warnings": [],
  "error": null
}
```

Exit codes: `0` ok · `1` not-found/empty · `2` usage · `3` cache-missing (run `fetch`) ·
`4` fetch/schema/row-floor error. Cell values are **sanitized on output** — a leading
`= + - @` (spreadsheet-formula-injection) is prefixed with `'` so results are safe to
re-export or render (e.g. via `report-builder`).

**`search` pagination.** `data` is the current page (a list); `provenance` carries the paging
state so you can fetch the next page deterministically without re-scanning blindly:
`matched` (total hits across the snapshot), `returned` (rows in this page), `offset`, `limit`,
`has_more` (bool), and `next_offset` (the `--offset` for the next page, or `null` at the end).
When `has_more` is true a warning also spells out the next call. Loop until `next_offset` is
`null`; an `--offset` past the end returns an empty page with `has_more: false` (not an error).

## The field map (why parsing is non-obvious)

List-valued cells use **different delimiters per file** — verified against real rows, and
the single most important thing to get right:

| File | List delimiter | Notes |
|---|---|---|
| policy | `; ` (semicolon-space) | `cloudEnvs` uses bare `;` |
| role | `, ` (comma-space) | applies to **all** role list columns |
| initiative | `; ` / `;` | mostly denormalized scalars |

`Name (guid)` columns (`policyRolesUsed`, `policyUsedInPolicySet`, role `UsedInPolicy`) are
split **anchored on the closing `)`** so names containing the delimiter don't over-split.
Role `*DataActions` of literal `"empty"` parse to `[]`. The authoritative map (columns,
delimiters, keys, row floors, expected headers) lives in `DATASETS` at the top of
`scripts/azadvertizer.py` — update it there if the upstream drifts.

## Scaling up (deliberately deferred)

This dataset is tiny (~22k rows total), so the query path is a stdlib `csv` linear scan —
no pandas/polars/DuckDB. If genuine **cross-file relational** queries become a real need
("policies in category X used by initiatives that also grant role Y"), the documented
escalation is stdlib **`sqlite3`** (build a DB on ingest) — still zero third-party
dependencies. Don't add it speculatively.

## Provenance & attribution

**All data surfaced by this skill is created and maintained by Julian Hayward (Microsoft
MVP) and published at [azadvertizer.net](https://www.azadvertizer.net).** AzAdvertizer is
his free, community-driven project; the policy/role/initiative metadata and — crucially —
the enrichment and cross-references are his work, not this skill's. This skill only
*fetches and caches his published CSV exports*; it does **not** redistribute them (no CSV
data is committed to this repo beyond tiny test fixtures).

Provenance is tracked end to end so any fact can be traced back to its source:

- Each cached snapshot writes a `*.meta.json` with `source_url`, `fetched_at` (UTC),
  `sha256`, `rows`/`cols`, and an `attribution` string crediting AzAdvertizer.
- Every query echoes that provenance (plus `snapshot_age_days` / `stale`) in the JSON
  envelope, so downstream consumers (`fact-verifier`, `report-builder`, `azure-architect`)
  cite the snapshot, not a guess.

When you surface this data in any output — a report, a review, a recommendation — **credit
AzAdvertizer / Julian Hayward and link <https://www.azadvertizer.net>.** Respect that it's
a free service: cache and reuse snapshots, refresh on a sensible cadence, and don't hammer
its bandwidth. Honour any terms published on the site. For authoritative, license-clear
definitions, go to Microsoft's own sources; use AzAdvertizer for the cross-referenced view
it uniquely provides.

## Tooling

- `scripts/azadvertizer.py` — the stdlib CLI (fetch/status/get/search/rel) + field map.
- `evals/` — offline behavioral eval (`uv run evals/grade.py`): lookups, relationship
  parsing, grouping, staleness, sanitization, and the ingest fail-safe (schema-drift and
  row-floor refusal, atomic write) against committed fixtures.
