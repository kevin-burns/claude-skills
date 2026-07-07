"""Place one icon from a split library into an .excalidraw diagram.

Deterministic and context-free: the icon's (often huge) JSON never enters the
agent's context. Offsets the icon to a target position, regenerates every
element id and groupId so repeated placements never collide, keeps internal
groups/bindings consistent, merges any embedded image files, and optionally adds
a caption. It never renders — run the diagram through `render_excalidraw.py`.

Usage:
    uv run python place_icon.py --diagram d.excalidraw \\
        (--icon "EC2" --library <lib-dir> | --icon-json path.json) \\
        --x 400 --y 300 [--label "Web Server"] [--scale 1.0] [--anchor top-left|center]

stdlib only.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import uuid
from pathlib import Path


def new_id() -> str:
    return uuid.uuid4().hex[:16]


def load_icon(args: argparse.Namespace) -> dict:
    """Return the icon record {name, elements, files?} from --icon-json or --icon/--library."""
    if args.icon_json:
        p = args.icon_json
    else:
        if not args.icon or not args.library:
            sys.exit("ERROR: provide either --icon-json, or both --icon and --library")
        # Match split_library.py's sanitization for the primary filename.
        import re
        stem = re.sub(r"-+", "-", re.sub(r"[^\w.-]", "", args.icon.strip().replace(" ", "-"))).strip("-")
        p = args.library / "icons" / f"{stem}.json"
    if not p.exists():
        sys.exit(f"ERROR: icon file not found: {p}")
    record = json.loads(p.read_text(encoding="utf-8"))
    if "elements" not in record or not record["elements"]:
        sys.exit(f"ERROR: icon has no elements: {p}")
    return record


def icon_bounds(elements: list[dict]) -> tuple[float, float, float, float]:
    """(min_x, min_y, width, height) of the icon's live elements."""
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
        return (0.0, 0.0, 0.0, 0.0)
    min_x, min_y = min(xs0), min(ys0)
    return (min_x, min_y, max(xs1) - min_x, max(ys1) - min_y)


def transform(elements: list[dict], min_x: float, min_y: float,
              target_x: float, target_y: float, scale: float) -> list[dict]:
    """Copy icon elements with fresh ids, remapped groups/bindings, scaled + offset."""
    # Fresh id for every element id AND every groupId referenced.
    id_map: dict[str, str] = {}
    for el in elements:
        if "id" in el:
            id_map.setdefault(el["id"], new_id())
        for gid in el.get("groupIds") or []:
            id_map.setdefault(gid, new_id())

    def remap(old):
        return id_map.get(old, old)

    out: list[dict] = []
    for src in elements:
        el = copy.deepcopy(src)
        if "id" in el:
            el["id"] = remap(el["id"])
        if el.get("groupIds"):
            el["groupIds"] = [remap(g) for g in el["groupIds"]]
        if el.get("containerId"):
            el["containerId"] = remap(el["containerId"])
        if el.get("frameId"):
            el["frameId"] = remap(el["frameId"])
        if isinstance(el.get("boundElements"), list):
            el["boundElements"] = [
                {**b, "id": remap(b["id"])} if isinstance(b, dict) and "id" in b else b
                for b in el["boundElements"]
            ]
        for binding in ("startBinding", "endBinding"):
            b = el.get(binding)
            if isinstance(b, dict) and b.get("elementId"):
                b["elementId"] = remap(b["elementId"])

        # Geometry: scale about the icon's own origin, then translate to target.
        el["x"] = target_x + (el.get("x", 0) - min_x) * scale
        el["y"] = target_y + (el.get("y", 0) - min_y) * scale
        if "width" in el and el["width"] is not None:
            el["width"] = el["width"] * scale
        if "height" in el and el["height"] is not None:
            el["height"] = el["height"] * scale
        if "points" in el and isinstance(el["points"], list):
            el["points"] = [[px * scale, py * scale] for px, py in el["points"]]
        if scale != 1.0 and isinstance(el.get("fontSize"), (int, float)):
            el["fontSize"] = el["fontSize"] * scale
        out.append(el)
    return out


def make_label(text: str, center_x: float, top_y: float, icon_h: float) -> dict:
    """A free-floating caption centered under the icon (skill font + neutral color)."""
    font_size = 16
    width = max(len(text) * font_size * 0.6, 40)
    height = font_size * 1.25
    return {
        "type": "text", "id": new_id(),
        "x": center_x - width / 2, "y": top_y + icon_h + 10,
        "width": width, "height": height,
        "text": text, "originalText": text,
        "fontSize": font_size, "fontFamily": 3,
        "textAlign": "center", "verticalAlign": "top",
        "strokeColor": "#495057", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "angle": 0,
        "seed": int(uuid.uuid4().int % 2**31), "version": 1,
        "versionNonce": int(uuid.uuid4().int % 2**31), "isDeleted": False,
        "groupIds": [], "boundElements": None, "link": None, "locked": False,
        "containerId": None, "lineHeight": 1.25,
    }


def place(args: argparse.Namespace) -> None:
    diagram_path: Path = args.diagram
    if not diagram_path.exists():
        sys.exit(f"ERROR: diagram not found: {diagram_path}")
    diagram = json.loads(diagram_path.read_text(encoding="utf-8"))
    diagram.setdefault("elements", [])
    diagram.setdefault("files", {})

    record = load_icon(args)
    elements = record["elements"]
    min_x, min_y, w, h = icon_bounds(elements)
    sw, sh = w * args.scale, h * args.scale

    if args.anchor == "center":
        target_x, target_y = args.x - sw / 2, args.y - sh / 2
    else:
        target_x, target_y = args.x, args.y

    placed = transform(elements, min_x, min_y, target_x, target_y, args.scale)
    diagram["elements"].extend(placed)

    if args.label:
        diagram["elements"].append(make_label(args.label, target_x + sw / 2, target_y, sh))

    # Merge embedded image data (raster icons) so the diagram renders offline.
    if record.get("files"):
        diagram["files"].update(record["files"])

    diagram_path.write_text(json.dumps(diagram, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Placed '{record['name']}' at ({target_x:g}, {target_y:g}), "
          f"size {sw:g}×{sh:g}, +{len(placed) + (1 if args.label else 0)} elements")


def main() -> None:
    ap = argparse.ArgumentParser(description="Place a split-library icon into an .excalidraw diagram")
    ap.add_argument("--diagram", type=Path, required=True, help="Target .excalidraw file")
    ap.add_argument("--icon", help="Icon name (used with --library)")
    ap.add_argument("--library", type=Path, help="Split library directory (contains icons/)")
    ap.add_argument("--icon-json", type=Path, help="Direct path to a split icon JSON")
    ap.add_argument("--x", type=float, required=True, help="Target X")
    ap.add_argument("--y", type=float, required=True, help="Target Y")
    ap.add_argument("--label", help="Optional caption placed under the icon")
    ap.add_argument("--scale", type=float, default=1.0, help="Uniform scale (best-effort; default 1.0)")
    ap.add_argument("--anchor", choices=("top-left", "center"), default="top-left",
                    help="Whether (x, y) is the icon's top-left (default) or center")
    place(ap.parse_args())


if __name__ == "__main__":
    main()
