---
name: use-linearis
description: Use when running Linear.app operations from the command line — creating, updating, archiving, listing, or filtering issues, setting project milestones, or wiring blocked-by relations via the `linearis` CLI (binaries `linear` and `linearis`, JSON output) instead of an MCP or the web UI. Triggers on any Linear issue/project/milestone task in a terminal, and on syncing Kevin's Ogham roadmap with its shared-memory database. Covers generic install/auth setup, the CLI's sharp edges, and how to resolve your own workspace identifiers. Not a full reference — that's `linear <cmd> --help`.
license: MIT
---

# use-linearis

`linearis` is a Node CLI for Linear.app — JSON output, smart ID resolution, cursor pagination, built for LLM agents. It ships two identical binaries, `linear` and `linearis`. It is **not** an MCP: no tool schemas land in context, so every fresh session pays a discovery tax. This skill pays that tax up front — generic setup, the CLI's sharp edges, and the Ogham dogfooding workflow. It carries **no real workspace identifiers**; resolve your own (see below).

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

Anything not covered below, discover with `--help` (this skill is the sharp edges, not the full surface):

```bash
linear --help
linear issues --help          # per-subcommand flags
```

## Gotchas (the ones that cost time — re-verified against 2026.6.0 on 2026-08-05)

**1. Flag asymmetry between `issues create`/`update` and `issues list`.** Create/update take `--project-milestone <ms>`; list takes `--milestone <name>` (and requires `--project`). Same concept, two flag names. Likewise `--label` (singular, comma-separated) on list vs `--labels` on create/update.

**2. ~~Milestone create is broken.~~ Fixed in 2026.6.0** ([#223](https://github.com/linearis-oss/linearis/issues/223), [#228](https://github.com/linearis-oss/linearis/issues/228))**.** It used to return `Variable "$projectId" of required type "String!" was not provided` even with `--project` set, so the workaround was to create milestones in the web UI. The project id is now passed correctly — an invalid project yields a clean `Project "X" not found` instead of the variable error. `milestones` also gained `read` and `update`. Note there is still **no `milestones delete`**, so a mistyped milestone has to be cleaned up in the web UI; that is why the fix above was probed with a deliberately invalid project rather than by creating a throwaway.

**3. ~~Labels can't be created via CLI.~~ Fixed in 2026.6.0** ([#117](https://github.com/linearis-oss/linearis/issues/117))**.** `linear labels` now has `create`, `read`, `update` and `delete` alongside `list`. Still true, and still the expensive part: a nonexistent label name passed to `issues create` fails with `Label "X" not found` and **no issue is created** — so create the label first, or the whole call is a no-op.

**4. The stored token isn't a raw Personal API Key.** Copying `~/.linearis/token` into a `curl` `Authorization: Bearer …` header returns 401. Don't bypass the CLI by hitting GraphQL directly — fix `linearis` or stay on its surface.

**5. Project resolves by name or UUID, not slug — and the slug is the one you'll reach for.** `projects list` hands you both a `slugId` and a `url`, and the slug is what sits in every Linear project URL, so it is the natural thing to paste. Neither form is accepted:

```bash
linear issues list --project "Ogham"                                  # resolves
linear issues list --project "00000000-proj-0000-0000-000000000000"   # resolves
linear issues list --project "abcdef012345"                           # Project not found
linear issues list --project "myproject-abcdef012345"                     # Project not found
```

Same on `milestones list --project`. Use the display name or the full UUID.

**6. Query-complexity ceiling.** `linear projects list` with no filter returns `Query too complex — complexity 13950 / 10000`. Use `--limit 5` or filter down. Not a linearis bug as such — it is Linear's own GraphQL cost limit — but tracked upstream as [#276](https://github.com/linearis-oss/linearis/issues/276) (open), which reports it firing even on a one-project workspace.

**7. Fetching one issue is `read`, not `get` — and `get` is never coming.** `linear issues read <issue>` returns the full record including the description. Asking for `get` fails with `error: too many arguments for 'issues'. Expected 0 arguments but got 2`, which reads like a flag problem rather than a wrong verb and sends you hunting through `--help` for the wrong thing.

This is a well-worn trap, not a local quirk: upstream [#48](https://github.com/linearis-oss/linearis/issues/48) reports LLMs reaching for `issues get` with exactly this error, and was closed **NOT_PLANNED** — aliases are a deliberate no, so do not wait for it. The recovery problem it describes is tracked separately as [#281](https://github.com/linearis-oss/linearis/issues/281) (open): malformed commands emit plain-text on stderr while valid-command errors emit the JSON envelope, both exit 1, so an agent cannot tell "I called it wrong" from "that issue doesn't exist".

Practical consequence: **a non-JSON error means you got the verb or arity wrong, not that the entity is missing.** Related verbs on the same object: `search <query>` (full-text), `archive` / `unarchive` / `delete <issue>`.

**8. Sub-collections come back as `{nodes: […]}`, not bare arrays.** `issues read` returns `labels`, `comments`, `children` and `relations` each wrapped in a `nodes` key, while `issues list` returns its results under a top-level `nodes`. So `jq '[.labels[].name]'` fails with `Cannot index array with string "name"` — it needs `jq '[.labels.nodes[].name]'`. Cheap way to avoid guessing:

```bash
linear issues read ENG-227 | jq 'keys'          # what fields exist
linear issues read ENG-227 | jq '.labels'       # what shape a given field is
```

**Version pin:** every gotcha above was re-verified against **2026.6.0** on 2026-08-05. Two of the eight had already gone stale by then (2 and 3 — both told you to go and use the web UI for something the CLI had since learned to do), so check before trusting:

```bash
linear --version; npm view linearis version    # drifted? re-verify 1-8 before relying on them
```

---

## Workspace identifiers — discover once, cache locally

This skill deliberately contains **no real IDs**. It is a public repo, and workspace, team, project and milestone UUIDs describe someone's private tracker even though they are not credentials. Every example below uses obvious placeholders (`00000000-proj-…`, `abcdef012345`).

Resolve yours once per session and keep them in shell variables — that costs three calls and beats hard-coding values that drift anyway:

```bash
TEAM=ENG                                    # your team key
PROJECT=$(linear projects list --limit 20 | jq -r '.nodes[] | select(.name=="Ogham") | .id')
linear milestones list --project "$PROJECT" | jq -r '.nodes[] | "\(.name)  \(.id)  \(.targetDate)"'
linear labels list | jq -r '.nodes[].name'   # label names are case-sensitive on create
```

If you want them to survive across sessions, write them to a gitignored file rather than back into this skill:

```bash
mkdir -p ~/.config/linearis
cat > ~/.config/linearis/ids.env <<EOF
TEAM=$TEAM
PROJECT=$PROJECT
EOF
# then: source ~/.config/linearis/ids.env
```

Remember gotcha 5: `--project` takes the **display name or full UUID**, never the slug from the project URL.

### Ogham conventions

- **Title carries the release**: prefix atomic issues with `[vX.Y.Z]` (e.g. `[v0.16] Migrations 041-043: ...`). Milestone linkage is separate, but titles let you scan a mixed list.
- **Milestone = release, Issue = atomic backlog item, in-session TaskCreate = per-session scratch.** Don't mirror Linear issues into the in-session task tracker. Do stamp `ENG-N` into a scratch task's description before closing it as ported.
- **Release-execution issue per milestone** — the last issue in each milestone, blocked-by all the others, invokes CLAUDE.md's 10-step release playbook. Named `[vX.Y.Z] Execute release per 10-step playbook (blocked by all above)`.
- **Priority mapping**: `2` = release-critical, `3` = medium, `4` = nice-to-have. `1` (urgent) is reserved for hotfixes.

### The Linear ↔ Ogham dogfooding loop

The reason to drive `linearis` from Claude Code rather than clicking Linear's web UI is the Ogham workflow experiment: **durable state lives in Linear** (issue status, blocked-by, milestone); **transient session context lives in Ogham**, the shared-memory database.

Ogham ships its own CLI — `ogham`, a Go binary (MCP client for the Ogham memory stack, JSON output by default). Source: <https://github.com/ogham-mcp/ogham-cli>. It's installed locally but **not on PATH** (currently a `dev` build, behind latest), so invoke it by path or alias it:

```bash
alias ogham=~/Developer/web-projects/ogham-cli/ogham   # adjust to your checkout
```

So when an agent picks up `ENG-114`:

```bash
linear issues read ENG-114                      # durable: atomic spec, status, blocked-by
ogham search "typed edges store_triple"         # transient: design memory (hybrid vector+keyword)
```

`ogham search <query>` runs the fast native-Go hybrid search; add `--sidecar` for the full retrieval pipeline (intent detection, MMR, graph augmentation), `--limit N` / `--tags a,b` to scope. That pairing — spec from Linear, design memory from Ogham — is the loop every prior task-tracking attempt was missing. See `ENG-131` for the recipe deliverable in v0.17.

## Common recipes

Examples use the Ogham IDs above; swap `OGHAM`/`ENG`/milestone IDs for your own workspace.

**Create an atomic issue against a milestone**:

```bash
OGHAM=00000000-proj-0000-0000-000000000000
V16_MS=00000000-ms02-0000-0000-000000000000
linear issues create "[v0.16] <what>" \
  --team ENG --project "$OGHAM" --project-milestone "$V16_MS" \
  --labels "Feature" --priority 2 \
  --description "$(cat <<'MD'
Body markdown.
MD
)"
```

**Batch create with error surfacing** — errors go to stdout as JSON, so `tee` a file and grep it:

```bash
OUT=/tmp/linear_batch.jsonl; : > "$OUT"
mk() {
  local title=${title:?} labels=${labels:?} prio=${prio:?} body=${body:?}
  linear issues create "$title" --team ENG --project "$OGHAM" \
    --labels "$labels" --priority "$prio" --description "$body" 2>&1 \
    | tee -a "$OUT" | grep '"identifier"'
}
title="[v0.16] Foo" labels="Feature" prio=2 body="..." mk
title="[v0.16] Bar" labels="Improvement" prio=3 body="..." mk
grep '"error"' "$OUT" || echo "clean"
```

> Named variables rather than `$1`-`$4` on purpose. A skill's markdown is rendered into the agent's context with its arguments interpolated, so bare positional parameters inside a fenced block get **silently replaced by whatever the caller passed as skill args** — an agent then copies a recipe that creates an issue titled `an` with the label `issue`. Observed on 2026-08-05. Keep shell examples in this file positional-free.

**Backfill a milestone across a range of issues**:

```bash
V16_MS=00000000-ms02-0000-0000-000000000000
for n in 109 110 111 112 113; do
  linear issues update "$TEAM-$n" --project-milestone "$V16_MS" | grep '"identifier"'
done
```

**Wire blocked-by** — one call per dependency, `--blocked-by` on `issues update`:

```bash
blocker=121
for dep in 109 110 111 112 113 114 115 116 117 118 119 120 122 123; do
  linear issues update "$TEAM-$blocker" --blocked-by "$TEAM-$dep" 2>&1 | grep '"error"'
done
```

**Filter open issues in a release**:

```bash
linear issues list --project "$OGHAM" --milestone v0.16 --limit 50 | \
  jq -r '.nodes[] | "\(.identifier)  \(.state.name)  \(.title)"'
```

**Clean up a stray test issue** (archive over delete — leaves history; both need `admin` scope):

```bash
linear issues archive ENG-102
```
