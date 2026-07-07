# excalidraw-diagram v2 — offline, deterministic render engine

**Date:** 2026-07-07
**Status:** Approved design, pending implementation
**Scope:** Render pipeline + packaging only. The diagram-authoring methodology is unchanged.

## Problem

The `excalidraw-diagram` skill's design methodology works well — hand-authored
`.excalidraw` JSON produces good diagrams. All observed friction lived in the
**render step**, where the agent renders JSON → PNG to self-validate.

Root cause: `references/render_template.html` imports Excalidraw from an
**unpinned CDN** at render time:

```html
import { exportToSvg } from "https://esm.sh/@excalidraw/excalidraw?bundle";
```

This is a runtime network dependency on esm.sh's dependency resolution. When
esm.sh served a 404 for a transitive dependency
(`@braintree/sanitize-url@6.0.2/.../constants.mjs`), the module graph never
finished loading, `window.__moduleReady` never flipped to `true`, and the
renderer hung until a 30s Playwright `TimeoutError` — with no indication of the
real cause.

Documented cost of a single failure: ~6 wasted tool calls (two dead renders, a
connectivity check, a console-probe script, a version-probe across three pinned
versions, and writing a one-off workaround harness) — none related to the actual
diagram.

### Failure modes to eliminate
1. **Opaque hang** — a 30s timeout on `__moduleReady` that reports nothing about *why*.
2. **CDN dependency drift** — unpinned transitive deps that move under the skill.
3. **Network coupling** — fails offline, in sandboxes, and during esm.sh outages.
4. **Version trial-and-error** — no known-good pin; every failure re-opens the question.
5. **Packaging bloat** — a full Playwright/Chromium `.venv` (~850k lines) committed into the skill.

## What is explicitly out of scope

- The diagram methodology in `SKILL.md` (patterns, isomorphism/education tests,
  multi-zoom, evidence artifacts, container discipline). It is the valuable part
  and is **not** modified beyond render/setup instructions.
- `references/color-palette.md`, `element-templates.md`, `json-schema.md` — unchanged.
- No switch to jsdom-based rendering or the official Excalidraw MCP. Both
  reintroduce the network/rendering fragility this design removes. Excalidraw's
  `exportToSvg` genuinely needs a DOM/canvas, so a real headless browser
  (Playwright + Chromium) remains the correct engine — the bug was never the
  browser, it was the *unpinned CDN import*.

## Design

### Key reframe: vendoring is a one-time authoring task, not per-user setup

The self-contained bundle is produced **once, at authoring time**, and committed
to the repo. End users never fetch or bundle anything. Their setup stays
`uv sync` + `playwright install chromium` — no Node, no npm, no network at render time.

### Component 1 — Vendored, pinned Excalidraw bundle (removes root cause)

- **Artifact:** `references/vendor/excalidraw.mjs` — a single self-contained ESM
  module exporting `exportToSvg`, with **all** dependencies inlined. Committed to the repo.
- **Pinned version:** `@excalidraw/excalidraw@0.18.1` (latest stable). If 0.18.1
  fails the authoring-time render test, fall back to `0.18.0` (confirmed-good).
  The chosen version is recorded in `references/vendor/VERSION`.
- **Production recipe (authoring-time only):** `references/scripts/vendor.sh`
  runs `npm install @excalidraw/excalidraw@<pin>` into a temp dir and bundles
  with `esbuild` (format=esm, bundle, minify) to produce a single offline
  `excalidraw.mjs`. Documented so a version bump is deliberate and reproducible.
- **Acceptance for the artifact:** rendering a known diagram against the vendored
  file issues **zero** network requests and produces a correct PNG.

### Component 2 — Template loads the local bundle

`references/render_template.html` imports the vendored bundle instead of the CDN:

```diff
-  import { exportToSvg } from "https://esm.sh/@excalidraw/excalidraw?bundle";
+  import { exportToSvg } from "./vendor/excalidraw.mjs";
```

and sets `window.EXCALIDRAW_ASSET_PATH` to the local `vendor/` URL so Excalidraw
resolves its fonts (referenced by relative `./fonts/...` paths) locally.

**Implementation note (deviation from the initial `file://` plan):** headless
Chromium blocks `fetch()` of `file://` resources, and Excalidraw fetches font
files at export time to embed them — under `file://` the fonts silently fail and
text falls back to a system font. The renderer therefore serves `references/`
over a **loopback HTTP server** (`127.0.0.1`, random port) and loads the template
via `http://127.0.0.1:<port>/render_template.html`. This is still fully offline
(no external network) but sidesteps the `file://` fetch restriction. Verified:
a render issues only loopback requests, zero external.

### Component 3 — Self-diagnosing renderer (removes opaque hang)

Harden `references/render_excalidraw.py`:

- **Before** `page.goto(...)`, attach listeners that accumulate:
  - `page.on("console", ...)` → collect `msg.type()` + `msg.text()` for `error`/`warning`.
  - `page.on("requestfailed", ...)` → collect `request.url()` + failure text.
  - `page.on("pageerror", ...)` → collect uncaught exceptions.
- **Reduce** the `__moduleReady` wait from 30s → 8s.
- **On timeout (or module error):** print the collected console errors, page
  errors, and failed requests to stderr, then exit non-zero. The real cause
  surfaces on the *first* failure — no separate probe script needed.
- **Network is now a red flag:** because the bundle is fully local, any
  `requestfailed` (or any external request at all) indicates the bundle wasn't
  fully inlined; surface it explicitly in the error output.
- No change to bounding-box, viewport-sizing, or screenshot logic — those work.

### Component 4 — Packaging / streamlining

- **Stop committing `.venv`.** Add `references/.venv/` to the skill's
  `.gitignore`. Setup remains, and is the only setup:
  ```bash
  cd .claude/skills/excalidraw-diagram/references
  uv sync
  uv run playwright install chromium
  ```
- **Repo home + live install.** The skill is added to the `claude-skills`
  repo at `excalidraw-diagram/` (versioned alongside the other skills) and
  installed to `~/.agents/skills/excalidraw-diagram` via a **symlink**, so the
  live copy tracks the repo. (The current `~/.agents/skills/excalidraw-diagram`
  is a standalone, untracked copy; it is replaced by the symlink.)
- **README** updated to describe offline rendering, the no-committed-venv setup,
  and the deliberate re-vendor procedure for version bumps.

### Follow-ups (out of scope here — separate spec + plan each)

Surfaced while surveying the `github/awesome-copilot`
`excalidraw-diagram-generator` skill (community-curated, **not** an official
Excalidraw project). Deferred to keep this change scoped to the render fix.

**1. Icon-library ingestion.** Scripts that split an official Excalidraw
`.excalidrawlib` (AWS/GCP/Azure/K8s) into per-icon JSON + a lightweight
`reference.md`, then place real cloud icons into a diagram deterministically —
so 200–1000-line icon JSON never enters the agent's context. Materially improves
architecture diagrams. Highest-value follow-up.

**2. Methodology-exemplar references (primary template idea).** A small set of
*worked examples of this skill's own patterns done well* — a strong fan-out, a
timeline, an evidence-artifact code snippet — each committed **with its rendered
PNG** (cheap now that rendering is offline). Teaches the agent what "good" looks
like in this skill's voice (JSON *and* the visual result), reinforcing "argue,
not display" rather than diluting it. Read on demand (progressive disclosure) so
the large JSON never sits in context unless that pattern is being drawn.

**3. Convention-bound type scaffolds (selective).** Reference `.excalidraw`
scaffolds for the diagram types with an established visual grammar readers
expect: **sequence, ER, class, swimlane**. For these, following convention is
correctness, not laziness. Explicitly framed in SKILL.md as "scaffolds you still
apply the methodology on top of," never fill-in-the-blank. **Deliberately
exclude** the generic flowchart / mind map / relationship templates from
awesome-copilot — those are exactly where the pattern-driven methodology should
take over, and importing them would pull output toward generic card grids.

The awesome-copilot `add-arrow.py` / `add-icon-to-diagram.py` mutation scripts
are lower value given this skill's hand-authored, methodology-driven flow —
reconsider only if icon ingestion (follow-up 1) needs deterministic placement.

## Data flow (render, after)

```
.excalidraw JSON
      │
      ▼
render_excalidraw.py  ──(validate JSON, compute bbox)
      │  launches Playwright + headless Chromium
      ▼
render_template.html  ──(file://)
      │  import ./vendor/excalidraw.mjs   ← LOCAL, pinned, zero network
      ▼
exportToSvg(elements, appState, files)
      │
      ▼
screenshot #root svg  ──►  PNG next to the .excalidraw file
```

Any deviation (module never ready, a network request, a page error) is captured
and printed with its real cause, then the process exits non-zero within ~8s.

## Testing / acceptance

1. **Offline render:** with networking disabled, `render_excalidraw.py` renders a
   sample diagram to a correct PNG. (Proves the network dependency is gone.)
2. **Zero-network assertion:** a render issues no external requests
   (`requestfailed` count and external-request count both zero).
3. **Diagnostic failure:** temporarily point the import at a missing file →
   the renderer exits non-zero in ≤ ~8s and prints the failed import, not a bare
   `TimeoutError`.
4. **Clean checkout setup:** from a fresh clone (no `.venv`), `uv sync` +
   `playwright install chromium` + render succeeds.
5. **Re-vendor reproducibility:** `scripts/vendor.sh` regenerates a working
   `vendor/excalidraw.mjs` for the pinned version.

## Risks / mitigations

- **Bundle doesn't fully inline (esbuild leaves an external import).** Mitigation:
  the zero-network assertion (test 2) catches it at authoring time; esbuild
  `--bundle` inlines all resolvable deps, and `exportToSvg` has no runtime
  browser-external fetches.
- **0.18.1 render regression.** Mitigation: authoring-time render test; fall back
  to 0.18.0, which is confirmed-good.
- **Bundle size in the repo.** Acceptable: one minified `.mjs` (order of a few
  hundred KB to ~1–2 MB) replaces a committed multi-hundred-thousand-line
  `.venv` — a net reduction in tracked bloat.
