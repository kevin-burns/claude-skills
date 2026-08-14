#!/usr/bin/env python3
"""Build the standalone ghost-publish repo from this one.

`ghost-publish` is the one skill here with an audience outside this repo:
Ghost writers looking for it will never find it inside a 22-skill personal
collection, and every competing skill is standalone. So it gets its own repo
for discoverability -- but a hand-maintained copy would drift, and a drifted
copy is worse than no copy.

So the mirror is a BUILD ARTIFACT. This repo stays the single source of
truth, CI regenerates the mirror on every merge, and nobody edits the mirror
by hand. Issues raised there route back here, which is stated on the
generated front page.

The layout it emits deliberately matches this repo's proven one -- skill in
a subdirectory, `skills` listing `./ghost-publish` -- because plugin
manifests here fail SILENTLY when the shape is wrong: a marketplace with a
bad `source` registered cleanly and listed zero plugins. Reusing a shape
that is known to install is worth more than a tidier one that is not.

Standard library only. Writes a directory; never touches git or the network.
"""

import argparse
import json
import re
import shutil
from pathlib import Path

SKILL = "ghost-publish"
REPO_URL = "https://github.com/kevin-burns/claude-skills"
OWNER = {"name": "Kevin Burns", "url": "https://github.com/kevin-burns"}

# Files copied verbatim from the repo root into the mirror root.
ROOT_FILES = ("LICENSE",)

GENERATED_BANNER = f"""> **This repository is generated.** `{SKILL}` is developed in
> [kevin-burns/claude-skills]({REPO_URL}) and mirrored here on every merge, so that Ghost
> users can find and install it on its own. **Please raise issues and pull requests
> [in the source repository]({REPO_URL}/issues)** — changes made here would be overwritten by
> the next build.

"""


def build_readme(skill_readme: str) -> str:
    """The skill's own README, re-pointed for a repo where it is the whole
    project rather than one of twenty-two."""
    text = skill_readme
    # The in-repo backlink resolves to nothing once the skill is the root
    # project, so it becomes a forward link to the collection instead.
    text = text.replace(
        "Part of [claude-skills](../README.md).",
        f"Part of the [claude-skills]({REPO_URL}) collection, and mirrored here as a "
        "standalone plugin.",
    )
    # Sibling-skill references are relative paths that only resolve in the
    # source repo. Point them at the collection rather than leaving 404s.
    text = re.sub(
        r"\[`?([a-z0-9-]+)`?\]\(\.\./([a-z0-9-]+)\)",
        rf"[`\1`]({REPO_URL}/tree/main/\2)",
        text,
    )
    title, _, body = text.partition("\n")
    return f"{title}\n\n{GENERATED_BANNER}{body.lstrip()}"


def manifests(version: str) -> dict[str, dict]:
    """Claude and Codex plugin manifests plus both marketplaces, in the shape
    this repo has verified by installing rather than by validating."""
    description = (
        "Publish, update, schedule and verify Ghost posts from a markdown file, driving "
        "TryGhost's official ghst CLI. Strips front matter Ghost would render as prose, and "
        "diffs what Ghost actually stored against the source in both directions."
    )
    homepage = f"https://github.com/kevin-burns/{SKILL}"
    claude_plugin = {
        "name": SKILL,
        "version": version,
        "description": description,
        "author": OWNER,
        "homepage": homepage,
        "license": "MIT",
        "skills": [f"./{SKILL}"],
    }
    claude_market = {
        "name": "ghost-publish",
        "description": f"The {SKILL} skill for Claude Code.",
        "owner": OWNER,
        "plugins": [{
            "name": SKILL,
            "source": "./",
            "description": description,
            "author": OWNER,
            "homepage": homepage,
            "license": "MIT",
            "category": "Productivity",
        }],
    }
    codex_plugin = {
        "name": SKILL,
        "version": version,
        "description": description,
        "skills": [f"./{SKILL}"],
        "interface": {
            "displayName": "Ghost Publish",
            "category": "Productivity",
            "defaultPrompt": [
                "Publish this markdown file to my Ghost blog as a draft",
                "Check that the Ghost post matches my source file",
                "Schedule this post for 07:00 tomorrow",
            ],
        },
    }
    # Codex marketplaces nest `source` as an object; the bare string Claude
    # uses registers cleanly here and then lists zero plugins.
    agents_market = {
        "name": "ghost-publish",
        "interface": {"displayName": "Ghost Publish"},
        "plugins": [{
            "name": SKILL,
            "source": {"source": "local", "path": "./"},
            "policy": {"installation": "AVAILABLE"},
            "category": "Productivity",
        }],
    }
    return {
        ".claude-plugin/plugin.json": claude_plugin,
        ".claude-plugin/marketplace.json": claude_market,
        ".codex-plugin/plugin.json": codex_plugin,
        ".agents/plugins/marketplace.json": agents_market,
    }


def build(root: Path, out: Path) -> list[str]:
    src = root / SKILL
    if not (src / "SKILL.md").is_file():
        raise SystemExit(f"no {SKILL}/SKILL.md under {root} -- wrong --root?")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    written: list[str] = []
    # The skill itself, minus caches that would otherwise ship to users.
    shutil.copytree(
        src, out / SKILL,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".venv"),
    )
    written += [str(p.relative_to(out)) for p in sorted((out / SKILL).rglob("*")) if p.is_file()]

    for name in ROOT_FILES:
        if (root / name).is_file():
            shutil.copy2(root / name, out / name)
            written.append(name)

    version = json.loads((root / ".claude-plugin/plugin.json").read_text())["version"]
    for path, payload in manifests(version).items():
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written.append(path)

    (out / "README.md").write_text(
        build_readme((src / "README.md").read_text(encoding="utf-8")), encoding="utf-8")
    written.append("README.md")
    return sorted(written)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    parser.add_argument("--root", default=".", help="the claude-skills checkout")
    parser.add_argument("--out", required=True, help="directory to build into (recreated)")
    args = parser.parse_args()

    files = build(Path(args.root).resolve(), Path(args.out).resolve())
    print(f"built {len(files)} files into {args.out}")
    for name in files:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
