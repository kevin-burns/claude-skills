---
name: source-snapshot
description: Playbook for getting external data into the repo deterministically — fetch a web page, doc, or API/registry result once, extract and normalize it, and cache it as a pinned, provenance-stamped artifact that agents read instead of re-fetching live. Use when you need facts an LLM or agent will rely on (docs, library/API behavior, Terraform/provider registry data, prices, schemas) to be reproducible and offline-readable rather than varying per run. Also use when deciding whether to snapshot vs. fetch live, and which extractor to use for a given source. Pairs with fact-verifier (snapshots become its tier-1 sources) and markdown-converter.
license: MIT
---

# Source Snapshot

The core move: **separate retrieval from consumption.** Retrieve once,
deterministically, into a pinned artifact with provenance. Then agents and the LLM read
the *artifact*, never the live source. Same input → same artifact → same downstream
behavior. Live `WebFetch`/MCP on every run is the non-determinism you're removing.

## When to snapshot vs. fetch live

| Situation | Do |
|---|---|
| Fact gates a decision **and** is reused (docs, registry data, schemas, versions) | **Snapshot** to a pinned artifact, commit it |
| One-off exploration, throwaway lookup | Fetch live (`WebFetch`, MCP, `c7search`) — no artifact |
| Value changes the build output if it drifts (IaC generation, pinned deps) | **Snapshot + pin a version**; refresh on a cadence, never live-per-run |

If you find yourself fetching the same URL/endpoint across runs, that's the signal to
snapshot it.

## Choose the extractor by content type

- **Article / blog / prose** → main-content extractor (Defuddle, or Mozilla Readability)
  → Markdown. Strips nav/ads/chrome; the cleaned result is small and stable. Defuddle
  is often *not* a PATH binary — the npm package is **`defuddle`** (the old `defuddle-cli`
  is deprecated, "merged into defuddle"; same `parse … --md` interface). The producer
  resolves a runner automatically (installed `defuddle` binary → `pnpm dlx defuddle` →
  `bunx` → `npx defuddle`) and never pins `@latest`, so a cached package is reused instead
  of re-downloaded. If no prose extractor is available, it falls back to markitdown.
  **Don't hand-write an `npx …@latest` call** — that forces a reinstall and is blocked
  outright in pnpm-enforced environments.
- **Why not just markitdown for an article?** markitdown *can* fetch a URL — but it does a
  **faithful full-page** HTML→Markdown conversion (it only drops `<script>`/`<style>`; nav,
  sidebar, and footer chrome come through). For a prose article you want the boilerplate
  *gone*, which is exactly what a main-content extractor does. That's the only reason
  defuddle is preferred here — not any inability of markitdown to read web pages.
- **Reference docs, API pages, tables, specs** → the `markdown-converter` skill
  (`markitdown`). Structure — headings, tables, links — is the part you'll cite, so
  preserve it rather than flattening to prose.
- **APIs / registries / anything with a schema** → request structured output (JSON/YAML)
  and store it **as data**, not prose. A `registry-snapshot.json` the verifier checks by
  key beats a page it matches by string. Prefer the source's cached/offline mode (e.g. a
  cached provider schema) over a live call where one exists.

## The procedure

1. **Fetch** the source (record the exact URL/endpoint + the time, from `args` — the
   clock is unavailable mid-run, so pass timestamps in).
2. **Extract / normalize** with the right extractor for the type (above).
3. **Write a provenance header**, then the content, to a stable path. Name the file so
   the same source maps to the same path (slug or content hash).
4. **Commit** the artifact. Review changes with `git diff` — a snapshot diff is how you
   *see* upstream drift.

### Provenance header (every snapshot)

For Markdown artifacts, a YAML front-matter block:

```yaml
---
source_url: https://...
retrieved_at: 2026-06-11T00:00:00Z   # passed in; do not invent
extractor: markitdown 0.x | defuddle | readability
content_sha256: <hash of the normalized body>
pinned_version: "1.2.3"              # for versioned sources (registry, package)
---
```

For JSON artifacts, the same fields under a top-level `"_provenance"` key. Provenance is
what makes a snapshot auditable and a citation trustworthy.

## Pinning & refresh

- **Pin a version** for versioned sources (a registry module, a package). The snapshot is
  tied to that version; bumping it is a deliberate, reviewable change.
- **Refresh on a cadence**, not per-run — a scheduled job or a `make refresh-*` target
  that re-snapshots and commits. The diff is the changelog.
- Never silently fall back to a live fetch when a snapshot is stale; surface staleness so
  the caller decides.

## Producer: `scripts/snapshot.py`

A stdlib-only helper that makes the routing above resilient — it detects which
extractors are actually installed, picks one by content type, **falls back when the
preferred is missing, and fails cleanly (exit 1, structured error) when none can handle
the type** — it never crashes or fabricates.

Run it by its **absolute path** — it lives in this skill's base directory (announced when the
skill loads, usually `~/.claude/skills/source-snapshot`); a bare `snapshot.py` won't resolve
from the repo you're working in. It's stdlib-only, so uv or python3 both work. Define a
`srcsnap` function at the start of each command block (a function passes arguments correctly
under bash and zsh — a plain `$VAR` doesn't word-split in zsh — and shell state doesn't persist
between tool calls, so re-declare it per block):

```bash
# uv is the preferred runner; resolve it even when it's not on a bare PATH (non-interactive
# shells often drop ~/.local/bin or the Homebrew bin -> `uv: command not found`):
UV="$(command -v uv || ls "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)"
srcsnap() { "$UV" run python "$HOME/.claude/skills/source-snapshot/scripts/snapshot.py" "$@"; }
# uv not installed? It's stdlib-only, so plain python3 works too:
#   srcsnap() { python3 "$HOME/.claude/skills/source-snapshot/scripts/snapshot.py" "$@"; }

# Decide what would be used, without fetching (deterministic):
srcsnap --format json plan --content-type prose
# Force availability for tests/CI (or to preview a leaner box):
srcsnap --have markitdown plan --content-type prose      # -> markitdown (fell back)
srcsnap --have none      plan --content-type prose      # -> exit 1, clean error

# Extract + write a provenance-stamped artifact:
srcsnap run https://example.com/post --content-type prose --out snapshots/post.md
srcsnap run report.pdf --content-type doc --out snapshots/report.md
```

Preference: `prose` → defuddle > readability > markitdown; `doc` → markitdown.
markitdown is the most reliable fallback (works via `uvx 'markitdown[all]'` even with no
local install). For defuddle the producer auto-resolves the runner and the verified CLI
shape (`defuddle parse {src} --md`); you only need an env override for a custom install or
a different prose tool (`{src}` = source slot):

```bash
# Usually unnecessary — the producer already finds defuddle. Override only for a custom path:
export SNAPSHOT_DEFUDDLE_CMD="defuddle parse {src} --md"
export SNAPSHOT_READABILITY_CMD="readable {src}"
```

**Tip — kill the startup friction for good:** install defuddle once so it's a PATH binary
and never re-resolves: `pnpm add -g defuddle` (gives the `defuddle` command; use the
`defuddle` package, not the deprecated `defuddle-cli`). The producer then uses it directly;
no `dlx`/`npx`, no per-run download.

Resilience is covered by `evals/` (the no-markitdown / no-defuddle matrix) — run
`cd evals && uv run python grade.py`.

## How this feeds the fleet

Snapshots are `fact-verifier`'s **tier-1 sources**: a committed `registry-snapshot.json`
or cached doc lets it cite `snapshot.json:line` deterministically and offline, instead of
hitting the network and hoping. Build the retriever once; reuse the artifact across many
agent runs. See `docs/agent-fleet-architecture.md`.

## Anti-patterns

- Re-fetching the same source live on every run (non-deterministic, slow, rate-limited).
- Storing raw HTML or a whole noisy page when you needed one section.
- Snapshots with no provenance — you can't tell what they are or when they drifted.
- Flattening structured data (tables, schemas) to prose, then trying to match it by string.
- Inventing a `retrieved_at` or a CLI invocation — pass timestamps in; verify commands.
