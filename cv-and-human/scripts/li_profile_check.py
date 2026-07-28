#!/usr/bin/env python3
"""Deterministic checks for a LinkedIn profile draft.

Character counting is the load-bearing part. LinkedIn's field counters run in
the browser, and ECMAScript defines String.prototype.length as the number of
UTF-16 code units -- so an emoji (a surrogate pair) counts as 2 there and as 1
under Python's len(), which counts code points. Reporting 214/220 on a headline
LinkedIn then rejects is worse than reporting nothing, because the user has been
told to trust the number.

If LinkedIn is ever observed to disagree, change count_chars() and nothing else.
"""

import argparse
import json
import sys

# Third-party-sourced; LinkedIn publishes no consolidated table. One block, so a
# drift is a one-line fix rather than a hunt through prose.
LIMITS = {
    "headline": 220,        # ~240 reported on mobile; target the stricter number
    "about": 2600,
    "experience": 2000,
    "position_title": 100,
    "company_name": 100,
    "skill": 80,
}

# Characters visible before the "see more" fold.
FOLD = 200


def count_chars(text: str) -> int:
    """Count UTF-16 code units, matching JavaScript's String.prototype.length."""
    return len(text.encode("utf-16-le")) // 2


def utf16_slice(text: str, n: int) -> str:
    """First n UTF-16 code units, never splitting a surrogate pair."""
    truncated = text.encode("utf-16-le")[: n * 2]
    return truncated.decode("utf-16-le", errors="ignore")


def check_field(name: str, text: str) -> dict:
    """Count one field against its limit."""
    limit = LIMITS[name]
    count = count_chars(text)
    return {
        "field": name,
        "count": count,
        "limit": limit,
        "over_by": max(0, count - limit),
        "ok": count <= limit,
    }


def check_front_load(text: str, must_contain: list[str]) -> dict:
    """Check the user's own specifics appear above the "see more" fold.

    Most readers never expand About, so a claim below the fold is a claim nobody
    reads. This checks presence, not quality -- no script can tell you the first
    two lines are generic.
    """
    visible = utf16_slice(text, FOLD)
    lowered = visible.lower()
    missing = [t for t in must_contain if t.lower() not in lowered]
    return {
        "check": "front_load",
        "visible": visible,
        "fold": FOLD,
        "missing": missing,
        "ok": not missing,
    }


def keyword_coverage(keywords: list[str], fields: dict[str, str]) -> list[dict]:
    """For each target keyword, report which fields carry it."""
    rows = []
    for keyword in keywords:
        needle = keyword.lower()
        carrying = [name for name, text in fields.items() if needle in text.lower()]
        rows.append({"keyword": keyword, "fields": carrying, "covered": bool(carrying)})
    return rows


def check_skills(skills: list[str]) -> list[dict]:
    """Each skill has its own length limit."""
    return [dict(check_field("skill", s), skill=s) for s in skills]


def check_profile(profile: dict) -> dict:
    """Run every check over a profile draft.

    profile: {"headline": str, "about": str, "skills": [str],
              "keywords": [str], "must_contain": [str]}

    Coverage results are advisory and do not affect ok or exit code: a keyword
    not covered in any field usually means the user lacks that skill, and this
    skill forbids inventing skills the candidate cannot back up.
    """
    headline = profile.get("headline", "")
    about = profile.get("about", "")
    skills = profile.get("skills", [])

    fields = {"headline": headline, "about": about, "skills": " ".join(skills)}
    results = {
        "fields": [check_field("headline", headline), check_field("about", about)],
        "front_load": check_front_load(about, profile.get("must_contain", [])),
        "skills": check_skills(skills),
        "coverage": keyword_coverage(profile.get("keywords", []), fields),
    }
    results["ok"] = (
        all(f["ok"] for f in results["fields"])
        and results["front_load"]["ok"]
        and all(s["ok"] for s in results["skills"])
    )
    return results


def _format_table(results: dict) -> str:
    lines = ["field        count  limit  status"]
    for f in results["fields"]:
        status = "ok" if f["ok"] else f"OVER by {f['over_by']}"
        lines.append(f"{f['field']:<12} {f['count']:>5}  {f['limit']:>5}  {status}")

    fold = results["front_load"]
    lines.append("")
    lines.append(f"above the fold ({fold['fold']} chars): {fold['visible'][:80]!r}...")
    if fold["missing"]:
        lines.append(f"  MISSING above the fold: {', '.join(fold['missing'])}")

    over = [s for s in results["skills"] if not s["ok"]]
    if over:
        lines.append("")
        for s in over:
            lines.append(f"  skill OVER by {s['over_by']}: {s['skill'][:40]}...")

    uncovered = [c["keyword"] for c in results["coverage"] if not c["covered"]]
    if uncovered:
        lines.append("")
        lines.append(f"  keywords not carried by any field: {', '.join(uncovered)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("profile", nargs="?", help="JSON file; omit to read stdin")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()

    raw = open(args.profile).read() if args.profile else sys.stdin.read()
    results = check_profile(json.loads(raw))

    print(json.dumps(results, indent=2) if args.json else _format_table(results))
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
