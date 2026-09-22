import subprocess
import sys
from pathlib import Path

# Same layout as terragrunt-skill: scripts/ goes on sys.path so the suite is self-contained.
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import preflight  # noqa: E402

# Every version in this file is expressed RELATIVE to VERIFIED, so bumping the pin never
# breaks its own tests -- the failure terragrunt-skill's suite had when it hardcoded 1.1.3.
Y, M, P = preflight.parse(preflight.VERIFIED)[0]
PINNED = preflight.VERIFIED
NEXT_MONTH = f"{Y}.{M + 1}.0"
LAST_MONTH = f"{Y}.{M - 1}.0" if M > 1 else f"{Y - 1}.12.0"
NEXT_YEAR = f"{Y + 1}.1.0"


def run(version, **kw):
    return preflight.report(version, None, **kw)


def fake(stdout="", returncode=0, raises=None):
    def _run():
        if raises:
            raise raises
        return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")
    return _run


# ---------------------------------------------------------------------------
# Comparison. Plain equal / ahead / behind -- linearis versions are calendar-shaped,
# so nothing here reads meaning into which field moved.
# ---------------------------------------------------------------------------

def test_the_pinned_version_is_equal_and_quiet():
    code, drifted, lines = run(PINNED)
    assert (code, drifted) == (0, False)
    assert "EQUAL" in lines[0]
    assert "WARN" not in "\n".join(lines)


def test_a_newer_release_is_ahead_and_names_all_eight_gotchas():
    """The case that went unnoticed for six weeks: an upgrade the skill never re-checked."""
    code, drifted, lines = run(NEXT_MONTH)
    out = "\n".join(lines)
    assert (code, drifted) == (0, True)
    assert "AHEAD" in lines[0]
    for n in range(1, 9):
        assert f"\n  {n}  " in out, f"gotcha {n} not named"


def test_an_older_release_is_behind():
    code, drifted, lines = run(LAST_MONTH)
    assert (code, drifted) == (0, True)
    assert "BEHIND" in lines[0]


def test_a_year_boundary_compares_numerically_not_lexically():
    """2027.1.0 must be ahead of 2026.12.0; a string compare gets this wrong."""
    assert preflight.compare(preflight.parse(NEXT_YEAR), preflight.parse(f"{Y}.12.0")) == "ahead"


def test_a_prerelease_of_the_pinned_base_is_behind_it():
    """linearis publishes -next.N builds; 2026.8.0-next.2 predates 2026.8.0."""
    code, drifted, lines = run(f"{PINNED}-next.2")
    assert drifted and "BEHIND" in lines[0]


def test_the_version_is_found_inside_surrounding_text():
    code, drifted, _ = run(f"linearis version {PINNED}\n")
    assert (code, drifted) == (0, False)


# ---------------------------------------------------------------------------
# Failure is reserved for a check that cannot be made. Drift is never a failure
# unless --strict asks for it.
# ---------------------------------------------------------------------------

def test_unparseable_output_fails_rather_than_guessing():
    code, _, lines = run("not a version")
    assert code == 1 and lines[0].startswith("FAIL")


def test_a_missing_binary_is_reported_as_a_failure():
    code, _, lines = preflight.report("", "linear is not on PATH")
    assert code == 1 and "not on PATH" in lines[0]


def test_drift_does_not_fail_by_default_but_does_under_strict():
    assert preflight.main(["--version", NEXT_MONTH]) == 0
    assert preflight.main(["--version", NEXT_MONTH, "--strict"]) == 1
    assert preflight.main(["--version", PINNED, "--strict"]) == 0


def test_strict_still_fails_an_unreadable_version():
    assert preflight.main(["--version", "garbage", "--strict"]) == 1


# ---------------------------------------------------------------------------
# The runners are injected, so none of these touch the real CLI or npm.
# ---------------------------------------------------------------------------

def test_read_version_passes_through_a_clean_run():
    raw, err = preflight.read_version(fake(stdout=f"{PINNED}\n"))
    assert (raw, err) == (PINNED, None)


def test_read_version_reports_a_nonzero_exit():
    _, err = preflight.read_version(fake(returncode=3))
    assert "exited 3" in err


def test_read_version_survives_the_binary_vanishing_mid_call():
    _, err = preflight.read_version(fake(raises=FileNotFoundError()))
    assert "FileNotFoundError" in err


def test_a_failed_npm_lookup_is_a_note_not_a_failure():
    latest, note = preflight.read_latest(fake(returncode=1))
    assert latest is None and note
    code, _, lines = run(PINNED, latest=latest, latest_note=note)
    assert code == 0 and any(line.startswith("note:") for line in lines)


def test_npm_latest_newer_than_installed_is_flagged():
    latest, _ = preflight.read_latest(fake(stdout=f"{NEXT_MONTH}\n"))
    _, _, lines = run(PINNED, latest=latest)
    assert any("newer than installed" in line for line in lines)


def test_the_pin_and_its_date_are_both_set():
    """They move together; an empty date means someone bumped half of it."""
    assert preflight.parse(preflight.VERIFIED)
    assert len(preflight.VERIFIED_ON) == 10 and preflight.VERIFIED_ON[4] == "-"
