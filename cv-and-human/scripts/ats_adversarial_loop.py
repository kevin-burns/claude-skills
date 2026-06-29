#!/usr/bin/env python3
"""
Measured ATS-lens harness for cv-and-human's red-team pass.

This drives the *measuring* half of the red team's ATS lens: it scores a CV through
a real ATS critic N times and reports the distribution (median / min / range), so
push-back targets the typical outcome rather than a single lucky run. The red team
*finds* weaknesses; the tailor *fixes* the truthful ones — this script only measures.

Design notes:
- The critic is non-deterministic, so a single score is meaningless. We always
  sample N>=5 and compare distributions.
- The scorer is pluggable. Provide a shell command that takes a CV path and prints
  the critic's JSON to stdout (e.g. a local `hiring-agent` invocation), or use the
  built-in stub for testing the harness logic without a model backend.

Usage:
  # Real critic (local hiring-agent that prints JSON with a numeric total):
  python ats_adversarial_loop.py score --cv cv.pdf \\
      --scorer-cmd "python /path/hiring-agent/score.py --json {cv}" --runs 10

  # Harness self-test with the deterministic-ish stub:
  python ats_adversarial_loop.py selftest
"""
from __future__ import annotations
import argparse
import json
import random
import statistics
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from typing import Callable, Optional


@dataclass
class Distribution:
    runs: list[float] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.runs)

    @property
    def median(self) -> float:
        return statistics.median(self.runs) if self.runs else float("nan")

    @property
    def minimum(self) -> float:
        return min(self.runs) if self.runs else float("nan")

    @property
    def maximum(self) -> float:
        return max(self.runs) if self.runs else float("nan")

    def summary(self) -> str:
        if not self.runs:
            return "no runs"
        return (f"median {self.median:.1f}, range {self.minimum:.0f}-"
                f"{self.maximum:.0f} over {self.n} runs")


def score_n(cv_path: str, scorer: Callable[[str], float], runs: int) -> Distribution:
    """Score one CV `runs` times via the pluggable scorer."""
    dist = Distribution()
    for i in range(runs):
        dist.runs.append(float(scorer(cv_path)))
    return dist


def subprocess_scorer(scorer_cmd: str) -> Callable[[str], float]:
    """Build a scorer that runs a shell command and extracts a numeric total.

    `{cv}` in the command is replaced with the CV path. The command must print
    JSON to stdout; we look for a numeric 'total'/'total_score'/'overall' field,
    else the last number on the last non-empty line.
    """
    def _scorer(cv_path: str) -> float:
        cmd = scorer_cmd.replace("{cv}", cv_path)
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                             timeout=600)
        text = out.stdout.strip()
        try:
            data = json.loads(text)
            for k in ("total", "total_score", "overall", "overall_score", "score"):
                if isinstance(data, dict) and k in data:
                    return float(data[k])
        except json.JSONDecodeError:
            pass
        # Fallback: last number on the last non-empty line.
        for line in reversed([l for l in text.splitlines() if l.strip()]):
            toks = [t for t in line.replace(":", " ").split() if _isnum(t)]
            if toks:
                return float(toks[-1])
        raise ValueError(f"Could not parse a score from scorer output:\n{text[:500]}")
    return _scorer


def _isnum(t: str) -> bool:
    try:
        float(t)
        return True
    except ValueError:
        return False


def improved(old: Distribution, new: Distribution, eps: float = 2.0) -> bool:
    """A revision is a real improvement only if the median rises by more than the
    noise band AND the worst-case floor does not drop materially."""
    if old.n == 0:
        return True
    median_gain = new.median - old.median
    floor_drop = old.minimum - new.minimum
    return median_gain > eps and floor_drop <= eps


def plateaued(history: list[Distribution], eps: float = 2.0) -> bool:
    """Stop when the last two iterations' medians differ by < eps."""
    if len(history) < 2:
        return False
    return abs(history[-1].median - history[-2].median) < eps


# --------------------------------------------------------------------------- #
# Built-in stub critic for harness self-testing (no model backend required).
# Models a noisy critic whose mean depends on a few legitimate CV signals.
# --------------------------------------------------------------------------- #
def stub_scorer_factory(signals: dict) -> Callable[[str], float]:
    """signals: dict of truthful CV properties → a base score, then add noise.
    Mirrors hiring-agent's real levers so the harness logic is exercised."""
    base = 40.0
    base += 25 if signals.get("real_open_source") else 0
    base += 15 if signals.get("complex_projects") else 0
    base += 10 if signals.get("all_projects_have_links") else 0
    base += 5 if signals.get("portfolio_url") else 0
    base -= 8 if signals.get("tutorial_projects") else 0

    def _scorer(_cv_path: str) -> float:
        # +/- noise reproduces the documented non-determinism.
        return max(0.0, min(120.0, base + random.gauss(0, 6)))
    return _scorer


def selftest() -> int:
    """Exercise the harness logic end-to-end with the stub, no model needed."""
    random.seed(0)
    print("== adversarial harness self-test ==")

    # v0: weak CV (linkless tutorial projects, no portfolio).
    v0_signals = dict(real_open_source=False, complex_projects=False,
                      all_projects_have_links=False, portfolio_url=False,
                      tutorial_projects=True)
    # v1: truthful improvements (surfaced real OSS, added real links + portfolio,
    # dropped toy projects).
    v1_signals = dict(real_open_source=True, complex_projects=True,
                      all_projects_have_links=True, portfolio_url=True,
                      tutorial_projects=False)

    history: list[Distribution] = []
    for label, sig in (("v0", v0_signals), ("v1", v1_signals)):
        dist = score_n("dummy.pdf", stub_scorer_factory(sig), runs=10)
        history.append(dist)
        print(f"  {label}: {dist.summary()}")

    assert history[0].n == 10, "expected 10 runs"
    assert improved(history[0], history[1]), "v1 should beat v0 on the distribution"
    assert not plateaued(history), "v0->v1 should not look plateaued"
    # A no-op revision should look plateaued and not 'improved'.
    same = score_n("dummy.pdf", stub_scorer_factory(v1_signals), runs=10)
    assert plateaued([history[1], same]), "identical signals should plateau"
    assert not improved(history[1], same), "no real change should not count as improvement"
    print("  median/min/range, improvement gate, and plateau detection: OK")
    print("PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="score a CV N times via a real critic")
    s.add_argument("--cv", required=True)
    s.add_argument("--scorer-cmd", required=True,
                   help="shell command; '{cv}' is replaced with the CV path; "
                        "must print the critic's JSON/score to stdout")
    s.add_argument("--runs", type=int, default=10)
    s.add_argument("--out", default=None, help="optional JSON history output path")

    sub.add_parser("selftest", help="run harness logic self-test (no model needed)")

    args = ap.parse_args()
    if args.cmd == "selftest":
        return selftest()

    if args.cmd == "score":
        scorer = subprocess_scorer(args.scorer_cmd)
        dist = score_n(args.cv, scorer, args.runs)
        print(dist.summary())
        if args.out:
            with open(args.out, "w") as f:
                json.dump(asdict(dist), f, indent=2)
            print(f"wrote {args.out}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
