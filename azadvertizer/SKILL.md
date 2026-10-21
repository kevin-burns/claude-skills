---
name: azadvertizer
description: >-
  Offline lookups over AzAdvertizer's published Azure data: Policy, policy initiative and RBAC role metadata with cross-references found nowhere else in one place (which roles a policy uses, which initiatives include a policy, which policies use a role), plus Entra ID roles, API permissions (Microsoft Graph and other first-party apps) and resource types with their latest API versions. Use whenever accurate current facts about an Azure built-in policy, initiative, RBAC or Entra role, Graph permission or resource API version are needed for Azure IaC, governance or landing-zone work.
license: MIT
---

# azadvertizer

[AzAdvertizer](https://www.azadvertizer.net) (by Julian Hayward) tracks Azure governance
capabilities — Policies, Initiatives (policy sets), and RBAC Roles — and publishes them in
**one combined, normalised JSON file**:
`https://www.azadvertizer.net/skillData/polPolsetRole.json` (~1 MB gzip, ~7.7 MB raw,
refreshed daily, ETag set). A second, compact file,
`https://www.azadvertizer.net/vscode/index.json`, adds **Entra ID roles, API permissions
and resource types with their latest API versions**. There is no query API. This skill turns
those files into deterministic offline lookups: fetch once, validate, cache with provenance, then query
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
   `get role <id|name>` then `rel role-policies <id>`. Typical for least-privilege
   and custom-role design.
4. **"Find candidate policies by category/effect."** → `search policy --where
   policyCategory=… --where policyEffect=…`. Typical when assembling or auditing a set.
5. **"Which API version should this resource use?"** → `get resource-type
   Microsoft.KeyVault/vaults`. Typical when pinning an `azapi` or Bicep resource type.
6. **"Is this Graph permission Application or Delegated, and does it need admin
   consent?"** → `get api-permission User.Read.All`. Typical when reviewing an app
   registration or a workload identity's grants.
7. **"Is this Entra role privileged?"** → `get entra-role "Global Administrator"` —
   privileged flag and EntraOps tier (ControlPlane / ManagementPlane / UserAccess).

The lifecycle is **fetch once, query many, refresh weekly — automatically**. Read commands
(`get`/`search`/`rel`) **auto-refresh a snapshot older than one week** (the default
`--max-age-days 7`); within that window nothing is re-downloaded, so repeated calls in a
session stay fast and deterministic. So in practice you often don't call `fetch` at all —
the first query of the week refreshes, the rest are offline. The JSON envelope is built to
be consumed by **azure-architect** (design decisions), **terragrunt-skill** (IaC
generation/review), and **fact-verifier** (each cached snapshot is a citeable tier-1
source).

## Honest caveats (read before relying on it)

- **Versioned, but it can still change.** The file carries a format version (`v`) and a
  `schema` description. The helper pins `v = 1` plus every field it reads, checked on every
  entity, and **refuses to overwrite a good cache on drift** — if a fetch starts failing
  with "schema drift", the upstream changed; update the pinned fields.
- **It's a free personal project.** Cache aggressively; never fetch the file per query.
  Snapshots are point-in-time — refresh on a cadence, not live-per-run. A refresh sends the
  stored ETag and the server answers 304 when the file has not changed (fixed upstream on
  2026-10-19; before that it always sent the full file).
- **Names and descriptions come from the definitions** since the 2026-10-19 file, commas
  included. Snapshots fetched before then have commas turned into semicolons; `fetch --force`
  replaces one.
- **The index is positional, so its field order is pinned.** `vscode/index.json` rows are
  arrays; the helper refuses a file whose own `schema` text for an entity differs from the
  pinned string, rather than read every value one column off.
- **Index text is truncated upstream.** Entra role descriptions stop at 220 characters and
  permission display names at 120.
- **A `null` API version means the index has none**, not that no API exists. 8,255 of
  12,379 resource types have no stable version on 2026-10-19, mostly operation-status and
  diagnostic sub-types; the main types (`microsoft.web/sites`, `microsoft.keyvault/vaults`)
  carry one.
- **Page links are checked live.** Every row carries a `page` URL, each pattern verified
  against the site with a made-up id as the 404 control. An API permission page is per app,
  `azentraidapipermissions/<appId>_<permissionId>.html`; the bare `<permissionId>.html`
  forwards to the Microsoft Graph permission, so it is the wrong page for any other app.
- **Checked against Microsoft Learn on 2026-10-20** (the Entra built-in roles reference and
  the Graph permissions reference, from their GitHub sources):
  - *Entra roles:* all 136 roles on Learn are present with the same template ids, and the
    `privileged` flag matches Learn's PRIVILEGED label on every one (35 privileged). The
    index has 9 more: roles Learn lists as deprecated or "not shown because it can't be
    used" (Guest User, Device Users, …). Two names differ from Learn's: the index has `Azure AD
    Joined Device Local Administrator` and `Customer LockBox` where Learn has `Microsoft
    Entra Joined Device Local Administrator` and `Customer Lockbox`. The index's names are
    what the directory returns; Learn's newer names are not served by any endpoint. Descriptions are the
    directory's own text, which differs from Learn's summary in 16 roles.
  - *Graph permissions:* every id on Learn is present with the same value, Application or
    Delegated type and admin-consent flag; display names differ only in apostrophes and
    spacing. The index has 65 Graph entries whose ids are not on Learn (63 of them not named
    there at all): newer permissions from the live service principal, ahead of the docs.
  - *Not on Learn at all,* so not checked: `entraOpsClassification` (the EntraOps model,
    Cloud-Architekt/AzurePrivilegedIAM) and `graphPrivilegeLevel` (Graph only; null on 315
    Graph entries).
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
azadv fetch                 # downloads policies, roles and initiatives (one file) into the cache
```

The script is stdlib-only and needs Python ≥3.12, so if (and only if) uv is genuinely not
installed you can swap the runner for plain python3 — same arguments:
`azadv() { python3 "$HOME/.claude/skills/azadvertizer/scripts/azadvertizer.py" "$@"; }` (python3 ≥3.12).

If a call fails with `command not found` (uv unresolved) or `No such file or directory` (wrong
path), fix the runner/path — re-resolve uv as above, or use the announced base directory.
**Do not** fall back to fetching azadvertizer.net's pages or the data file directly:
the helper validates the file and stamps provenance, and scraping the HTML defeats the
entire point of this skill. Every fact you surface
must come from the helper's JSON envelope, full stop.

Cache lives in `$XDG_CACHE_HOME/azadvertizer` (override with `--cache-dir`). Fetch is
gzip-on-the-wire, decompressed-at-rest, **atomic** (temp→rename), and **validated**
(format version, every pinned field, row floors) before it replaces anything. No third-party dependencies —
`uv run` handles the stdlib-only script.

## Query (all offline, JSON envelope)

`azadv` is the function defined in Setup above (named to avoid clashing with the Azure CLI's
`az`) — re-declare it at the top of the block if this is a fresh command (shell state doesn't
carry over between tool calls).

```bash
# exact lookup by id OR name
azadv get policy 7ca8c8ac-3a6e-493d-99ba-c5fa35347ff2
azadv get role "Contributor"                  # list fields are always arrays
azadv get initiative <initiativeId>            # grouped: initiative meta + member policies
azadv get entra-role "Global Administrator"   # privileged flag, EntraOps tier, permission count
azadv get api-permission User.Read.All        # every app and id with that value (a list)
azadv get resource-type Microsoft.KeyVault/vaults   # latest stable + preview API version

# substring search (case-insensitive, repeatable --where COL=SUBSTR)
azadv search policy --where policyCategory=Storage --where policyEffect=Deny \
   --fields policyName,policyEffect,policyId --limit 20
azadv search role --name "Reader"
azadv search initiative --name "NIST"
azadv search api-permission --where appName="Microsoft Graph" --where permissionType=Application
azadv search resource-type --where resourceType=microsoft.network/ --fields resourceType,latestStableApiVersion

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
  "provenance": { "source_url": "...", "fetched_at": "...", "generated": "...",
                  "etag": "...", "sha256": "...",
                  "counts": { "policies": 4574, "roles": 986, "initiatives": 249 },
                  "snapshot_age_days": 2.1, "stale": false },
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

## The field map

Output keeps the **column names of the CSV exports** this skill read until 2026-10
(`policyName`, `policyEffect`, `policyRolesUsed`, `RoleActions`, `UsedInPolicy`,
`initiativeId` …), so `--where` and `--fields` work as before and consumers don't change.
Three differences:

- **List fields are always arrays.** `--split` is still accepted and does nothing.
- **Cross-references are `[{name, id}]`** (`policyUsedInPolicySet` adds `source`, the
  initiative's type), resolved against the same snapshot. Effects use one spelling each.
- **`policyPreview` / `policyDeprecated` are booleans**; `--where policyDeprecated=false`
  matches them as text.

The three index datasets have no legacy names, so their columns are new:

| dataset | columns |
|---|---|
| `entra-role` | `entraRoleId`, `entraRoleName`, `privileged` (bool), `entraOpsClassification`, `permissionsTotal`, `entraRoleDescription`, `page` |
| `api-permission` | `permissionId`, `permissionValue`, `permissionDisplayName`, `permissionType` (Application / Delegated / Resource-specific (application)), `adminConsentRequired` (bool), `graphPrivilegeLevel` (Graph only, else null), `appId`, `appName`, `page` |
| `resource-type` | `resourceType` (lower-cased `namespace/type`), `resourceTypeName`, `latestStableApiVersion`, `latestPreviewApiVersion` (only when newer than stable), `providerDisplayName`, `operationsCount`, `policyAliasesCount`, `page` |

`api-permission` is one row per entry: one value such as `User.Read.All` is ten ids across
seven apps. 64 ids have two entries: 12 are shared by two apps, and 52 are one app using
the same GUID for its Application and Delegated permission (Graph's `User.Export.All`,
which Microsoft's permissions reference lists the same way). Filter on `permissionType`
when the distinction matters. `get
api-permission` therefore returns a list. The index's pinned shape lives in `INDEX_SCHEMA`,
`INDEX_ROW_LEN` and `PERMISSION_TYPES`; each source is cached in its own file, so a failed
index fetch never touches the policy data.

Why the CSVs went: their per-file list delimiters broke two lookups. `policyUsedInPolicySet`
entries end in `) BuiltIn;`, so `rel policy-initiatives` returned one item where a policy
was in many (1,723 of 4,574 policies on 2026-10-18), and an unused role's ` ()` came back as
one blank item (938 roles). The evals pin both. The pinned shape lives in `TOP_KEYS`,
`ENTITY_FIELDS` and `MEMBER_FIELDS` at the top of `scripts/azadvertizer.py`.

## Scaling up (deliberately deferred)

This dataset is small (~22k entities and members), so the query path is stdlib dict
lookups and a linear scan for `search` —
no pandas/polars/DuckDB. If genuine **cross-file relational** queries become a real need
("policies in category X used by initiatives that also grant role Y"), the documented
escalation is stdlib **`sqlite3`** (build a DB on ingest) — still zero third-party
dependencies. Don't add it speculatively.

## Provenance & attribution

**All data surfaced by this skill is created and maintained by Julian Hayward (Microsoft
MVP) and published at [azadvertizer.net](https://www.azadvertizer.net).** AzAdvertizer is
his free, community-driven project; the policy/role/initiative metadata and — crucially —
the enrichment and cross-references are his work, not this skill's. This skill only
*fetches and caches the data file he publishes*; it does **not** redistribute it
(nothing is committed to this repo beyond a tiny test fixture).

Provenance is tracked end to end so any fact can be traced back to its source:

- Each cached snapshot writes a `*.meta.json` with `source_url`, `fetched_at` (UTC), the
  file's own `generated` time, `etag`, `sha256`, per-entity `counts`, and the
  `attribution` string the file itself carries.
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
  `fetch --only core|index` refreshes one source.
- `evals/` — offline behavioral eval (`cd evals && uv run python grade.py`): lookups, relationship
  resolution, grouping, staleness, sanitization, the two CSV-era regressions, and the
  ingest fail-safe (drift, version, non-JSON and row-floor refusal, atomic write, 304),
  and for the index the decoded columns and the refusal of a reordered field list, against
  committed fixtures.
