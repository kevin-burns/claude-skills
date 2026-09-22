#!/usr/bin/env python3
"""Compare the installed linearis CLI with the version this skill's gotchas were verified on.

WHY THIS EXISTS. Until 2026-09-22 SKILL.md ended its gotchas with a sentence: "every gotcha
above was re-verified against 2026.6.0 on 2026-08-05. Two of the eight had already gone
stale by then... so check before trusting." That sentence admitted a 25% staleness rate on
the day it was written and still left the reader to do the checking. It then went stale
itself: two upstream issues it called "(open)" closed on 2026-08-06, and a rule it gave
("a non-JSON error means you got the verb wrong") stopped firing once every error became
JSON. Nothing in the repository noticed for six weeks. (claude-skills-2qo, -kxs7.)

So the pin is now a constant in code, and this script asks the machine what is installed.

WHAT IT REPORTS. equal / ahead / behind against VERIFIED, and on any drift the eight
gotchas by number, because those are the claims that need re-checking.

WHAT IT DELIBERATELY DOES NOT DO.

  IT DOES NOT BLOCK. A check that fails the day linearis ships a release is a check that
  gets deleted. Drift warns. `--strict` exists for CI.

  IT DOES NOT CLASSIFY MAJOR/MINOR/PATCH. linearis versions are calendar-shaped
  (2026.8.0 is the August 2026 release), not semver, so "a minor ahead" carries no
  compatibility meaning here. The report is plain equal, ahead or behind.

  IT DOES NOT TOUCH LINEAR. `linear --version` makes no API call. `--latest` asks npm,
  which is the only network use, and is off by default.

Usage:
    python3 scripts/preflight.py
    python3 scripts/preflight.py --latest            # also ask npm for the newest release
    python3 scripts/preflight.py --strict            # drift exits 1 (for CI)
    python3 scripts/preflight.py --version 2026.9.0  # report for a version without running it
"""

import argparse
import re
import shutil
import subprocess

# THE PIN. Bump both together, and only after re-running all eight gotchas against the
# new release -- the number was never the defect; the unchecked claims behind it were.
VERIFIED = "2026.8.0"
VERIFIED_ON = "2026-09-22"

GOTCHAS = (
    "1  flag asymmetry: --project-milestone/--labels on create vs --milestone/--label on list",
    "2  milestones: create works; still no `milestones delete`",
    "3  labels: create/read/update/delete exist; an unknown label on `issues create` aborts it",
    "4  the stored token is not a raw Personal API Key (401 against GraphQL)",
    "5  --project resolves by name or UUID, never by slugId or URL slug",
    "6  `projects list` with no --limit (complexity ceiling, #276)",
    "7  `issues read`, never `get`; how a wrong verb is reported (#281)",
    "8  sub-collections are {nodes: [...]}, not bare arrays",
)

VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.]+)?")


def parse(text):
    """((y, m, p), prerelease-or-None) from the first version in text, or None."""
    m = VERSION_RE.search(text or "")
    if not m:
        return None
    return tuple(int(g) for g in m.groups()[:3]), m.group(4)


def _runner(argv):
    return lambda: subprocess.run(argv, capture_output=True, text=True, timeout=20, check=False)


def read_version(run=None):
    """(raw output, error). `run` is injectable so the tests never shell out."""
    if run is None:
        if not shutil.which("linear"):
            return "", "linear is not on PATH (npm i -g linearis)"
        run = _runner(["linear", "--version"])
    try:
        proc = run()
    except (OSError, subprocess.SubprocessError) as e:
        return "", f"could not run linear --version: {type(e).__name__}"
    if proc.returncode != 0:
        return proc.stdout or "", f"linear --version exited {proc.returncode}"
    return (proc.stdout or "").strip(), None


def read_latest(run=None):
    """(version or None, note). A failed npm lookup is a note, never a failure."""
    if run is None:
        if not shutil.which("npm"):
            return None, "npm not on PATH, newest release not checked"
        run = _runner(["npm", "view", "linearis", "version"])
    try:
        proc = run()
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"npm lookup failed: {type(e).__name__}"
    got = parse(proc.stdout) if proc.returncode == 0 else None
    if not got:
        return None, "npm lookup returned nothing usable"
    return ".".join(map(str, got[0])), None


def compare(installed, pinned):
    """'equal', 'ahead' or 'behind'. A prerelease of the pinned base counts as behind it."""
    (base_i, pre_i), (base_p, pre_p) = installed, pinned
    if base_i != base_p:
        return "ahead" if base_i > base_p else "behind"
    if pre_i == pre_p:
        return "equal"
    return "behind" if pre_i else "ahead"


def report(raw, err, latest=None, latest_note=None):
    """(exit code, drifted, lines). Exit 1 only when the check CANNOT be made."""
    if err:
        return 1, False, [f"FAIL {err}"]
    got = parse(raw)
    if not got:
        return 1, False, [f"FAIL could not parse a version out of {raw!r}"]

    shown = ".".join(map(str, got[0])) + (got[1] or "")
    state = compare(got, parse(VERIFIED))
    lines = [f"linearis {shown} -- gotchas verified against {VERIFIED} on {VERIFIED_ON}: {state.upper()}"]

    if latest:
        newer = compare(parse(latest), got) == "ahead"
        lines.append(f"npm latest {latest}" + ("  (newer than installed)" if newer else ""))
    elif latest_note:
        lines.append(f"note: {latest_note}")

    drifted = state != "equal"
    if drifted:
        lines.append("")
        relation = "newer than" if state == "ahead" else "older than"
        lines.append(f"WARN installed build is {relation} the verified one. Re-check before relying on:")
        lines += [f"  {g}" for g in GOTCHAS]
        lines.append("Then bump VERIFIED and VERIFIED_ON in this file, together.")
    return 0, drifted, lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument("--strict", action="store_true", help="exit 1 on any drift, for CI")
    ap.add_argument("--latest", action="store_true", help="also ask npm for the newest release")
    ap.add_argument("--version", help="report for this version instead of running linear")
    args = ap.parse_args(argv)

    raw, err = (args.version, None) if args.version else read_version()
    latest, note = read_latest() if args.latest else (None, None)
    code, drifted, lines = report(raw, err, latest, note)
    print("\n".join(lines))
    if args.strict and code == 0 and drifted:
        return 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
