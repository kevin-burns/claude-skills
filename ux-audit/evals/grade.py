#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Grade ux-audit eval runs by keyword-scanning the produced findings.

Usage:
    uv run grade.py <iteration-dir>
    # default: ../../ux-audit-workspace/iteration-1

Reads every text/json/md output a run produced, lowercases it, and checks whether the
planted faults were caught and whether findings are structured (severity + a fix). Writes
grading.json per run and prints a pass-rate table. Keyword matching is deliberately
generous on *catching* a fault (so baselines get fair credit) and stricter on *structure*
(where the skill's rubric should show its value).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CONFIGS = ("with_skill", "with_skill_pw", "without_skill")
TEXT_EXT = (".json", ".md", ".txt", ".html", ".yaml", ".yml")


def _text(outputs: Path) -> str:
    parts = []
    for f in sorted(outputs.glob("**/*")):
        if f.is_file() and f.suffix.lower() in TEXT_EXT:
            parts.append(f.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts).lower()


def _has_any(text: str, *kw: str) -> bool:
    return any(k in text for k in kw)


def _structured(text: str) -> bool:
    has_sev = _has_any(text, "blocking", "major", "minor", "critical", "serious", "severity")
    has_fix = _has_any(text, "suggested_fix", "fix", "add ", "use ", "replace", "associate", "increase")
    return has_sev and has_fix


def _schema_ok(outputs: Path) -> tuple[bool, str]:
    """The skill defines a return envelope a fan-out merge depends on: a top-level object
    with a `summary` and a `findings` array whose items carry severity + a fix field. A bare
    list or ad-hoc field names (what a no-skill run tends to emit) fails this."""
    jsons = sorted(outputs.glob("**/*.json"))
    if not jsons:
        return False, "no json output"
    try:
        d = json.loads(jsons[0].read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return False, "invalid json"
    if not isinstance(d, dict):
        return False, "bare list, no envelope"
    if "findings" not in d or "summary" not in d:
        return False, f"missing envelope keys (has {sorted(d)})"
    findings = d.get("findings") or []
    if not findings or not isinstance(findings, list):
        return False, "no findings array"
    f0 = findings[0] if isinstance(findings[0], dict) else {}
    if "severity" not in f0 or "suggested_fix" not in f0:
        return False, f"finding fields off-contract (has {sorted(f0)})"
    return True, "envelope + summary + suggested_fix conform"


def check_eval0(text: str, outputs: Path) -> list[dict]:
    schema_ok, schema_ev = _schema_ok(outputs)
    return [
        {"text": "flags missing alt text", "passed": "alt" in text and _has_any(text, "image", "img"),
         "evidence": "alt+image mentioned" if "alt" in text else "no alt mention"},
        {"text": "flags low contrast", "passed": "contrast" in text,
         "evidence": "contrast mentioned" if "contrast" in text else "no contrast mention"},
        {"text": "flags the unlabeled form field", "passed": "label" in text,
         "evidence": "label mentioned" if "label" in text else "no label mention"},
        {"text": "flags heading structure / missing h1",
         "passed": _has_any(text, "heading", "<h1", "h1 ", "h1.", "h1,", "level-one", "headings"),
         "evidence": "heading mentioned" if _has_any(text, "heading", "h1") else "none"},
        {"text": "findings mention severity + a fix", "passed": _structured(text),
         "evidence": "severity+fix present" if _structured(text) else "unstructured"},
        {"text": "emits the documented return envelope (mergeable schema)", "passed": schema_ok,
         "evidence": schema_ev},
    ]


def check_eval1(text: str, outputs: Path) -> list[dict]:
    schema_ok, schema_ev = _schema_ok(outputs)
    return [
        {"text": "flags icon button missing accessible name",
         "passed": _has_any(text, "accessible name", "aria-label", "button name", "icon button", "discernible"),
         "evidence": "name issue mentioned" if _has_any(text, "accessible name", "aria-label", "discernible") else "none"},
        {"text": "flags placeholder-as-label", "passed": "placeholder" in text or "label" in text,
         "evidence": "placeholder/label mentioned" if ("placeholder" in text or "label" in text) else "none"},
        {"text": "flags table missing headers",
         "passed": _has_any(text, "header cell", "<th", "th ", "table header", "headers"),
         "evidence": "table-header issue mentioned" if _has_any(text, "header", "<th") else "none"},
        {"text": "findings mention severity + a fix", "passed": _structured(text),
         "evidence": "severity+fix present" if _structured(text) else "unstructured"},
        {"text": "emits the documented return envelope (mergeable schema)", "passed": schema_ok,
         "evidence": schema_ev},
    ]


CHECKERS = {0: check_eval0, 1: check_eval1}


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent
    default = here.parent.parent / "ux-audit-workspace" / "iteration-1"
    iteration = Path(argv[1]).resolve() if len(argv) > 1 else default
    if not iteration.is_dir():
        print(f"error: iteration dir not found: {iteration}", file=sys.stderr)
        return 2

    totals = {c: [0, 0] for c in CONFIGS}
    print(f"\n== ux-audit grading: {iteration} ==\n")
    for eval_dir in sorted(iteration.glob("eval-*")):
        eid = int(eval_dir.name.split("-")[1])
        checker = CHECKERS.get(eid)
        if not checker:
            continue
        for cfg in CONFIGS:
            outputs = eval_dir / cfg / "outputs"
            if not outputs.is_dir():
                continue
            text = _text(outputs)
            results = checker(text, outputs)
            grading = {"run_id": f"{eval_dir.name}-{cfg}", "expectations": results}
            (eval_dir / cfg / "grading.json").write_text(json.dumps(grading, indent=2))
            p = sum(1 for r in results if r["passed"])
            totals[cfg][0] += p
            totals[cfg][1] += len(results)
            print(f"{eval_dir.name:20} {cfg:14} {p}/{len(results)}")
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
