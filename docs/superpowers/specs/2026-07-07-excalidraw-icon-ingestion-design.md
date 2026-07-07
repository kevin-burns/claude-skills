# excalidraw-diagram: icon-library ingestion

**Date:** 2026-07-07
**Status:** Approved design, pending implementation
**Depends on:** the offline render engine (shipped) — placed icons are validated
with the existing `render_excalidraw.py` loop.
**Scope:** Follow-up #1 from `2026-07-07-excalidraw-offline-render-design.md`.

## Problem

The skill draws cloud/service components as basic shapes. Real architecture
diagrams want the actual vendor icons (AWS/Azure/GCP/K8s). Excalidraw ships those
as `.excalidrawlib` files, but each icon is a 200–1000-line group of elements.
Two problems if the agent handles them directly:

1. **Context bloat** — reading several icon JSONs to hand-place them burns a huge
   amount of the agent's context for pure boilerplate.
2. **ID collisions & broken groups** — copying icon elements verbatim reuses
   their element IDs and `groupIds`; place two of the same icon and IDs clash,
   groups merge, `boundElements` point at the wrong elements.

The fix is deterministic tooling: ingest a library once into per-icon files + a
lightweight index the agent reads, and a placement script that offsets, re-IDs,
and appends an icon without the JSON ever entering context.

## Decisions (locked)

- **Provider-agnostic.** Works with any `.excalidrawlib` (AWS/Azure/GCP/K8s/
  generic). No hardcoded default library.
- **Scope = split + place.** No scripted arrow-adder — the skill hand-authors
  connectors well and the render loop validates them; a scripted placer for
  arrows adds surface for little gain.
- **Our own scripts**, stdlib-only, run via `uv run`, matching this repo's
  conventions (absolute-path invocation, clear summaries). The approach is
  credited to `github/awesome-copilot` (MIT) in the skill's Provenance note.
- **No redistribution of vendor icon art.** `references/libraries/` is
  gitignored; users supply their own `.excalidrawlib` under that set's license.
- **`--scale` is best-effort in v1**, not load-bearing.

## Out of scope

- Scripted arrow/connector insertion (hand-authored per methodology).
- Shipping real cloud-icon example diagrams (would embed licensed vendor art).
- Auto-layout of icons. The agent positions them; the render loop catches
  spacing problems.
- Modifying the diagram methodology or render engine.

## Design

### File layout (additions)

```
excalidraw-diagram/references/
  scripts/
    split_library.py     # NEW: .excalidrawlib -> per-icon JSON + reference.md
    place_icon.py         # NEW: deterministic icon placement into a diagram
    vendor.sh, build.mjs  # existing (render engine)
  libraries/              # NEW, gitignored: user drops <set>/<set>.excalidrawlib
    README.md             # committed: how to add a library (the only tracked file)
```

### Component 1 — `split_library.py`

Ingest a library into a form the agent can browse cheaply.

- **Input:** path to a `.excalidrawlib` file, or a directory containing exactly
  one. Validate `type == "excalidrawlib"` and a non-empty `libraryItems` array;
  clear error otherwise.
- **Per item:** derive a sanitized filename from `item.name` (spaces→`-`, strip
  non-`[\w.-]`, collapse repeats). Resolve collisions with a numeric suffix.
  Write the full item to `<library-dir>/icons/<name>.json`.
- **Index:** write `<library-dir>/reference.md` — a table of
  `name | icons/<file>.json | W×H` (bounding-box size from the item's elements).
  The size column lets the agent plan spacing without opening any icon JSON.
- **Files:** if the library carries embedded image data (raster icons), preserve
  each item's associated `files` entries in its per-icon JSON so placement can
  merge them later (see Component 2).
- **Output:** stdlib-only; prints a summary (N icons, output paths).

### Component 2 — `place_icon.py`

Append one icon to a diagram deterministically, JSON never entering context.

- **Input:** `--diagram <path>`, the icon as either `--icon <name> --library
  <dir>` (looked up via `icons/<sanitized>.json`) or `--icon-json <path>`;
  `--x <n> --y <n>` target position; optional `--label <text>`,
  `--scale <f>` (default 1.0), `--anchor top-left|center` (default `top-left`).
- **Transform (pure, deterministic):**
  1. Read the icon's `elements` (and any `files`).
  2. Compute the element bounding box.
  3. Compute offset so the bbox's anchor lands on `(x, y)`.
  4. Build an `old_id → new_id` map (fresh 16-hex IDs) covering element IDs and
     every `groupId`. Rewrite `groupIds`, `boundElements[].id`,
     `containerId`, and arrow `startBinding/endBinding.elementId` through the map
     so groups/bindings stay internally consistent and never collide with the
     diagram's existing elements.
  5. Apply offset (and `--scale`, best-effort: multiply `x/y/width/height`,
     `points`, `fontSize`; leave `roundness` type flags alone) to each element.
  6. If `--label`, append one free-floating `text` element centered under the
     icon, using `fontFamily: 3` and a palette detail color.
- **Merge:** append transformed elements to the diagram's `elements`; merge any
  icon `files` into the diagram's `files` (new fileIds if needed) so image icons
  render offline.
- **Write:** save the updated diagram; print a summary (icon, final bbox, element
  count added). Never render — that's the existing loop's job.

### Component 3 — SKILL.md integration

New section "Using icons in architecture diagrams":

- **When:** technical architecture diagrams for cloud/infra — icons replace
  generic rectangles for real services. Not for conceptual/abstract diagrams.
- **Workflow:** confirm a library exists under `references/libraries/<set>/` (if
  not, point the user to the setup flow) → read only that set's `reference.md`
  → `place_icon.py` per service → **hand-author connectors, labels, evidence
  artifacts** per the methodology → run the render→view→fix loop, fixing spacing.
- **Framing:** icons are the *concrete detail layer*. The structure, flow, and
  visual argument remain the agent's job; dropping icons in a grid is not a
  diagram (ties back to "argue, not display").
- Points to `references/libraries/README.md` for the one-time setup.

### Component 4 — setup + packaging

- `references/libraries/README.md` (committed): download a `.excalidrawlib` from
  https://libraries.excalidraw.com/, put it at
  `references/libraries/<set>/<set>.excalidrawlib`, run
  `uv run python ../scripts/split_library.py <set>/`. Notes the licensing caveat.
- `.gitignore`: ignore `references/libraries/*` but keep
  `references/libraries/README.md` tracked.
- README + SKILL.md Provenance note updated to credit the awesome-copilot
  approach (MIT) alongside the existing Excalidraw credit.

## Testing / acceptance

A small **synthetic** `.excalidrawlib` fixture (authored by us, not vendor art)
with: (a) a vector icon = a few grouped shapes, (b) a second vector icon, (c) one
**image-based** icon referencing a `files` entry. Used from scratch, not
committed to the skill.

1. **Split:** `split_library.py` produces one `icons/*.json` per item, a
   `reference.md` with correct `W×H`, and preserves `files` for the image icon.
2. **Place + no collision:** place the *same* icon twice into a diagram; assert
   all element IDs and groupIds are unique across the result, and each icon's
   internal groups/bindings still resolve (no cross-contamination).
3. **Image icon renders:** place the image-based icon; the merged `files` let the
   existing `render_excalidraw.py` render it offline (zero external requests).
4. **Label:** `--label` adds exactly one caption element under the icon.
5. **Render-validate end to end:** a diagram with two placed icons + a
   hand-authored connector renders to a correct PNG via the existing loop.

## Risks / mitigations

- **`--scale` distorts complex icons** (stroke widths, roundness). Mitigation:
  documented best-effort, default 1.0; the render loop reveals distortion.
- **Library uses an unexpected item shape** (e.g., elements nested differently
  across `.excalidrawlib` versions). Mitigation: validate structure and fail with
  a clear message naming the offending item, rather than producing broken output.
- **Image icons with external image URLs** (not embedded data). Mitigation:
  detect and warn — offline rendering needs embedded data; such libraries aren't
  supported for offline render.

## Follow-ups (not now)

Remaining from the parent spec: methodology-exemplar single-pattern references,
and the sequence/ER/class/swimlane convention scaffolds.
