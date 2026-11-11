"""Required items: the default list, its pass rules, and what a repository may change."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from items import CORE_KEYS, DEFAULT_ITEMS, ItemsError, load_items

KEYS = ["goal", "audience", "non_goals", "anti_goal", "success_check", "verification", "boundaries", "risks"]


def extension(tmp_path: Path, data: dict) -> Path:
    (tmp_path / ".spec-ready").mkdir()
    (tmp_path / ".spec-ready" / "items.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


def test_default_order():
    assert [i.key for i in DEFAULT_ITEMS] == KEYS


def test_only_risks_may_be_guessed():
    assert {i.key for i in DEFAULT_ITEMS if i.may_be_guessed} == {"risks"}


def test_definitions_are_plain_questions():
    assert all(i.definition.endswith("?") for i in DEFAULT_ITEMS)
    anti = next(i for i in DEFAULT_ITEMS if i.key == "anti_goal")
    assert anti.definition == "What would make this a failure even if it technically works?"


def test_repo_can_add_and_remove(tmp_path):
    repo = extension(tmp_path, {
        "add": [{"key": "privacy", "label": "Privacy", "definition": "What personal data does it touch?",
                 "may_be_guessed": False}],
        "remove": ["non_goals"],
    })
    keys = [i.key for i in load_items(repo)]
    assert "non_goals" not in keys and keys[-1] == "privacy"


def test_core_items_cannot_be_removed(tmp_path):
    repo = extension(tmp_path, {"remove": ["anti_goal"]})
    with pytest.raises(ItemsError):
        load_items(repo)
    assert {"anti_goal", "success_check", "verification"} == CORE_KEYS


def test_no_file_means_defaults(tmp_path):
    assert load_items(tmp_path) == DEFAULT_ITEMS
