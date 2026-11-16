"""no_new_suppressions: refuse a commit that ADDS a lint or security suppression.

Kevin, 2026-09-24: "Don't introduce exclusions in code smells." An inline noqa on a urlopen
hid a finding that bandit still raised, and public CI went red. Existing suppressions are left
alone; only lines a commit adds are checked.
"""
import importlib
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
nns = importlib.import_module("no_new_suppressions")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def repo_with(tmp_path, files):
    tmp_path.mkdir(parents=True, exist_ok=True)
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.invalid")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "old.py").write_text("import os  # noqa: F401\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    git(tmp_path, "add", "-A")
    return tmp_path


def test_flags_added_noqa_and_nosec(tmp_path):
    repo = repo_with(tmp_path, {
        "a.py": "x = 1  # noqa: E501\n",
        "b.py": "subprocess.run(cmd, shell=True)  # nosec B602\n",
        "c.sh": "eval \"$x\"  # noqa\n",
    })
    found = nns.added_suppressions(repo)
    assert {f.path for f in found} == {"a.py", "b.py", "c.sh"}


def test_ignores_existing_suppressions_and_prose(tmp_path):
    repo = repo_with(tmp_path, {
        "old.py": "import os  # noqa: F401\nimport sys\n",
        "doc.md": "Never add `# noqa`; fix the smell.\n",
        "baseline.json": '{"nosec": 0}\n',
        "d.py": 'print("we never add noqa here")\n',
    })
    assert nns.added_suppressions(repo) == []


def test_flags_new_ignore_config(tmp_path):
    repo = repo_with(tmp_path, {
        "pyproject.toml": '[tool.ruff.lint.per-file-ignores]\n"x.py" = ["E501"]\n',
    })
    found = nns.added_suppressions(repo)
    assert [f.path for f in found] == ["pyproject.toml"]


def test_main_exit_codes(tmp_path, capsys):
    clean = repo_with(tmp_path / "clean", {"e.py": "y = 2\n"})
    assert nns.main(["--repo", str(clean)]) == 0
    dirty = repo_with(tmp_path / "dirty", {"f.py": "y = 2  # noqa\n"})
    assert nns.main(["--repo", str(dirty)]) == 1
    assert "f.py:1" in capsys.readouterr().err


def test_python_strings_are_not_comments(tmp_path):
    repo = repo_with(tmp_path, {"g.py": 'sample = "x = 1  # noqa: E501"\nreal = 1  # noqa: E501\n'})
    found = nns.added_suppressions(repo)
    assert [(f.path, f.line) for f in found] == [("g.py", 2)]
