# Icon libraries

Drop Excalidraw icon libraries here to use real cloud/service icons (AWS, Azure,
GCP, K8s, …) in architecture diagrams. **Nothing in this folder except this file
is committed** — icon art carries its own license, so you supply your own.

## Add a library (one-time per set)

1. Go to https://libraries.excalidraw.com/, find an icon set, and download its
   `.excalidrawlib` file.
2. Put it in its own subdirectory here, e.g.:
   ```
   references/libraries/aws/aws-architecture-icons.excalidrawlib
   ```
3. Split it into per-icon files + a browsable index:
   ```bash
   cd references
   uv run python scripts/split_library.py libraries/aws/
   ```
   This creates `libraries/aws/icons/*.json` and `libraries/aws/reference.md`.

## Use icons in a diagram

- Read `libraries/<set>/reference.md` to pick icons by name (it lists each
  icon's size — you never need to open the icon JSON).
- Place each with `scripts/place_icon.py` (see SKILL.md → "Using icons in
  architecture diagrams"). It offsets, re-IDs, and appends the icon
  deterministically; the icon JSON never enters your context.

## Notes

- **Fidelity:** these are community-authored, hand-drawn-style icons — recognizable
  and correctly colored, but not the official flat vendor icons. Good for
  Excalidraw diagrams; if you need pixel-official icons, this isn't that.
- **Self-labeled icons:** many cloud icons embed their own name text. For those,
  omit `place_icon.py --label` (it would double the caption).
- **Licensing:** each icon set is under its own license — don't redistribute the
  split output or committed diagrams containing it without checking.
