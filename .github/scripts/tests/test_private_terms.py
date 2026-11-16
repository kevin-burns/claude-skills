"""private_terms: refuse a commit that adds a private term to this PUBLIC repo.

2026-09-05: screening regexes that together triangulated a person reached this repo;
gitleaks and the pre-commit chain both passed them. The term list lives outside the
repository (it is itself private data), and only lines a commit adds are checked.
"""
import importlib
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
pt = importlib.import_module("private_terms")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def staged_repo(path, files):
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "t@example.invalid")
    git(path, "config", "user.name", "t")
    (path / "old.md").write_text("Acme Widgets was here before.\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "base")
    for name, text in files.items():
        (path / name).write_text(text)
    git(path, "add", "-A")
    return path


def terms_file(path, text):
    f = path / "terms.txt"
    f.write_text(text)
    return f


def test_literal_terms_are_case_insensitive(tmp_path):
    repo = staged_repo(tmp_path / "r", {"a.md": "We met ACME widgets on Tuesday.\n"})
    terms = pt.load_terms(terms_file(tmp_path, "# comment\nacme widgets\n\n"))
    found = pt.added_hits(repo, terms)
    assert [(f.path, f.line) for f in found] == [("a.md", 1)]


def test_regex_terms(tmp_path):
    repo = staged_repo(tmp_path / "r", {"b.sh": "ssh host-4711\n"})
    terms = pt.load_terms(terms_file(tmp_path, r"re:\bhost-\d{4}\b" + "\n"))
    assert [f.path for f in pt.added_hits(repo, terms)] == ["b.sh"]


def test_existing_lines_are_not_rechecked(tmp_path):
    repo = staged_repo(tmp_path / "r", {"old.md": "Acme Widgets was here before.\nnew line\n"})
    terms = pt.load_terms(terms_file(tmp_path, "acme widgets\n"))
    assert pt.added_hits(repo, terms) == []


def test_hits_do_not_echo_the_term(tmp_path, capsys):
    repo = staged_repo(tmp_path / "r", {"c.md": "acme widgets\n"})
    f = terms_file(tmp_path, "acme widgets\n")
    assert pt.main(["--repo", str(repo), "--terms", str(f)]) == 1
    err = capsys.readouterr().err
    assert "c.md:1" in err and "acme" not in err.lower()


def test_missing_list_fails_closed(tmp_path):
    repo = staged_repo(tmp_path / "r", {"d.md": "fine\n"})
    assert pt.main(["--repo", str(repo), "--terms", str(tmp_path / "nope.txt")]) == 2


def test_clean_commit_passes(tmp_path):
    repo = staged_repo(tmp_path / "r", {"e.md": "nothing private\n"})
    f = terms_file(tmp_path, "acme widgets\n")
    assert pt.main(["--repo", str(repo), "--terms", str(f)]) == 0
