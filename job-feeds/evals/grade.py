#!/usr/bin/env python3
"""Offline behavioural eval for job-feeds. Exits non-zero on any failure.

Run:  uv run evals/grade.py
  or: python3 evals/grade.py          (the skill is stdlib-only)

This is deliberately NOT a re-run of the unit suite. It asserts the handful
of behaviours whose absence would be SILENT in daily use -- a source
returning fewer rows, a duplicate quietly dropped, a rate limit forgotten,
an attribution link removed. Those are the failures you would not notice.
"""

import json
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import report  # noqa: E402
from job_feeds import RateLimiter, Store, fetch_all, load_config, location_counts  # noqa: E402
from sources import SOURCES, validate_schema  # noqa: E402

FIXTURES = ROOT / "scripts" / "tests" / "fixtures"
NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
RSS = ("wwr", "pythonorg")

results = []


def check(eval_id, name, condition, detail=""):
    results.append((eval_id, name, bool(condition), detail))


def load_fixture(name):
    path = FIXTURES / (name + (".xml" if name in RSS else ".json"))
    raw = path.read_bytes()
    return SOURCES[name], (ET.fromstring(raw) if name in RSS else json.loads(raw))


def job(**over):
    base = {"title": "Cloud Engineer", "company": "Acme", "location": "Berlin",
            "remote": True, "posted_at": "2026-08-04T00:00:00Z", "url": "https://x/1",
            "description": "d", "tags": [], "salary": None, "source": "arbeitnow"}
    base.update(over)
    return base


def main():
    tmp = Path(tempfile.mkdtemp())

    # 0 -- drift rejects wholesale, naming the field
    broken = [{"slug": "a", "title": "T", "company_name": "C", "location": "L",
               "remote": True, "url": "u"}]
    rows, reason = validate_schema(SOURCES["arbeitnow"], broken)
    check(0, "schema-drift-rejects-wholesale",
          rows == [] and reason and "created_at" in reason, reason or "no reason given")

    # 1 -- healthy fixtures pass their own declared schema
    bad = [name for name in SOURCES
           if validate_schema(*(lambda s, p: (s, s.rows(p)))(*load_fixture(name)))[1]]
    check(1, "healthy-fixtures-pass-their-own-schema", not bad, f"drifted: {bad}")

    # 2 / 3 -- dedupe in both directions
    store = Store(tmp / "dedupe.db")
    store.upsert([job(source="remotive", location="Americas, Europe, Israel"),
                  job(source="wwr", location="Anywhere in the World")], NOW)
    merged = store.select(30, NOW)
    check(2, "dedupe-collapses-cross-source",
          len(merged) == 1 and "wwr" in (merged[0]["also_seen_on"] or ""),
          f"{len(merged)} row(s)")

    store2 = Store(tmp / "cities.db")
    store2.upsert([job(title="Senior Counsel", location="Cambridge"),
                   job(title="Senior Counsel", location="London")], NOW)
    check(3, "dedupe-preserves-distinct-cities", len(store2.select(30, NOW)) == 2,
          f"{len(store2.select(30, NOW))} row(s)")

    # 4 -- first_seen survives a refetch
    store3 = Store(tmp / "seen.db")
    store3.upsert([job()], NOW)
    store3.upsert([job()], NOW + timedelta(days=3))
    row = store3.select(30, NOW + timedelta(days=3))[0]
    check(4, "first-seen-survives-refetch",
          row["first_seen"] == "2026-08-05T12:00:00Z"
          and row["last_seen"] == "2026-08-08T12:00:00Z",
          f"{row['first_seen']} / {row['last_seen']}")

    # 5 -- undated rows survive the window filter
    store4 = Store(tmp / "undated.db")
    store4.upsert([job(posted_at=None, source="pythonorg")], NOW)
    check(5, "undated-rows-are-kept", len(store4.select(14, NOW)) == 1)

    # 6 -- rate limiter fails closed on lost state
    allowed, why = RateLimiter(tmp / "absent.json").allows(SOURCES["jobicy"], NOW, seen=True)
    check(6, "ratelimit-fails-closed", not allowed, why)

    # 7 -- a 429 is backpressure, and it is remembered
    limiter = RateLimiter(tmp / "bp.json")
    limiter.record(SOURCES["jobicy"], NOW)
    opener = lambda url, headers: (429, b"", {})  # noqa: E731
    result = fetch_all([SOURCES["arbeitnow"]], opener, limiter,
                       Store(tmp / "bp.db"), NOW)[0]
    recorded = json.loads((tmp / "bp.json").read_text(encoding="utf-8"))
    check(7, "backpressure-is-not-failure",
          result.status == "throttled" and "arbeitnow" in recorded,
          f"{result.status}, recorded={sorted(recorded)}")

    # 8 / 9 / 10 -- the report
    config_path = tmp / "config.json"
    config_path.write_text(json.dumps({
        "defaults": {"window": 14},
        "lanes": [{"name": "p", "label": "P", "match": "engineer|xt1"}]}), encoding="utf-8")
    config = load_config(config_path)
    hostile = job(title="<script>XT1</script>",
                  company="\"XC2 onmouseover=\"a ' onmouseover='b",
                  source="remoteok")
    hostile.update({"lanes": ["P"], "highlight": False, "also_seen_on": ""})
    doc = report.render_html([hostile], config, 14, [], "fixed")

    unquoted = []
    import re
    for tag in re.findall(r"<([a-zA-Z][^>]*)>", doc):
        quote, i = None, 0
        while i < len(tag):
            c = tag[i]
            if quote:
                if c == quote:
                    quote = None
            elif c in "\"'":
                quote = c
            elif c == "=" and tag[i + 1:i + 2] not in ("\"", "'"):
                unquoted.append(tag[:50])
                break
            i += 1
    check(8, "report-escapes-hostile-input",
          "<script>XT1</script>" not in doc and doc.count("<script>") == 1
          and not unquoted and "' onmouseover='" not in doc,
          f"unquoted={unquoted[:2]}")

    footer = doc.split("<footer>", 1)[1]
    check(9, "attribution-is-present",
          "remoteok.com" in footer and "nofollow" not in footer)

    check(10, "report-is-self-contained-and-deterministic",
          doc == report.render_html([hostile], config, 14, [], "fixed")
          and "cdn." not in doc and "src=\"http" not in doc and "@import" not in doc)

    # 11 -- contacts stripped from every real fixture
    leaked = []
    for name in SOURCES:
        source, payload = load_fixture(name)
        for raw in source.rows(payload):
            text = source.normalise(raw)["description"] or ""
            if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
                leaked.append(name)
                break
    check(11, "contacts-stripped-at-ingest", not leaked, f"leaked: {leaked}")

    # Goes through a real Store round trip, which the unit tests do not: the
    # value has to survive SQLite and come back as None rather than the empty
    # string, or the breakdown silently loses the rows it exists to surface.
    store = Store(Path(tempfile.mkdtemp()) / "jobs.db")
    store.upsert([
        {"title": "Platform Engineer", "company": "Acme", "location": "Berlin",
         "remote": True, "posted_at": "2026-08-04T00:00:00Z", "url": "https://x/1",
         "description": "", "tags": [], "salary": None, "source": "arbeitnow"},
        {"title": "Data Engineer", "company": "Bcme", "location": None,
         "remote": True, "posted_at": "2026-08-04T00:00:00Z", "url": "https://x/2",
         "description": "", "tags": [], "salary": None, "source": "arbeitnow"},
        {"title": "SRE", "company": "Ccme", "location": "   ",
         "remote": True, "posted_at": "2026-08-04T00:00:00Z", "url": "https://x/3",
         "description": "", "tags": [], "salary": None, "source": "arbeitnow"},
    ], NOW)
    counts = dict(location_counts(store.select(30, NOW, False)))
    check(12, "unplaced-rows-are-counted-not-dropped",
          counts.get("(none)") == 2 and sum(counts.values()) == 3,
          f"counts: {counts}")

    width = max(len(name) for _, name, _, _ in results)
    failures = 0
    for eval_id, name, ok, detail in results:
        failures += not ok
        line = f"  [{eval_id:>2}] {name:<{width}}  {'PASS' if ok else 'FAIL'}"
        print(line + (f"   {detail}" if detail and not ok else ""))
    print(f"\n{len(results) - failures}/{len(results)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
