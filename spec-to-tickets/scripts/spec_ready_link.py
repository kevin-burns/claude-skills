"""Find the spec-ready skill installed beside this one, to reuse its transcript reader.

spec-to-tickets depends on spec-ready, never the reverse. Both ship in the same collection, so
spec-ready sits in a sibling directory whether this skill runs from a checkout, a plugin install
or a symlinked skills directory. When it is not there, callers fall back and say so.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def find_spec_ready(here: Path | None = None) -> Path | None:
    here = here or Path(__file__)
    candidates = [Path(os.path.abspath(here)).parent.parent.parent, here.resolve().parent.parent.parent]
    for root in candidates:
        scripts = root / "spec-ready" / "scripts"
        if (scripts / "transcripts.py").is_file():
            return scripts
    return None


def load_transcripts():
    """spec-ready's transcripts module, or None when spec-ready is not installed beside this skill."""
    scripts = find_spec_ready()
    if scripts is None:
        return None
    if str(scripts) not in sys.path:
        sys.path.append(str(scripts))
    return importlib.import_module("transcripts")
