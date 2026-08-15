#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["jinja2>=3.1"]
# ///
"""Render a Jinja2 HTML template against a JSON context into a single HTML file.

Generic, project-agnostic half of the report-builder pattern: prep code produces a
JSON context, this renders it. Autoescape is ON and undefined variables are an error,
so template bugs fail loudly instead of emitting blank/wrong output.

Usage:
    uv run render.py --template report.html.j2 --data context.json --out report.html
    uv run render.py --template report.html.j2 --data context.json --out report.html \\
        --title "Q2 Cost Report"

The context JSON is passed to the template as top-level variables. `--title`, if given,
overrides/sets `title` in the context. Use `{{ value | tojson }}` in the template to hand
data to JavaScript safely.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


def render(template_path: Path, context: dict, *, title: str | None) -> str:
    if title is not None:
        context = {**context, "title": title}
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(
            enabled_extensions=("html", "htm", "xml", "j2"), default_for_string=True
        ),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_path.name)
    return template.render(**context)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--template",
        required=True,
        type=Path,
        help="Path to the Jinja2 template (e.g. report.html.j2)",
    )
    parser.add_argument(
        "--data", required=True, type=Path, help="Path to the JSON context file"
    )
    parser.add_argument("--out", required=True, type=Path, help="Output HTML path")
    parser.add_argument(
        "--title", default=None, help="Optional title; overrides 'title' in the context"
    )
    args = parser.parse_args(argv)

    if not args.template.is_file():
        print(f"error: template not found: {args.template}", file=sys.stderr)
        return 2
    if not args.data.is_file():
        print(f"error: data file not found: {args.data}", file=sys.stderr)
        return 2

    try:
        context = json.loads(args.data.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: --data is not valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(context, dict):
        print(
            "error: --data must be a JSON object (the template context)",
            file=sys.stderr,
        )
        return 2

    try:
        html = render(args.template, context, title=args.title)
    except Exception as exc:  # surface template errors (incl. StrictUndefined) clearly
        print(f"error: render failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"wrote {args.out} ({len(html):,} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
