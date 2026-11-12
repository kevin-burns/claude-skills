"""layers: the layers a breakdown is checked against come from the spec in its own words, or are
marked Proposed: for the person to confirm (2026-11-11 rerun: an agent collapsed four named adapters
into one and said "the spec names no finer split")."""

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))

from check_tickets import check_layers
from tickets_md import Tickets

SPEC = ("## Implementation decisions\n\n- Four layers: web pages, an API, a database, and an email adapter "
        "for outgoing messages.\n")


def t(layers, layers_from=None):
    front = {"layers": list(layers)}
    if layers_from is not None:
        front["layers_from"] = layers_from
    return Tickets(front, ())


def rules(findings):
    return [f.rule for f in findings]


def test_missing_source_is_a_finding():
    assert rules(check_layers(t(["web", "api"]), "", SPEC)) == ["layers"]


def test_quote_from_the_spec_naming_every_layer_passes():
    quote = '"Four layers: web pages, an API, a database, and an email adapter"'
    assert check_layers(t(["web pages", "API", "database", "email adapter"], quote), "", SPEC) == []
    assert check_layers(t(["web-pages", "api", "databases", "email"], quote), "", SPEC) == []  # forms vary


def test_layer_not_in_the_quote_is_named():
    quote = '"Four layers: web pages, an API, a database, and an email adapter"'
    [f] = check_layers(t(["web pages", "API", "storage"], quote), "", SPEC)
    assert "storage" in f.message


def test_quote_not_in_the_spec_fails():
    assert rules(check_layers(t(["core", "adapters"], '"the core and its adapters"'), "", SPEC)) == ["layers"]


def test_short_quote_fails():
    assert rules(check_layers(t(["database"], '"a database"'), "", SPEC)) == ["layers"]


def test_proposed_source_passes_and_no_layers_means_nothing_to_check():
    assert check_layers(t(["ui", "core"], "Proposed: the spec names no layers"), "", SPEC) == []
    assert check_layers(Tickets({}, ()), "", SPEC) == []


def test_check_lists_a_proposed_layers_source(tmp_path):
    d = tmp_path / "docs"
    d.mkdir()
    (d / "prd.md").write_text("## Goal\n\nVolunteers sign up for shifts online and drop out of them.\n",
                              encoding="utf-8")
    (d / "tickets.md").write_text("""---
prd: prd.md
layers: [ui, core]
layers_from: Proposed: the spec names no layers
---

## Increment 1 — skeleton

### T1 — Sign up
- moscow: Must
- size: S
- layers: [ui, core]
- kind: slice
- traces: "Volunteers sign up for shifts online"
- acceptance:
  - A volunteer signs up (proves: the goal)

### T2 — Drop out
- moscow: Could
- size: S
- layers: [ui, core]
- kind: slice
- traces: "and drop out of them"
- acceptance:
  - A volunteer drops out (proves: the goal)
""", encoding="utf-8")
    run = subprocess.run([sys.executable, str(HERE / "scripts" / "check_tickets.py"), "check", str(d / "tickets.md")],
                         capture_output=True, text=True, check=False, env={**os.environ, "HOME": str(tmp_path)})
    assert "layers_from" in run.stdout and "Proposed" in run.stdout, run.stdout
