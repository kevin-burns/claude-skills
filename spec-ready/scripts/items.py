"""The planning items a spec depends on, and which of them may stay a guess.

This is the gate's policy. A repository may add items or drop optional ones in
`.spec-ready/items.json`; it may not drop the three that most often go unsaid and most often
cause rework: the anti-goal, the success check and the verification strategy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class ItemsError(ValueError):
    pass


@dataclass(frozen=True)
class Item:
    key: str
    label: str
    definition: str
    may_be_guessed: bool


DEFAULT_ITEMS: tuple[Item, ...] = (
    Item("goal", "Goal", "What changes, and for whom, when this works?", False),
    Item("audience", "Who it is for", "Who exactly is this for (a named kind of user, not 'users')?", False),
    Item("non_goals", "Non-goals", "What is this deliberately not going to do?", False),
    Item("anti_goal", "Anti-goal", "What would make this a failure even if it technically works?", False),
    Item("success_check", "Success check", "How will the person know it worked?", False),
    Item("verification", "Verification strategy",
         "How will the work be checked: TDD, combinatorial coverage, evals/ablation, "
         "or a live probe versus a fake?", False),
    Item("boundaries", "Boundaries touched",
         "Does this create or move a component boundary, and which one (or does the person say none)?", False),
    Item("risks", "Risks and assumptions", "What could go wrong or is being assumed?", True),
)

CORE_KEYS = frozenset({"anti_goal", "success_check", "verification"})


def _item(entry: object) -> Item:
    if not isinstance(entry, dict):
        raise ItemsError(f"an added item must be an object, got {entry!r}")
    try:
        item = Item(str(entry["key"]), str(entry["label"]), str(entry["definition"]),
                    bool(entry.get("may_be_guessed", False)))
    except KeyError as missing:
        raise ItemsError(f"added item lacks {missing}") from None
    if not item.definition.endswith("?"):
        raise ItemsError(f"definition of {item.key!r} must be a question")
    return item


def load_items(repo: Path) -> tuple[Item, ...]:
    path = repo / ".spec-ready" / "items.json"
    if not path.is_file():
        return DEFAULT_ITEMS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ItemsError(f"{path}: {error}") from None
    remove = set(data.get("remove", []))
    if blocked := remove & CORE_KEYS:
        raise ItemsError(f"these items cannot be removed: {', '.join(sorted(blocked))}")
    items = [i for i in DEFAULT_ITEMS if i.key not in remove]
    known = {i.key for i in items}
    for entry in data.get("add", []):
        item = _item(entry)
        if item.key in known:
            raise ItemsError(f"duplicate item {item.key!r}")
        items.append(item)
        known.add(item.key)
    return tuple(items)
