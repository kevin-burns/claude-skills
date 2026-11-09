#!/usr/bin/env python3
"""Generate adr-author routing cases in the root evals/ layout that `claude plugin eval` reads.

One directory per prompt: `adr-author-route-NN` for should-trigger, `adr-author-not-NN` for
should-not. Each has a `prompt.md` with front matter and a `graders/fired.md` that checks whether
the Skill tool was called with adr-author: at least once for should-trigger, never for should-not.

Usage:
    make_routing_cases.py [EVALS_DIR]     # default: the repository's root evals/ directory
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUTING = HERE / "routing.json"
DEFAULT_TARGET = HERE.parents[1] / "evals"
MATCH = "input_match: '\"skill\"\\s*:\\s*\"(?:[\\w-]+:)?adr-author\"'\n"

PROMPT = "---\nmax_turns: 10\nallowed_tools: [Read, Glob, Grep, Skill]\n---\n\n{text}\n"
FIRES = ("---\ntype: tool_used\ntool: Skill\n" + MATCH + "---\n\n"
         "Did the request reach `adr-author`? Should-trigger case generated from "
         "adr-author/evals/routing.json.\n")
SILENT = ("---\ntype: tool_used\ntool: Skill\n" + MATCH + "min: 0\nmax: 0\narm: both\n---\n\n"
          "`adr-author` must NOT fire here: this is a near miss that belongs to another skill or to "
          "none. Generated from adr-author/evals/routing.json.\n")


def write_cases(target: Path) -> list[Path]:
    """Write all routing cases under target and return their directories in order."""
    data = json.loads(ROUTING.read_text(encoding="utf-8"))
    written = []
    for kind, prompts, grader in (("route", data["should_trigger"], FIRES), ("not", data["should_not"], SILENT)):
        for n, text in enumerate(prompts, 1):
            case = target / f"adr-author-{kind}-{n:02d}"
            (case / "graders").mkdir(parents=True, exist_ok=True)
            (case / "prompt.md").write_text(PROMPT.format(text=text), encoding="utf-8")
            (case / "graders" / "fired.md").write_text(grader, encoding="utf-8")
            written.append(case)
    return written


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    target = Path(args[0]) if args else DEFAULT_TARGET
    for case in write_cases(target):
        print(case)
    return 0


if __name__ == "__main__":
    sys.exit(main())
