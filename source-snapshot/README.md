# source-snapshot

Separate retrieval from consumption. Fetch an external source **once**, normalise it, and
commit it as a pinned, provenance-stamped artifact that agents read instead of re-fetching.

Part of [claude-skills](../README.md).

## What it does

Same input → same artifact → same downstream behaviour. Live `WebFetch` on every run is
the non-determinism this removes.

```bash
srcsnap plan --content-type prose --format json          # what WOULD be used, no fetch
srcsnap run https://example.com/post --content-type prose --out snapshots/post.md
```

Two things make a snapshot worth more than a saved page:

**Provenance.** Every artifact carries `source_url`, `retrieved_at`, which extractor
produced it, a `content_sha256` of the normalised body, and a `pinned_version` for
versioned sources. Markdown gets YAML front matter; JSON gets the same fields under
`_provenance`. Without that block you cannot tell what a file is or when it drifted.

**The diff is the changelog.** Refresh on a cadence, commit, and `git diff` shows you
exactly how upstream moved. That is the mechanism — it turns silent drift into a review.

### Choosing the extractor

| Content | Use | Why |
|---|---|---|
| Article, blog, prose | Defuddle → Readability → markitdown | Strips nav, ads and chrome; small and stable |
| Reference docs, API pages, tables, specs | [`markdown-converter`](../markdown-converter) (markitdown) | Structure is the part you'll cite — don't flatten it |
| APIs, registries, anything with a schema | Request JSON/YAML, store **as data** | A snapshot checked by key beats a page matched by string |

markitdown *can* fetch a URL, but it does a faithful **full-page** conversion — nav,
sidebar and footer come through. For a prose article you want the boilerplate gone, which
is the only reason Defuddle is preferred.

`scripts/snapshot.py` (stdlib-only) detects which extractors are actually installed, picks
one by content type, falls back when the preferred one is missing, and **fails cleanly
with exit 1 and a structured error when none can handle the type** — it never crashes or
fabricates. `srcsnap --have markitdown plan …` forces availability so you can preview a
leaner machine or test the fallback path.

## What it does NOT do

- **It does not decide what is true.** A snapshot is a faithful record of what a source
  said at a time. If upstream was wrong, the snapshot preserves the error.
- **It does not refresh itself.** Staleness is surfaced, never silently repaired — it will
  not fall back to a live fetch behind your back, because that would reintroduce exactly
  the non-determinism it exists to remove.
- **It does not invent provenance.** `retrieved_at` is passed in, never generated
  mid-run. A fabricated timestamp makes an artifact worse than no artifact.
- **It is not for one-off lookups.** Throwaway exploration should just fetch live. The
  signal to snapshot is finding yourself fetching the same URL across runs.
- **It does not bypass access controls**, paywalls or robots directives.

## Requirements

- `uv` preferred; the producer is stdlib-only so `python3` works identically.
- At least one extractor for the content type you want. markitdown is the most reliable
  fallback and needs no local install (`uvx 'markitdown[all]'`).
- Optional but recommended: `pnpm add -g defuddle` once, so it becomes a PATH binary and
  stops re-resolving per run. Use the `defuddle` package — `defuddle-cli` is deprecated
  and merged into it. Never hand-write an `npx …@latest` call: it forces a reinstall and
  is blocked outright in pnpm-enforced environments.

Run the script by **absolute path**; a bare `snapshot.py` will not resolve from whatever
repo you are working in. [`SKILL.md`](./SKILL.md) has the `srcsnap` function recipe.

## Anti-patterns

Re-fetching the same source live every run. Storing raw HTML when you needed one section.
Snapshots with no provenance. Flattening tables or schemas to prose and then matching them
by string. Inventing a `retrieved_at`.

## How it fits

Snapshots are the highest-tier source for fact-checking: a committed
`registry-snapshot.json` can be cited by key, deterministically and offline, instead of
hitting the network and hoping. [`terraform-registry`](../terraform-registry) is a
concrete producer — its cached, provenance-stamped payloads *are* snapshots.

Resilience is covered by `evals/` — the no-markitdown / no-defuddle matrix. Run
`cd evals && uv run python grade.py`.
