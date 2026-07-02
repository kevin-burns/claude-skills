---
name: use-linearis
description: Use when running Linear.app operations from the command line — creating, updating, archiving, listing, or filtering issues, setting project milestones, or wiring blocked-by relations via the `linearis` CLI (binaries `linear` and `linearis`, JSON output) instead of an MCP or the web UI. Triggers on any Linear issue/project/milestone task in a terminal, and on syncing Kevin's Ogham roadmap with its shared-memory database. Covers generic install/auth setup, the CLI's sharp edges, and the pre-loaded Ogham project IDs. Not a full reference — that's `linear <cmd> --help`.
license: MIT
---

# use-linearis

`linearis` is a Node CLI for Linear.app — JSON output, smart ID resolution, cursor pagination, built for LLM agents. It ships two identical binaries, `linear` and `linearis`. It is **not** an MCP: no tool schemas land in context, so every fresh session pays a discovery tax. This skill pays that tax up front — generic setup, the CLI's sharp edges, and Kevin's Ogham-project specifics.

If Linear ships an official MCP with write support, migrate to it. Until then, `linearis` is the agent-shaped CLI.

## Setup (generic — works for any Linear workspace)

**Source:** <https://github.com/linearis-oss/linearis> · npm package `linearis` (MIT). Requires Node.

Install globally, then authenticate:

```bash
npm i -g linearis        # installs BOTH `linear` and `linearis` (same binary)
linear auth login        # browser OAuth; stores a token at ~/.linearis/token
```

One-liner to confirm it's installed and authed:

```bash
command -v linear >/dev/null && linear auth status || echo "install: npm i -g linearis && linear auth login"
```

`auth status` returns `{authenticated: true, user: {name, email}}` when a token is live at `~/.linearis/token`. If write operations fail with `Invalid scope: write required`, generate a Personal API Key in the Linear web UI (Settings → API → Personal API keys) with `admin` scope, then either `export LINEAR_API_TOKEN=<key>` or overwrite `~/.linearis/token`.

Anything not pre-loaded below, discover with `--help` (this skill is the sharp edges, not the full surface):

```bash
linear --help
linear issues --help          # per-subcommand flags
```

## Gotchas (the ones that cost time — version 2026.4.9)

**1. Flag asymmetry between `issues create`/`update` and `issues list`.** Create/update take `--project-milestone <id>`; list takes `--milestone <name>` (and requires `--project`). Same concept, two flag names. Likewise `--label` (singular) on list vs `--labels` (comma-separated names) on create/update.

**2. Milestone create is broken.** `linear milestones create <name> --project <id>` returns `Variable "$projectId" of required type "String!" was not provided` even with the flag set. Create milestones in the web UI (Project → Milestones → New milestone, ~30s each) and reuse their IDs.

**3. Labels can't be created via CLI.** `linear labels` only has `list` and `usage`. Create labels in the web UI (Settings → Labels). A nonexistent label name on create fails with `Label "X" not found` and **no issue is created**.

**4. The stored token isn't a raw Personal API Key.** Copying `~/.linearis/token` into a `curl` `Authorization: Bearer …` header returns 401. Don't bypass the CLI by hitting GraphQL directly — fix `linearis` or stay on its surface.

**5. Project resolves by name or UUID, not slug.** `--project "Ogham"` works; `--project "ogham-4bd4e0924fda"` and `--project "4bd4e0924fda"` both return `Project not found`. Use the full UUID or the display name.

**6. Query-complexity ceiling.** `linear projects list` with no filter returned `Query too complex — complexity 13950 / 10000` on a 20+ project workspace. Use `--limit 5` or filter down.

---

## Kevin's Ogham project (pre-loaded identifiers)

Skip the four `list --limit 5 | jq` discovery calls at session start — reuse these:

| Thing | Value |
|---|---|
| Team | `TBU` (name: TBUdesigns, id: `8cb9a463-3aef-4489-85b1-28d901cfcd1c`) |
| Project | `d0221f7d-8ce0-404b-92ed-0f8975f94ddc` (name: Ogham, slugId: `4bd4e0924fda`) |
| Project URL | <https://linear.app/tbudesigns/project/ogham-4bd4e0924fda> |
| Milestone `v0.15.3` | `d9ca9182-b52c-42c2-bcd9-5ba93f060e8d` (target 2026-07-05) |
| Milestone `v0.16` | `54229ddf-58ac-4ca0-931d-823da8c2ee22` (target 2026-07-08) |
| Milestone `v0.17` | `95e3c2d4-3757-4816-98db-7f3d7f7682ed` (target 2026-07-31) |
| Labels (case-sensitive) | `Bug`, `Feature`, `Improvement`, `frontend` |

If a target date, ID, or label has drifted, refresh:

```bash
OGHAM=d0221f7d-8ce0-404b-92ed-0f8975f94ddc
linear milestones list --project "$OGHAM" | jq '.nodes[] | {name, id, targetDate}'
linear labels list | jq '.nodes[] | {name}'
```

### Ogham conventions

- **Title carries the release**: prefix atomic issues with `[vX.Y.Z]` (e.g. `[v0.16] Migrations 041-043: ...`). Milestone linkage is separate, but titles let you scan a mixed list.
- **Milestone = release, Issue = atomic backlog item, in-session TaskCreate = per-session scratch.** Don't mirror Linear issues into the in-session task tracker. Do stamp `TBU-N` into a scratch task's description before closing it as ported.
- **Release-execution issue per milestone** — the last issue in each milestone, blocked-by all the others, invokes CLAUDE.md's 10-step release playbook. Named `[vX.Y.Z] Execute release per 10-step playbook (blocked by all above)`.
- **Priority mapping**: `2` = release-critical, `3` = medium, `4` = nice-to-have. `1` (urgent) is reserved for hotfixes.

### The Linear ↔ Ogham dogfooding loop

The reason to drive `linearis` from Claude Code rather than clicking Linear's web UI is the Ogham workflow experiment: **durable state lives in Linear** (issue status, blocked-by, milestone); **transient session context lives in Ogham**, the shared-memory database.

Ogham ships its own CLI — `ogham`, a Go binary (MCP client for the Ogham memory stack, JSON output by default). Source: <https://github.com/ogham-mcp/ogham-cli>. It's installed locally but **not on PATH** (currently a `dev` build, behind latest), so invoke it by path or alias it:

```bash
alias ogham=~/Developer/web-projects/ogham-cli/ogham   # adjust to your checkout
```

So when an agent picks up `TBU-114`:

```bash
linear issues get TBU-114                       # durable: atomic spec, status, blocked-by
ogham search "typed edges store_triple"         # transient: design memory (hybrid vector+keyword)
```

`ogham search <query>` runs the fast native-Go hybrid search; add `--sidecar` for the full retrieval pipeline (intent detection, MMR, graph augmentation), `--limit N` / `--tags a,b` to scope. That pairing — spec from Linear, design memory from Ogham — is the loop every prior task-tracking attempt was missing. See `TBU-131` for the recipe deliverable in v0.17.

## Common recipes

Examples use the Ogham IDs above; swap `OGHAM`/`TBU`/milestone IDs for your own workspace.

**Create an atomic issue against a milestone**:

```bash
OGHAM=d0221f7d-8ce0-404b-92ed-0f8975f94ddc
V16_MS=54229ddf-58ac-4ca0-931d-823da8c2ee22
linear issues create "[v0.16] <what>" \
  --team TBU --project "$OGHAM" --project-milestone "$V16_MS" \
  --labels "Feature" --priority 2 \
  --description "$(cat <<'MD'
Body markdown.
MD
)"
```

**Batch create with error surfacing** — errors go to stdout as JSON, so `tee` a file and grep it:

```bash
OUT=/tmp/linear_batch.jsonl; : > "$OUT"
mk() { linear issues create "$1" --team TBU --project "$OGHAM" --labels "$2" --priority "$3" --description "$4" 2>&1 | tee -a "$OUT" | grep '"identifier"'; }
mk "[v0.16] Foo" "Feature" 2 "..."
mk "[v0.16] Bar" "Improvement" 3 "..."
grep '"error"' "$OUT" || echo "clean"
```

**Backfill a milestone across a range of issues**:

```bash
V16_MS=54229ddf-58ac-4ca0-931d-823da8c2ee22
for n in 109 110 111 112 113; do
  linear issues update "TBU-$n" --project-milestone "$V16_MS" | grep '"identifier"'
done
```

**Wire blocked-by** — one call per dependency, `--blocked-by` on `issues update`:

```bash
wire() {
  local blocker="$1"; shift
  for dep in "$@"; do
    linear issues update "TBU-$blocker" --blocked-by "TBU-$dep" 2>&1 | grep '"error"'
  done
}
wire 121 109 110 111 112 113 114 115 116 117 118 119 120 122 123
```

**Filter open issues in a release**:

```bash
linear issues list --project "$OGHAM" --milestone v0.16 --limit 50 | \
  jq -r '.nodes[] | "\(.identifier)  \(.state.name)  \(.title)"'
```

**Clean up a stray test issue** (archive over delete — leaves history; both need `admin` scope):

```bash
linear issues archive TBU-102
```
