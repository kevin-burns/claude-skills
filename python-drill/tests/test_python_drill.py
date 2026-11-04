"""Tests for python-drill: progress tracking, the test runner, the exercise generator, and the
recorded outputs in the reference docs (re-run, so a doc cannot drift from what Python does)."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
REFS = SKILL / "references"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mv = load("make_variant")


def run(args, home, cwd=None, today=None):
    env = {"PATH": os.environ.get("PATH", ""), "PYTHON_DRILL_HOME": str(home)}
    if today:
        env["PYTHON_DRILL_TODAY"] = today
    return subprocess.run(
        [sys.executable, "-I", *map(str, args)],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        timeout=120,
        check=False,
    )


# --------------------------------------------------------------------------- SKILL.md


def frontmatter():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    block = text.split("---")[1]
    return dict(re.findall(r'^(\w+): "?(.*?)"?$', block, re.M))


def test_frontmatter_name_license_and_description_length():
    fm = frontmatter()
    assert fm["name"] == SKILL.name == "python-drill"
    assert fm["license"] == "MIT"
    assert len(fm["description"]) <= 1024


def test_no_personal_or_book_text_references():
    banned = re.compile(r"kevin(?!-burns)|larkspur|python-tutor|book-texts|purchased|harrison-effective", re.I)
    hits = [
        f"{p.relative_to(SKILL)}:{i}"
        for p in SKILL.rglob("*")
        if p.is_file() and p.suffix in {".md", ".py"} and p.name != "test_python_drill.py"
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if banned.search(line)
    ]
    assert hits == []


def test_every_referenced_path_exists():
    missing = []
    for doc in [SKILL / "SKILL.md", *REFS.glob("*.md")]:
        for ref in re.findall(r"`((?:references|scripts|fixtures)/[^`\s<*]+)`", doc.read_text(encoding="utf-8")):
            if not (SKILL / ref.rstrip("/")).exists():
                missing.append((doc.name, ref))
    assert missing == []


def curriculum_ids():
    return set(re.findall(r"^- `([^`]+)` \[", (REFS / "curriculum.md").read_text(encoding="utf-8"), re.M))


def test_generator_topics_are_all_in_the_curriculum():
    assert set(mv.covered_topics()) - curriculum_ids() == set()


# --------------------------------------------------------------------------- progress.py


def test_progress_box_moves_and_due_order(tmp_path):
    p = SCRIPTS / "progress.py"
    assert run([p, "record", "core.sets", "pass"], tmp_path, today="2026-01-01").returncode == 0
    assert run([p, "record", "core.sets", "pass"], tmp_path, today="2026-01-02").returncode == 0
    r = run([p, "record", "core.slicing", "fail", "--note=-1 is the last item"], tmp_path, today="2026-01-02")
    assert r.returncode == 0, r.stderr
    state = json.loads((tmp_path / "progress.json").read_text())
    assert state["topics"]["core.sets"]["box"] == 3
    assert state["topics"]["core.slicing"]["box"] == 1
    due = run([p, "due", "--n", "2"], tmp_path, today="2026-01-03").stdout
    assert due.splitlines()[0].startswith("core.slicing")  # seen and weak comes first


def test_progress_rejects_unknown_topic_and_track(tmp_path):
    p = SCRIPTS / "progress.py"
    assert run([p, "record", "core.nope", "pass"], tmp_path).returncode != 0
    assert run([p, "due", "--track", "nope"], tmp_path).returncode != 0


# --------------------------------------------------------------------------- run_tests.py

SOLUTION = "def dedupe(xs):\n    return list(dict.fromkeys(xs))\n"


def runner(tmp_path, tests, solution=SOLUTION, *extra):
    (tmp_path / "s.py").write_text(solution)
    (tmp_path / "t.py").write_text(tests)
    return run([SCRIPTS / "run_tests.py", tmp_path / "s.py", tmp_path / "t.py", *extra], tmp_path)


def test_runner_counts_failures_and_keeps_going(tmp_path):
    r = runner(
        tmp_path,
        'check("ok", dedupe([1, 1]), [1])  # comment\n'
        'check(\n    "multi, line",\n    dedupe([2]),\n    [2],\n)\n'
        'check("wrong", dedupe([1]), [9])\n'
        'check("boom, comma", dedupe(None), [])\n'
        'check("raises", raises(lambda: dedupe(None), TypeError), True)\n',
    )
    assert r.returncode == 2
    assert "3/5 passed" in r.stdout
    assert "FAIL boom, comma" in r.stdout


def test_runner_refuses_bare_raises_and_empty_tests(tmp_path):
    assert runner(tmp_path, "raises(lambda: dedupe(None), TypeError)\n").returncode == 103
    assert runner(tmp_path, "x = 1\n").returncode == 103


def test_runner_reports_early_exit_not_success(tmp_path):
    assert runner(tmp_path, 'check("a", 1, 1)\n', "import sys\nsys.exit(0)\n").returncode == 104
    assert runner(tmp_path, 'x = 1 / 0\ncheck("a", 1, 1)\n').returncode == 104


def test_runner_timeout(tmp_path):
    r = runner(tmp_path, 'check("a", 1, 1)\n', "while True:\n    pass\n", "--timeout", "1")
    assert r.returncode == 102


# --------------------------------------------------------------------------- make_variant.py


@pytest.mark.parametrize("family", list(mv.FAMILIES))
def test_family_is_deterministic_varied_and_valid(family, tmp_path):
    seeds = range(120)
    hashes = {mv.build(family, s)["hash"] for s in seeds}
    assert len(hashes) >= 0.9 * len(seeds)
    assert all(mv.build(family, s)["hash"] == mv.build(family, s)["hash"] for s in range(10))
    for s in range(12):
        ex = mv.build(family, s)
        ast.parse(ex["script"])
        a = mv.run(ex, tmp_path / f"{s}a")
        b = mv.run(ex, tmp_path / f"{s}b")
        assert (a["stdout"], a["error"]) == (b["stdout"], b["error"])
        assert a["error"] is None or "timeout" not in a["error"]
        assert sorted(f.name for f in (tmp_path / f"{s}a").iterdir()) == sorted(
            {"script.py", ex["input_name"]} - {None}
        )  # no app.db or other run artefacts


def first(family, pred, limit=3000):
    for s in range(limit):
        ex = mv.build(family, s)
        if pred(ex):
            return ex
    raise AssertionError(f"no {family} exercise matched")


def test_planted_problems_name_the_bug_that_actually_fires(tmp_path):
    ex = first("sql", lambda e: e["kind"] == "sql/executemany" and "[0] for r" not in e["script"] and not e["defects"])
    assert "ProgrammingError" in (mv.run(ex, tmp_path / "em")["error"] or "")
    assert any("executemany" in p for p in mv.planted_problems(ex))

    ex = first(
        "sql",
        lambda e: (
            e["kind"] == "sql/rerun" and "UNIQUE" in e["script"] and '"INSERT INTO' in e["script"] and not e["defects"]
        ),
    )
    assert "IntegrityError" in (mv.run(ex, tmp_path / "rr")["error"] or "")
    assert any("IntegrityError" in p for p in mv.planted_problems(ex))


def test_new_never_repeats_and_hides_the_answer(tmp_path):
    out = tmp_path / "out"
    seen_ids = set()
    for _ in range(25):
        r = run([SCRIPTS / "make_variant.py", "new", "--rotate", "--out", out], tmp_path)
        assert r.returncode == 0, r.stderr
        shown = json.loads(r.stdout)
        assert set(shown) == {"id", "script", "input", "question", "answer_file", "seen_total"}
        assert Path(shown["answer_file"]).parent.name == "answers"
        assert Path(shown["script"]).parent != Path(shown["answer_file"]).parent
        seen_ids.add(shown["id"])
    assert len(seen_ids) == 25
    last = run([SCRIPTS / "make_variant.py", "last"], tmp_path).stdout
    assert "/" not in last  # family only, never the kind that names the bug


def test_uncovered_topic_exits_3(tmp_path):
    mvp = SCRIPTS / "make_variant.py"
    assert run([mvp, "new", "--topic", "core.big-o", "--out", tmp_path], tmp_path).returncode == 3
    assert (
        run([mvp, "new", "--family", "mailbox", "--topic", "rv.sql-safety", "--out", tmp_path], tmp_path).returncode
        == 3
    )


# --------------------------------------------------------------------------- reference docs


def test_string_ops_reference_matches_python(tmp_path):
    """Every row of string-ops.md is re-run as a tiny script, so the doc cannot drift."""
    text = (REFS / "string-ops.md").read_text(encoding="utf-8")
    rows, line_src = [], None
    for raw in text.splitlines():
        m = re.match(r"^`line = (.+)`$", raw)
        if m:
            line_src = m.group(1)
            continue
        m = re.match(r"^\| `(.+?)` \| (.+?) \|", raw)
        if m and line_src is not None:
            rows.append((line_src, *m.groups()))
    assert len(rows) >= 30
    for i, (line_src, expr, shown) in enumerate(rows):
        script = tmp_path / f"row{i}.py"
        script.write_text(
            f"line = {line_src}\ntry:\n    print('`' + repr({expr}) + '`')\n"
            "except Exception as e:\n    print('**' + type(e).__name__ + '**')\n"
        )
        got = run([script], tmp_path).stdout.strip()
        assert got == (shown if shown.startswith("`") else shown.split(":")[0]), expr


SCENARIO_OUTPUTS = {  # script -> (input, substring of the real output or error)
    "mailbox/m1_separator_index.py": ("sample.mbox", "['Jan', 'Jan', 'Jan']"),
    "mailbox/m2_header_sender.py": ("sample.mbox", "'\"Bo'"),
    "mailbox/m3_startswith_from.py": ("sample.mbox", "'ada.lane@example.org': 2"),
    "mailbox/m6_subject_word.py": ("sample.mbox", "IndexError"),
    "regex/r2_search_first_only.py": ("contacts.txt", "None]"),
    "csvjson/c2_split_comma.py": ("orders.csv", "too many values to unpack"),
    "csvjson/j1_weather.py": ("weather.json", "IndexError"),
    "dates/d2_mutable_default.py": (None, "['eu', 'us'] ['eu', 'us'] ['apac']"),
    "gotchas/g1_remove_while_iterating.py": (None, "['web1', 'tmp-b', 'db1']"),
    "gotchas/g2_late_binding.py": (None, "['deploy to prod', 'deploy to prod', 'deploy to prod']"),
    "gotchas/g4_exhausted_generator.py": (None, "3 []"),
    "gotchas/g5_bare_except.py": (None, "80 8080 8080 8080"),
}


@pytest.mark.parametrize("script", sorted(SCENARIO_OUTPUTS))
def test_fixed_scenarios_print_what_the_doc_says(script, tmp_path):
    inp, expected = SCENARIO_OUTPUTS[script]
    args = [SKILL / "fixtures/scenarios" / script] + ([SKILL / "fixtures" / inp] if inp else [])
    r = run(args, tmp_path, cwd=tmp_path)
    assert expected in r.stdout + r.stderr
