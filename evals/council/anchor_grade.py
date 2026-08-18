#!/usr/bin/env python3
"""Grade the anchoring test: does a member echo vocabulary it could only have got
from the members that preceded it?

The metric is BORROWED VOCABULARY. Build three bags of content words:

  brief    the shared input both conditions see
  prefix   the five preceding contributions (LAST condition only)
  target   the member's own output

A borrowed term is one in `target` that appears in `prefix` and NOT in `brief`. The
target could not have got it from the shared input, so in the LAST condition it either
came from its predecessors or from the model's own vocabulary. The FIRST condition never
saw the prefix, so ITS borrowed count is exactly that baseline -- the rate at which two
independent readings of the same brief happen to reach for the same words.

So the comparison is not "does LAST borrow" (it will, by chance) but "does LAST borrow
MORE THAN CHANCE", where chance is measured, not assumed.

Read it the way ../ablation reads its arms: a difference is only a difference if it beats
the replicate-to-replicate spread within each condition.
"""
import itertools
import json
import pathlib
import re
import statistics

HERE = pathlib.Path(__file__).parent
RUNS = HERE / "runs"

# Function words carry no evidence of borrowing -- both conditions use them at similar
# rates whatever happened. Trimming them stops the metric measuring English.
#
# SIM905 wants a list literal here. It conflicts with E501: ~100 words as a literal is
# the 1,048-character line ruff rejects on the next rule. The readable form wins.
STOP = frozenset("""a an the and or but if then than that this these those there here it its is are was were
be been being am do does did doing have has had having will would shall should can could
may might must not no nor so as at by for from in into of off on onto out over to under
up with within without about above after again against all also any because before below
between both during each few further more most other others our out own same some such
only very via when where which who whom why how what while you your they them their we
us i me my he she his her one two three what's i'm it's don't doesn't isn't aren't we're
they're you're cannot""".split())  # noqa: SIM905

WORD = re.compile(r"[a-z][a-z0-9'-]+")


def bag(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOP and len(w) > 3}


def result(name: str, rep: str) -> str | None:
    p = RUNS / f"{name}-{rep}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    if d.get("is_error"):
        return None
    return d.get("result") or None


def main() -> int:
    brief = bag((HERE / "brief.md").read_text())
    prefix_txt = "".join(
        (result(f"prefix-{m}", "1") or "")
        for m in ("software-architect", "data-engineer", "devops-sre", "product-manager", "customer-voice")
    )
    prefix = bag(prefix_txt)
    # Only terms the target could NOT have taken from the shared brief.
    borrowable = prefix - brief
    print(f"brief: {len(brief)} content words   prefix: {len(prefix)}   "
          f"borrowable (prefix minus brief): {len(borrowable)}\n")

    rows, rates = {}, {}
    for cond in ("first", "last"):
        rs = []
        print(f"  {cond.upper()}")
        for rep in "12345":
            r = result(cond, rep)
            if r is None:
                print(f"    rep {rep}: MISSING/ERROR")
                continue
            t = bag(r)
            borrowed = t & borrowable
            rate = len(borrowed) / len(t) if t else float("nan")
            rs.append(rate)
            print(f"    rep {rep}: {len(t):>4} words  {len(borrowed):>3} borrowed  {rate:.3f}")
        rates[cond] = rs
        rows[cond] = rs

    print()
    for cond, rs in rates.items():
        if len(rs) > 1:
            print(f"  {cond}: mean {statistics.mean(rs):.4f}  sd {statistics.stdev(rs):.4f}  n={len(rs)}")

    a, b = rates["first"], rates["last"]
    if len(a) > 1 and len(b) > 1:
        obs = statistics.mean(b) - statistics.mean(a)
        pool = a + b
        hits = tot = 0
        for combo in itertools.combinations(range(len(pool)), len(a)):
            x = [pool[i] for i in combo]
            y = [pool[i] for i in range(len(pool)) if i not in combo]
            if statistics.mean(y) - statistics.mean(x) >= obs - 1e-12:
                hits += 1
            tot += 1
        print(f"\n  LAST minus FIRST: {obs:+.4f}   exact permutation p={hits/tot:.4f} "
              f"(min attainable {1/tot:.4f})")
        # The within-condition spread is the noise floor: an effect smaller than the
        # replicate spread is not readable whatever the p-value says.
        floor = statistics.mean([statistics.stdev(a), statistics.stdev(b)])
        print(f"  within-condition sd (noise floor): {floor:.4f}   "
              f"effect/floor = {obs/floor:.2f}" if floor else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
