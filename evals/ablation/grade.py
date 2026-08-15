#!/usr/bin/env python3
"""Grade the ablation runs mechanically.

The instrument is a coverage mask, not a label match. Each `tells[].quote` is
located in the case input and the character span it covers is marked. An arm's
output becomes a set of input positions it objected to. That is granularity
robust: "robust" and "a robust, seamless architecture" overlap instead of
counting as two unrelated findings, which a label or string comparison would
get wrong.

Two numbers matter and only in relation to each other:

  within-arm  Jaccard between replicates of the SAME arm -- the noise floor
  between-arm Jaccard between different arms

If between-arm agreement is no worse than within-arm agreement, the ablated
material changed nothing that this instrument can see.
"""

import itertools
import json
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).parent
RUNS = HERE / "runs"
CASES = HERE / "cases"

EXPECTED_TYPE = {"1": "docs", "3": "linkedin", "8": None, "9": None}

# Vocabulary the skill teaches by name. An arm can converge on the same
# objections while describing them in its own words; counting these separates
# "the list changed what was found" from "the list changed what it was called".
SKILL_TERMS = [
    "copula",
    "negative parallelism",
    "engagement bait",
    "significance inflation",
    "rule of three",
    "permission phrase",
    "ai vocabulary",
    "vague",
    "filler",
    "cliche",
    "cliché",
]


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower())


def coverage(quotes: list[str], source: str) -> tuple[set[int], int]:
    """Map quotes onto character positions of the (normalised) source.

    Returns (covered positions, number of quotes not found in the source).
    A quote that cannot be located is either a paraphrase or a fabrication;
    either way it is not evidence about the input, so it is counted separately
    rather than silently dropped.
    """
    src = norm(source)
    src = re.sub(r"\s+", " ", src)
    covered: set[int] = set()
    missing = 0
    for q in quotes:
        nq = re.sub(r"\s+", " ", norm(q)).strip()
        if not nq:
            missing += 1
            continue
        i = src.find(nq)
        if i < 0:
            missing += 1
            continue
        covered.update(range(i, i + len(nq)))
    return covered, missing


def jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def permutation_p(xs: list[set[int]], ys: list[set[int]]) -> tuple[float, int]:
    """Exact permutation test on the mean within-minus-between Jaccard gap.

    H0: the arm label carries no information, so any 3/3 split of the pooled
    runs is as good as the observed one. With 3 replicates per arm there are
    only 10 distinct splits, so p can never fall below 0.10 -- the design
    cannot reject at 0.05 however large the effect. That ceiling is reported
    alongside p so it cannot be mistaken for a null.
    """
    pool = xs + ys
    k = len(xs)
    if k < 2 or len(ys) < 2:
        return float("nan"), 1

    def gap(idx: tuple[int, ...]) -> float:
        a = [pool[i] for i in idx]
        b = [pool[i] for i in range(len(pool)) if i not in idx]
        w = [jaccard(p, q) for p, q in itertools.combinations(a, 2)]
        w += [jaccard(p, q) for p, q in itertools.combinations(b, 2)]
        btw = [jaccard(p, q) for p in a for q in b]
        return statistics.mean(w) - statistics.mean(btw)

    splits = [s for s in itertools.combinations(range(len(pool)), k) if 0 in s]
    observed = gap(tuple(range(k)))
    extreme = sum(1 for s in splits if gap(s) >= observed - 1e-12)
    return extreme / len(splits), len(splits)


def load(case: str, arm: str, rep: str):
    p = RUNS / f"{case}-{arm}-{rep}.json"
    if not p.exists() or not p.stat().st_size:
        return None
    env = json.loads(p.read_text())
    if env.get("is_error"):
        return {"error": env.get("result"), "cost": env.get("total_cost_usd", 0.0)}
    try:
        payload = json.loads(env["result"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return {"error": "unparseable result", "cost": env.get("total_cost_usd", 0.0)}
    payload["cost"] = env.get("total_cost_usd", 0.0)
    return payload


def main() -> int:
    cases = sys.argv[1:] or ["1", "3", "8", "9"]
    arms = sorted({p.stem.split("-")[1] for p in RUNS.glob("*-*-*.json")})
    total_cost = 0.0

    for case in cases:
        reps = sorted({p.stem.rsplit("-", 1)[1] for p in RUNS.glob(f"{case}-*-*.json")}, key=int)
        source = (CASES / f"{case}.txt").read_text()
        print(f"\n{'=' * 72}\nCASE {case}\n{'=' * 72}")

        cov: dict[str, list[set[int]]] = {}
        for arm in arms:
            cov[arm] = []
            rows = []
            for rep in reps:
                d = load(case, arm, rep)
                if d is None:
                    continue
                total_cost += d.get("cost", 0.0)
                if "error" in d:
                    rows.append((rep, "ERROR", d["error"][:40], "", ""))
                    continue
                quotes = [t.get("quote", "") for t in d.get("tells", [])]
                c, missing = coverage(quotes, source)
                cov[arm].append(c)
                ctype = d.get("content_type", "")
                exp = EXPECTED_TYPE.get(case)
                tick = "" if exp is None else ("ok" if ctype == exp else f"WRONG(exp {exp})")
                rows.append(
                    (rep, len(quotes), f"{len(c)}ch", f"{missing} unlocated", f"{ctype} {tick}")
                )
            print(f"\n  arm {arm}")
            for r in rows:
                print(f"    rep {r[0]}: tells={r[1]:<4} covered={r[2]:<7} {r[3]:<14} type={r[4]}")

        # Only compare arms that actually ran on this case. Not every arm was run
        # on every case -- D and E were built to answer a question that only the
        # rewrite cases can answer -- and averaging two empty noise floors throws.
        arms = [a for a in arms if len(cov.get(a, [])) >= 2]

        # noise floor vs signal
        print("\n  agreement (coverage Jaccard, 1.0 = identical objections)")
        within = {}
        for arm in arms:
            pairs = [jaccard(a, b) for a, b in itertools.combinations(cov[arm], 2)]
            within[arm] = statistics.mean(pairs) if pairs else float("nan")
            print(f"    within {arm}      : {within[arm]:.3f}   (noise floor, n={len(pairs)} pairs)")
        for x, y in itertools.combinations(arms, 2):
            pairs = [jaccard(a, b) for a in cov[x] for b in cov[y]]
            m = statistics.mean(pairs) if pairs else float("nan")
            floor = statistics.mean([v for v in (within[x], within[y]) if v == v])
            p, nperm = permutation_p(cov[x], cov[y])
            print(
                f"    between {x} vs {y} : {m:.3f}   floor {floor:.3f}   "
                f"gap {floor - m:+.3f}   perm p={p:.3f} (min attainable {1 / nperm:.3f})"
            )

        # terminology transfer: does the arm speak the skill's vocabulary?
        print("\n  skill vocabulary in labels (transfer without behaviour change?)")
        for arm in arms:
            hits = []
            for rep in reps:
                d = load(case, arm, rep)
                if not d or "error" in d:
                    continue
                blob = " ".join(t.get("label", "") for t in d.get("tells", [])).lower()
                hits.append(sum(1 for term in SKILL_TERMS if term in blob))
            avg = statistics.mean(hits) if hits else float("nan")
            print(f"    arm {arm}: {avg:.1f} skill terms per run  {hits}")

    print(f"\ntotal cost across graded runs: ${total_cost:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
