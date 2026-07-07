"""Split an Excalidraw library (.excalidrawlib) into per-icon JSON + an index.

Ingest a library once so the agent browses a lightweight `reference.md` (name →
file → size) and never loads 200–1000-line icon JSON into context. Pair with
`place_icon.py`, which places an icon into a diagram deterministically.

Usage:
    uv run python split_library.py <path-to-.excalidrawlib | dir-containing-one>

Output (written next to the library file):
    icons/<sanitized-name>.json   one per library item (elements + any files)
    reference.md                  a table of name | file | W×H

stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """Turn an icon name into a filesystem-safe stem (no extension)."""
    stem = name.strip().replace(" ", "-")
    stem = re.sub(r"[^\w.-]", "", stem)      # keep word chars, dot, hyphen
    stem = re.sub(r"-+", "-", stem).strip("-")
    return stem or "icon"


def find_library(path: Path) -> Path:
    """Resolve the .excalidrawlib file from a file or a directory path."""
    if path.is_file():
        return path
    if path.is_dir():
        libs = sorted(path.glob("*.excalidrawlib"))
        if not libs:
            sys.exit(f"ERROR: no .excalidrawlib file found in {path}")
        if len(libs) > 1:
            sys.exit(f"ERROR: multiple .excalidrawlib files in {path}; keep one or pass it directly")
        return libs[0]
    sys.exit(f"ERROR: path not found: {path}")


def element_bbox(elements: list[dict]) -> tuple[float, float]:
    """Return (width, height) of an icon's elements. (0, 0) if empty."""
    xs0, ys0, xs1, ys1 = [], [], [], []
    for el in elements:
        if el.get("isDeleted"):
            continue
        x, y = el.get("x", 0), el.get("y", 0)
        w, h = el.get("width", 0) or 0, el.get("height", 0) or 0
        if el.get("type") in ("arrow", "line") and "points" in el:
            for px, py in el["points"]:
                xs0.append(x + px); ys0.append(y + py)
                xs1.append(x + px); ys1.append(y + py)
        else:
            xs0.append(x); ys0.append(y)
            xs1.append(x + abs(w)); ys1.append(y + abs(h))
    if not xs0:
        return (0.0, 0.0)
    return (round(max(xs1) - min(xs0), 1), round(max(ys1) - min(ys0), 1))


def item_files(item: dict, top_files: dict) -> dict:
    """Collect embedded file data (raster icons) referenced by this item.

    Library formats vary: files may live on the item (`item['files']`) or at the
    top level of the .excalidrawlib. Pull whatever fileIds this item's image
    elements reference so the per-icon JSON is self-contained.
    """
    files: dict = {}
    available = {**(top_files or {}), **(item.get("files") or {})}
    if not available:
        return files
    for el in item.get("elements", []):
        fid = el.get("fileId")
        if fid and fid in available:
            files[fid] = available[fid]
    return files


def split(library_path: Path) -> None:
    data = json.loads(library_path.read_text(encoding="utf-8"))

    if data.get("type") != "excalidrawlib":
        sys.exit(f"ERROR: not an Excalidraw library (type={data.get('type')!r}) in {library_path.name}")
    items = data.get("libraryItems")
    if not isinstance(items, list) or not items:
        sys.exit(f"ERROR: no libraryItems in {library_path.name}")

    out_dir = library_path.parent
    icons_dir = out_dir / "icons"
    icons_dir.mkdir(exist_ok=True)
    top_files = data.get("files") or {}

    used_files: set[str] = set()
    rows: list[tuple[str, str, str]] = []

    for item in items:
        name = item.get("name") or "Unnamed"
        stem = sanitize_filename(name)
        # Resolve filename collisions against ALL prior filenames, case-insensitively
        # (a suffixed name like "EC2-2.json" must not clobber a real "EC2-2", and
        # "S3.json"/"s3.json" collide on case-insensitive filesystems like APFS).
        filename = f"{stem}.json"
        n = 1
        while filename.lower() in used_files:
            n += 1
            filename = f"{stem}-{n}.json"
        used_files.add(filename.lower())

        elements = item.get("elements", [])
        record = {"name": name, "elements": elements}
        files = item_files(item, top_files)
        if files:
            record["files"] = files

        (icons_dir / filename).write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        w, h = element_bbox(elements)
        rows.append((name, f"icons/{filename}", f"{w:g}×{h:g}"))

    rows.sort(key=lambda r: r[0].lower())
    lib_name = library_path.stem
    ref = [
        f"# {lib_name} — icon reference",
        "",
        f"{len(rows)} icons from `{library_path.name}`. "
        "Read this table to pick icons; place them with `place_icon.py` "
        "(do **not** paste icon JSON into context).",
        "",
        "| Icon | File | Size (W×H) |",
        "|------|------|------------|",
    ]
    ref += [f"| {name} | `{f}` | {size} |" for name, f, size in rows]
    ref.append("")
    (out_dir / "reference.md").write_text("\n".join(ref), encoding="utf-8")

    print(f"Split {len(rows)} icons from {library_path.name}")
    print(f"  icons:     {icons_dir}")
    print(f"  reference: {out_dir / 'reference.md'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Split a .excalidrawlib into per-icon JSON + reference.md")
    ap.add_argument("path", type=Path, help="Path to a .excalidrawlib file, or a directory containing exactly one")
    args = ap.parse_args()
    split(find_library(args.path))


if __name__ == "__main__":
    main()
