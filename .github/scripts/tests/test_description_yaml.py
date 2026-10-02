"""check_conventions.description_yaml_problem: the two shapes that broke seven skills (claude-skills-b9nk)."""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
cc = importlib.import_module("check_conventions")


def test_block_indicator_with_text_on_the_same_line_fails():
    assert cc.description_yaml_problem("name: x\ndescription: > Write things\n")


def test_unquoted_value_with_colon_space_fails():
    assert cc.description_yaml_problem("name: x\ndescription: Use when the user wants to: write\n")
    assert cc.description_yaml_problem("name: x\ndescription: first line\n  then wants to: write\n")


def test_valid_shapes_pass():
    assert cc.description_yaml_problem("name: x\ndescription: >-\n  Use when the user wants to: write\n") is None
    assert cc.description_yaml_problem('name: x\ndescription: "a: b"\n') is None
    assert cc.description_yaml_problem("name: x\ndescription: plain text, no colon space\n") is None
