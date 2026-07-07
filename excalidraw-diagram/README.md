# Excalidraw Diagram Skill

A coding agent skill that generates beautiful and practical Excalidraw diagrams from natural language descriptions. Not just boxes-and-arrows - diagrams that **argue visually**.

Compatible with any coding agent that supports skills. For agents that read from `.claude/skills/` (like [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [OpenCode](https://github.com/nicepkg/OpenCode)), just drop it in and go.

## What Makes This Different

- **Diagrams that argue, not display.** Every shape/group of shapes mirrors the concept it represents — fan-outs for one-to-many, timelines for sequences, convergence for aggregation. No uniform card grids.
- **Evidence artifacts.** As an example, technical diagrams include real code snippets and actual JSON payloads.
- **Built-in visual validation.** A Playwright-based render pipeline lets the agent see its own output, catch layout issues (overlapping text, misaligned arrows, unbalanced spacing), and fix them in a loop before delivering.
- **Fully offline, deterministic rendering.** The Excalidraw engine and its fonts are vendored under `references/vendor/` and served over a loopback HTTP server — no CDN, no external network. A render can't break from dependency drift, a CDN outage, or a sandboxed network, and failures report the real cause instead of hanging.
- **Brand-customizable.** All colors and brand styles live in a single file (`references/color-palette.md`). Swap it out and every diagram follows your palette.

## Installation

Copy this skill directory into your project's `.claude/skills/` directory (or your agent's skills path):

```bash
cp -r excalidraw-diagram /path/to/.claude/skills/excalidraw-diagram
```

The design methodology in this skill began as a fork of [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill); the render engine has since been rebuilt to run fully offline (see below).

## Setup

The skill includes a render pipeline that lets the agent visually validate its diagrams. There are two ways to set it up:

**Option A: Ask your coding agent (easiest)**

Just tell your agent: *"Set up the Excalidraw diagram skill renderer by following the instructions in SKILL.md."* It will run the commands for you.

**Option B: Manual**

```bash
cd .claude/skills/excalidraw-diagram/references
uv sync
uv run playwright install chromium
```

That's the whole setup — the Excalidraw engine itself ships vendored in `references/vendor/`, so nothing is fetched from a CDN at render time.

## Usage

Ask your coding agent to create a diagram:

> "Create an Excalidraw diagram showing how the AG-UI protocol streams events from an AI agent to a frontend UI"

The skill handles the rest — concept mapping, layout, JSON generation, rendering, and visual validation.

## Customize Colors

Edit `references/color-palette.md` to match your brand. Everything else in the skill is universal design methodology.

## File Structure

```
excalidraw-diagram/
  SKILL.md                          # Design methodology + workflow
  references/
    color-palette.md                # Brand colors (edit this to customize)
    element-templates.md            # JSON templates for each element type
    json-schema.md                  # Excalidraw JSON format reference
    render_excalidraw.py            # Render .excalidraw to PNG (offline)
    render_template.html            # Browser template for rendering
    pyproject.toml                  # Python dependencies (playwright)
    vendor/                         # Pinned, offline Excalidraw engine + fonts
      excalidraw.mjs                #   self-contained exportToSvg bundle
      fonts/                        #   Latin font families
      VERSION                       #   pinned versions + provenance
    scripts/
      vendor.sh                     # Regenerate vendor/ on a version bump
      build.mjs                     # esbuild config used by vendor.sh
      split_library.py              # Ingest a .excalidrawlib → per-icon JSON + index
      place_icon.py                 # Deterministically place an icon into a diagram
    libraries/                      # User-supplied icon sets (gitignored except README)
      README.md                     #   how to add AWS/Azure/GCP/K8s icon libraries
```

## Cloud/architecture icons

For architecture diagrams you can place real service icons (AWS/Azure/GCP/K8s)
instead of generic shapes. Icon sets aren't bundled (they carry their own
licenses) — you add a `.excalidrawlib` and the skill ingests it. See
`references/libraries/README.md` for setup, and SKILL.md → "Using icons in
architecture diagrams" for the workflow. Icons are recognizable community
hand-drawn style (not official-flat vendor icons).

## Updating the Excalidraw version

The vendored engine is pinned (see `references/vendor/VERSION`) and committed, so
normal use never touches the network. To bump it deliberately:

```bash
cd .claude/skills/excalidraw-diagram/references
scripts/vendor.sh 0.18.1          # or any version; requires node + npm
```

Then render a test diagram, eyeball it (a new Excalidraw version can change
export behavior), update `vendor/VERSION`, and commit.
