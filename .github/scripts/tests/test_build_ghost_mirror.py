"""Tests for the ghost-publish mirror builder.

The mirror is what strangers install, so a bad build reaches users directly
rather than being caught in review. These check the three things that would
ship broken silently: manifest shapes, relative links that only resolve in
the source repo, and caches leaking into a published tree.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from build_ghost_mirror import build, build_readme, manifests  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]


def test_build_emits_the_skill_and_all_four_manifests(tmp_path):
    files = build(ROOT, tmp_path / "out")
    for expected in (
        "ghost-publish/SKILL.md",
        "ghost-publish/README.md",
        "ghost-publish/scripts/verify_post.py",
        "ghost-publish/scripts/prepare_post.py",
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        "README.md",
        "LICENSE",
    ):
        assert expected in files, f"{expected} missing from the mirror"


def test_manifests_keep_the_shapes_this_repo_verified_by_installing(tmp_path):
    """Plugin manifests fail silently when the shape is wrong -- a bad
    marketplace `source` registered cleanly and then listed zero plugins.
    These assertions pin the shapes that are known to install."""
    build(ROOT, tmp_path / "out")
    out = tmp_path / "out"

    claude = json.loads((out / ".claude-plugin/plugin.json").read_text())
    assert claude["skills"] == ["./ghost-publish"], "skills must list a subdirectory path"

    # Claude's marketplace takes a bare string source; Codex's nests an object.
    market = json.loads((out / ".claude-plugin/marketplace.json").read_text())
    assert market["plugins"][0]["source"] == "./"

    agents = json.loads((out / ".agents/plugins/marketplace.json").read_text())
    assert agents["plugins"][0]["source"] == {"source": "local", "path": "./"}


def test_no_caches_or_virtualenvs_reach_the_published_tree(tmp_path):
    files = build(ROOT, tmp_path / "out")
    for name in files:
        assert "__pycache__" not in name
        assert not name.endswith(".pyc")
        assert ".venv" not in name
        assert ".pytest_cache" not in name


def test_readme_rewrites_the_backlink_that_would_404(tmp_path):
    """`Part of [claude-skills](../README.md)` resolves inside this repo. The
    generated front page has to point at the collection instead."""
    out = build_readme("# ghost-publish\n\nPart of [claude-skills](../README.md).\n")
    assert "../README.md" not in out
    assert "github.com/kevin-burns/claude-skills" in out


def test_readme_says_where_issues_go(tmp_path):
    """A stranger's first instinct is to open an issue where they found the
    code. The banner has to redirect that before they do."""
    out = build_readme("# ghost-publish\n\nBody.\n")
    assert "generated" in out.lower()
    assert "/issues" in out
    assert out.startswith("# ghost-publish")  # title stays first, banner follows


def test_sibling_skill_links_are_rewritten_to_the_collection():
    out = build_readme("# x\n\nUse [`clear-and-human`](../clear-and-human) for prose.\n")
    assert "(../clear-and-human)" not in out
    assert "claude-skills/tree/main/clear-and-human" in out


def test_version_is_taken_from_the_source_manifest(tmp_path):
    source_version = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"]
    built = manifests(source_version)
    assert built[".claude-plugin/plugin.json"]["version"] == source_version
    assert built[".codex-plugin/plugin.json"]["version"] == source_version


def test_rebuild_is_deterministic(tmp_path):
    """CI diffs the built tree against the mirror to decide whether to push.
    A build that varies run to run would commit noise forever."""
    first = build(ROOT, tmp_path / "a")
    second = build(ROOT, tmp_path / "b")
    assert first == second
    for name in first:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
