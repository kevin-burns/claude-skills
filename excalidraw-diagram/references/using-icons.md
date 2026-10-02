# Icons in architecture diagrams

Linked from `SKILL.md`. Read before placing any service icon.

For technical **cloud/infra architecture** diagrams, you can place real service icons (AWS, Azure, GCP, K8s) instead of generic rectangles. Icons are the *concrete detail layer* — the structure, flow, and visual argument are still yours to author (this is not license to drop icons in a uniform grid; that's "display", not "argue").

**Only when a library is installed.** Check `references/libraries/` for a `<set>/reference.md`. If none exists, tell the user how to add one (see `references/libraries/README.md`) — don't invent icons.

**Workflow:**
1. Read `references/libraries/<set>/reference.md` to pick icons by name. It lists each icon's size so you can plan spacing — **never open the icon JSON files**, that's what the placement script is for.
2. Place each icon deterministically (icon JSON never enters your context):
   ```bash
   cd references
   uv run python scripts/place_icon.py --diagram <file.excalidraw> \
       --icon "Lambda" --library libraries/aws --x 400 --y 240 [--label "Auth"]
   ```
   It offsets the icon to `(x, y)`, regenerates all ids/groups so repeated placements never collide, merges image data for raster icons, and appends to the diagram. Flags: `--anchor center`, `--scale <f>` (best-effort), `--label` (see below).
3. **Hand-author the connectors, labels, and evidence artifacts** yourself, per the methodology — icons don't make the argument, your layout does.
4. Run the normal **render → view → fix** loop. Icon spacing/overlap is caught there.

**Gotchas:**
- **Many cloud icons embed their own name text** — for those, omit `--label` or you'll double the caption. Render once to check.
- **Fidelity:** community icons are recognizable and correctly colored but hand-drawn style, not official-flat vendor icons. Set expectations accordingly.
- Sizes vary (~60–170px); read the size column and space accordingly.
