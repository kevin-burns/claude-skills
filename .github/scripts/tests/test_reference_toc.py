"""reference_toc: the generated contents list for long skill reference files (claude-skills-b9nk.1)."""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
rt = importlib.import_module("reference_toc")


def long_doc(*sections, pad=120):
    body = "".join(f"## {s}\n\ntext\n\n" for s in sections)
    return "# Title\n\nIntro.\n\n" + body + "filler\n" * pad


def make_skill(tmp_path, text, name="refs.md"):
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "SKILL.md").write_text("---\nname: s\n---\n")
    (tmp_path / "s" / "references").mkdir()
    p = tmp_path / "s" / "references" / name
    p.write_text(text)
    return p


def test_inserts_after_the_h1_and_is_idempotent():
    once = rt.with_block(long_doc("Alpha", "Beta", "Gamma"))
    assert once.startswith("# Title\n\n" + rt.MARK_START)
    assert "- [Alpha](#alpha)" in once and "- [Gamma](#gamma)" in once
    assert rt.with_block(once) == once


def test_a_missing_list_and_a_stale_list_both_fail_the_check(tmp_path):
    p = make_skill(tmp_path, long_doc("Alpha", "Beta", "Gamma"))
    assert [why for _, why in rt.problems(tmp_path)] == ["over 100 lines with no generated contents list"]
    p.write_text(rt.with_block(p.read_text()))
    assert rt.problems(tmp_path) == []
    p.write_text(p.read_text().replace("## Beta", "## Beta renamed"))
    assert [why for _, why in rt.problems(tmp_path)] == ["contents list is stale; headings have changed"]


def test_short_files_are_left_alone(tmp_path):
    make_skill(tmp_path, "# T\n\n## A\n## B\n## C\n")
    assert rt.problems(tmp_path) == []


def test_headings_inside_code_fences_are_not_listed():
    doc = long_doc("Alpha", "Beta", "Gamma").replace("## Beta\n", "```\n## Not a heading\n```\n## Beta\n")
    assert "Not a heading" not in rt.build_block(doc)


def test_duplicate_headings_get_githubs_numbered_anchors():
    block = rt.build_block(long_doc("Setup", "Use", "Setup"))
    assert "(#setup)" in block and "(#setup-1)" in block


def test_falls_back_to_h3_only_when_that_is_where_the_structure_is():
    banks = "# Bank\n\n## Intro\n\n" + "".join(f"### Q{i} Question\n\nx\n\n" for i in range(5)) + "y\n" * 120
    assert "- [Q0 Question](#q0-question)" in rt.build_block(banks)
    two_h2_no_h3 = "# T\n\n## One\n\n## Two\n\n" + "z\n" * 120
    assert "- [One](#one)" in rt.build_block(two_h2_no_h3)
