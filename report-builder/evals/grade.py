#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Grade report-builder eval runs by inspecting the produced HTML.

Usage:
    uv run grade.py <iteration-dir>
    # default: ../../report-builder-workspace/iteration-1

For each eval-<id>/<config>/outputs/*.html it checks objective properties and writes
grading.json into each run dir, then prints a pass-rate table per config.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CONFIGS = ("with_skill", "without_skill")


def _html_text(outputs: Path) -> tuple[str, list[Path]]:
    files = sorted(outputs.glob("**/*.html"))
    text = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in files)
    return text, files


def check_eval0(text: str, files: list[Path]) -> list[dict]:
    low = text.lower()
    # A </script> breakout payload: if embedded raw (e.g. as a JS string literal inside an
    # inline <script>, the common hand-rolled approach), the </script> closes the tag early
    # and the trailing <img onerror> becomes live HTML → XSS. Safe handling (Jinja2
    # autoescape / | tojson) escapes it so this exact raw sequence never appears.
    payload = "</script><img src=x onerror=alert(1)>"
    return [
        {"text": "produces at least one .html file", "passed": len(files) >= 1,
         "evidence": f"{len(files)} html file(s)"},
        {"text": "embeds a chart (canvas/chart.js/plotly)",
         "passed": ("<canvas" in low) or ("chart.js" in low) or ("chart.umd" in low) or ("plotly" in low),
         "evidence": "chart marker present" if "<canvas" in low or "chart" in low or "plotly" in low else "none found"},
        {"text": "includes a data table", "passed": "<table" in low,
         "evidence": "<table> present" if "<table" in low else "no table"},
        {"text": "service names present (EC2, RDS, CloudFront)",
         "passed": all(s in text for s in ("EC2", "RDS", "CloudFront")),
         "evidence": "all present" if all(s in text for s in ("EC2", "RDS", "CloudFront")) else "missing some"},
        {"text": "</script>-breakout payload neutralized (no raw breakout in output)",
         "passed": payload not in text,
         "evidence": "raw breakout absent (escaped)" if payload not in text else "RAW </script> BREAKOUT PRESENT — XSS"},
    ]


def check_eval1(text: str, files: list[Path]) -> list[dict]:
    low = text.lower()
    return [
        {"text": "produces at least one .html file", "passed": len(files) >= 1,
         "evidence": f"{len(files)} html file(s)"},
        {"text": "embeds a chart",
         "passed": ("<canvas" in low) or ("chart" in low) or ("plotly" in low),
         "evidence": "chart marker present" if ("<canvas" in low or "chart" in low or "plotly" in low) else "none"},
        {"text": "suite names present (integration, contract)",
         "passed": ("integration" in low) and ("contract" in low),
         "evidence": "present" if ("integration" in low and "contract" in low) else "missing some"},
        {"text": "totals / summary present",
         "passed": any(w in low for w in ("total", "summary", "passed", "pass rate")),
         "evidence": "summary language present" if any(w in low for w in ("total", "summary", "passed")) else "none"},
    ]


CHECKERS = {0: check_eval0, 1: check_eval1}


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent
    default = here.parent.parent / "report-builder-workspace" / "iteration-1"
    iteration = Path(argv[1]).resolve() if len(argv) > 1 else default
    if not iteration.is_dir():
        print(f"error: iteration dir not found: {iteration}", file=sys.stderr)
        return 2

    totals = {c: [0, 0] for c in CONFIGS}  # passed, total
    print(f"\n== report-builder grading: {iteration} ==\n")
    for eval_dir in sorted(iteration.glob("eval-*")):
        eid = int(eval_dir.name.split("-")[1])
        checker = CHECKERS.get(eid)
        if not checker:
            continue
        for cfg in CONFIGS:
            outputs = eval_dir / cfg / "outputs"
            if not outputs.is_dir():
                continue
            text, files = _html_text(outputs)
            results = checker(text, files)
            grading = {"run_id": f"{eval_dir.name}-{cfg}", "expectations": results}
            (eval_dir / cfg / "grading.json").write_text(json.dumps(grading, indent=2))
            p = sum(1 for r in results if r["passed"])
            totals[cfg][0] += p
            totals[cfg][1] += len(results)
            print(f"{eval_dir.name:24} {cfg:14} {p}/{len(results)}")
            for r in results:
                print(f"    [{'PASS' if r['passed'] else 'FAIL'}] {r['text']} — {r['evidence']}")
        print()

    print("== totals ==")
    for cfg in CONFIGS:
        p, t = totals[cfg]
        rate = f"{100 * p / t:.0f}%" if t else "n/a"
        print(f"  {cfg:14} {p}/{t}  ({rate})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
