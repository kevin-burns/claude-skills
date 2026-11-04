#!/usr/bin/env python3
"""Run a candidate solution against a test file in a fresh, isolated interpreter. Stdlib only.

    run_tests.py SOLUTION.py TESTS.py [--pandas] [--timeout 10]

The two files are joined into one script (solution first, then a `check` helper, then the
tests) and run with `python -I`, so nothing from the current directory, PYTHONPATH or user
site-packages leaks in. With --pandas the script runs under `uv run --with pandas`.

Tests are top-level calls to check(name, got, expected); every case runs even after a
failure. A check may span several lines or carry a trailing comment. An exception inside a
check is a failed case, not a crash. To test that something raises, wrap raises() in check():

    check("empty list", dedupe([]), [])
    check("raises on None", raises(lambda: dedupe(None), TypeError), True)

A bare top-level raises(...) line is refused (exit 103), because it would test nothing.

Exit status: 0 all passed · 1-100 number of failed cases (capped) · 101 uv missing ·
102 timeout · 103 bad tests file · 104 the run ended before the summary (a crash or sys.exit in the solution or setup).
"""

from __future__ import annotations

import argparse
import ast
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = r"""
# ---- harness (python-drill) ----
import sys as _sys
_results = []
def check(name, got, expected):
    ok = got == expected
    _results.append(ok)
    print(((
        "PASS "
    ) if ok else "FAIL ") + name + ("" if ok else f"\n     got:      {got!r}\n     expected: {expected!r}"))
def raises(fn, exc=Exception):
    try:
        fn()
    except exc:
        return True
    except BaseException as e:
        return f"raised {type(e).__name__}: {e}"
    return False
# ---- tests ----
"""

FOOTER = r"""
# ---- summary ----
print(f"\n{sum(_results)}/{len(_results)} passed")
_sys.exit(min(100, _results.count(False)))
"""


class TestsFileError(Exception):
    pass


def wrap_tests(tests: str) -> str:
    """Wrap each top-level check(...) statement in try/except so an exception in one case does not
    stop the rest. Uses the AST, so multi-line checks and trailing comments are handled. Other
    top-level statements (imports, setup) pass through unchanged."""
    try:
        tree = ast.parse(tests)
    except SyntaxError as e:
        raise TestsFileError(f"tests file does not parse: line {e.lineno}: {e.msg}") from e
    lines = tests.splitlines()
    out: list[str] = []
    cursor = 0  # index into lines of the next line not yet emitted
    for node in tree.body:
        call = node.value if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) else None
        fname = call.func.id if call is not None and isinstance(call.func, ast.Name) else None
        if fname == "raises":
            raise TestsFileError(
                f"line {node.lineno}: bare raises(...) tests nothing; "
                "write check(name, raises(lambda: ..., ExcType), True)"
            )
        if fname != "check":
            continue
        out.extend(lines[cursor : node.lineno - 1])
        src = ast.get_source_segment(tests, node)
        name = "?"
        if call.args and isinstance(call.args[0], ast.Constant):
            name = str(call.args[0].value)
        out.append("try:")
        out.extend("    " + x for x in src.splitlines())
        out.append("except BaseException as _err:")
        out.append("    _results.append(False)")
        out.append(f"    print('FAIL ' + {name!r} + '\\n     error:    ' + type(_err).__name__ + ': ' + str(_err))")
        cursor = node.end_lineno
    out.extend(lines[cursor:])
    if not any(
        isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Name)
        and n.value.func.id == "check"
        for n in tree.body
    ):
        raise TestsFileError("no top-level check(...) calls: nothing would be tested")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("solution")
    ap.add_argument("tests")
    ap.add_argument("--pandas", action="store_true")
    ap.add_argument("--timeout", type=float, default=10.0)
    a = ap.parse_args(argv)

    try:
        wrapped = wrap_tests(Path(a.tests).read_text(encoding="utf-8"))
    except TestsFileError as e:
        print(f"BAD TESTS FILE: {e}")
        return 103
    script = Path(a.solution).read_text(encoding="utf-8") + "\n" + HARNESS + wrapped + FOOTER
    with tempfile.TemporaryDirectory(prefix="python-drill-") as d:
        combined = Path(d) / "run.py"
        combined.write_text(script, encoding="utf-8")
        if a.pandas:
            uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
            if not Path(uv).exists():
                print("uv not found; cannot run a pandas exercise", file=sys.stderr)
                return 101
            cmd = [uv, "run", "--no-project", "--quiet", "--with", "pandas", "python", "-I", str(combined)]
        else:
            cmd = [sys.executable, "-I", str(combined)]
        try:
            proc = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=a.timeout, check=False)
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT after {a.timeout:g}s (infinite loop, or a very slow solution)")
            return 102
    sys.stdout.write(proc.stdout)
    if proc.stderr.strip():
        sys.stdout.write("\n--- stderr ---\n" + proc.stderr)
    out_lines = proc.stdout.strip().splitlines()
    summary = out_lines[-1] if out_lines else ""
    if not summary.endswith(" passed"):
        print("\nCRASH outside any check: the solution or setup code raised (see stderr)")
        return 104
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
