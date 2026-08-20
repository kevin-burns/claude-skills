#!/usr/bin/env python3
"""Structural checks for the skills in this repo. Standard library only.

Scope, stated plainly: this validates STRUCTURE, not quality. Most skills
here are prose, and nothing automated can tell you whether a skill's
instructions are good. What it catches is the drift that accumulates
silently across twenty-odd skills -- a renamed directory, a missing
README, a config example that no longer parses, a link to a file somebody
moved.

The one failure mode it cannot see is the one that actually bites a repo
this size: two skill descriptions overlapping so a request routes to the
wrong skill. That needs a model, so it lives outside CI.

Run: python3 .github/scripts/check_conventions.py
Exits non-zero on any failure.
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Skills that predate the README convention. New skills must ship one, so
# this list may shrink but must never grow -- a check enforces that below.
#
# Shrunk 2026-08-05 from fourteen to seven: the skills someone might plausibly
# INSTALL without reading SKILL.md were done first, because that is where a
# README earns its keep. What remains is small, self-evident, or personal
# tooling. See claude-skills-xrs.
README_GRANDFATHERED = {
    "convert-to-webp", "dev-fleet", "hook-and-human",
    "markdown-converter", "social-image-prep", "use-linearis",
}

failures = []
notes = []


def fail(where, message):
    failures.append(f"{where}: {message}")


def skill_dirs():
    return sorted(p for p in ROOT.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def check_frontmatter(skill):
    """name must match the directory, or the skill cannot be invoked by path."""
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        return fail(skill.name, "SKILL.md has no YAML frontmatter")
    block = match.group(1)
    name = re.search(r"^name:\s*(\S+)", block, re.M)
    if not name:
        fail(skill.name, "SKILL.md frontmatter has no 'name:'")
    elif name.group(1) != skill.name:
        fail(skill.name, f"frontmatter name is {name.group(1)!r}, directory is {skill.name!r}")
    if not re.search(r"^description:", block, re.M):
        fail(skill.name, "SKILL.md frontmatter has no 'description:'")
    return None


def check_readme(skill):
    """CONTRIBUTING.md makes the README, and its 'what it does NOT do'
    section, part of the deliverable -- boundaries are what make a skill's
    output trustworthy."""
    if (skill / "README.md").exists():
        if skill.name in README_GRANDFATHERED:
            notes.append(f"{skill.name}: now has a README — remove it from "
                         f"README_GRANDFATHERED in this script")
        return
    if skill.name not in README_GRANDFATHERED:
        fail(skill.name, "no README.md (required by CONTRIBUTING.md for new skills)")


def check_catalog():
    """A skill absent from the table is invisible; a row pointing at a
    deleted directory is a broken link on the repo's front page."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    table = readme.split("## Skills", 1)[-1].split("### Using these skills", 1)[0]
    listed = set(re.findall(r"^\|\s*\[([a-z0-9-]+)\]\(\./", table, re.M))
    on_disk = {s.name for s in skill_dirs()}
    for missing in sorted(on_disk - listed):
        fail("README.md", f"skill {missing!r} exists but is not in the catalog table")
    for stale in sorted(listed - on_disk):
        fail("README.md", f"catalog lists {stale!r} but no such skill directory exists")


def check_relative_script_paths(skill):
    """A relative path resolves only from this repo's root. Run from a
    user's own project it aborts before the script executes, and the model
    then 'works around' the missing output by guessing -- which is exactly
    why CONTRIBUTING.md mandates absolute paths."""
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for fence in re.findall(r"```bash\n(.*?)```", text, re.S):
        for line in fence.splitlines():
            if re.search(r"(uv run|python3?)\s+[a-z0-9-]+/(scripts|evals)/", line):
                fail(skill.name, f"relative script path in a bash fence: {line.strip()[:70]}")


def _strip_code(text):
    """Remove fenced blocks and inline code spans.

    Both routinely contain markdown that is being SHOWN rather than used --
    CONTRIBUTING.md documents the skill-README backlink as
    `Part of [claude-skills](../README.md)`, which is an instruction, not a
    link. Checking it reported a broken path that does not exist.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def check_internal_links(path):
    """Relative links that point at nothing. External URLs are left alone --
    they rot on someone else's schedule and would make CI flaky."""
    text = _strip_code(path.read_text(encoding="utf-8"))
    for target in re.findall(r"\]\((\.[^)\s]+)\)", text):
        resolved = (path.parent / target.split("#")[0]).resolve()
        if not resolved.exists():
            fail(str(path.relative_to(ROOT)), f"broken relative link: {target}")


def check_fenced_json(path):
    """Config examples inside fences. One that no longer parses is a real
    bug for anyone who copies it.

    Fences containing an elision (`[...]`, `{...}`, `"..."`) are skipped:
    they illustrate a SHAPE rather than provide something copyable, so a
    parse error in one is not a defect. Both such fences in this repo were
    reported as broken on the first run, which is how the rule was found.
    """
    text = path.read_text(encoding="utf-8")
    for block in re.findall(r"```json\n(.*?)```", text, re.S):
        if "..." in block:
            continue
        try:
            json.loads(block)
        except json.JSONDecodeError as exc:
            fail(str(path.relative_to(ROOT)), f"```json fence does not parse: {exc}")


def check_shipped_json(skill):
    for path in sorted(skill.rglob("*.json")):
        if any(part in {".venv", "node_modules", "__pycache__"} for part in path.parts):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            fail(str(path.relative_to(ROOT)), f"invalid JSON: {exc}")


def check_manifest_lists_every_skill(skills):
    """A skill absent from a plugin manifest is INVISIBLE TO EVERY PLUGIN USER, and nothing
    says so. Found 2026-08-20 by installing the collection and counting: the manifests listed
    22 skills, the repo had 23, and `frontier-rounds` had never been added. The plugin
    description said "Twenty-three" while the array said otherwise, and the array is the half
    that is enforced.

    This is the same silent-schema failure recorded in [[agent-plugin-manifests]] -- a
    marketplace that registered cleanly and listed zero plugins, an `agents` field that
    accepted valid paths and loaded none. They fail by loading LESS, never by erroring, so the
    only way to catch one is to count.

    Checked in both directions: an entry pointing at a directory that no longer exists is the
    same defect arriving from the other side, after a rename."""
    on_disk = {s.name for s in skills}
    for rel in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            listed = json.loads(path.read_text()).get("skills") or []
        except json.JSONDecodeError as e:
            fail(rel, f"not valid JSON: {e}")
            continue
        names = {entry.rsplit("/", 1)[-1] for entry in listed}
        for missing in sorted(on_disk - names):
            fail(rel, f"{missing}/ has a SKILL.md but is not in the manifest — "
                      "plugin users would never see it")
        for stale in sorted(names - on_disk):
            fail(rel, f"lists {stale}, which has no SKILL.md — renamed or deleted?")


def check_reference_placeholders(skill):
    """Templated fields that shipped EMPTY, and empty list bullets.

    Found 2026-08-20 in terragrunt-skill/references/error-patterns.md, and only because a
    number on a banner was checked before publishing it. All 68 entries carried
    `**Match:** `{}`` -- the field DIAGNOSE was supposed to match a pasted error against, empty
    in every one, so the router advertised a mode whose data did not exist. Alongside them,
    192 bare `-` bullets rendered as blank list items.

    Both came in with harvested content, like the four pre-1.0 blocks in claude-skills-c3x.
    Neither is a broken link or a bad heading, so nothing structural noticed. A reference that
    ships a placeholder is making a promise the file cannot keep, and the cost lands on whoever
    greps it expecting an answer."""
    refs = skill / "references"
    if not refs.is_dir():
        return
    for path in sorted(refs.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        rel = f"{skill.name}/references/{path.name}"
        # SAME LINE, and a literal {} -- nothing else. The first version allowed an empty
        # alternative and \s* across newlines, so `**Syntax:**` followed by an opening ```
        # fence matched as an empty value. It flagged 38 correct blocks in four files before
        # anything was looked at. A check that cries wolf gets switched off.
        # No ^ anchor: the real one was mid-line, `**Category:** authentication  |
        # **Match:** `{}``, and anchoring to the line start missed every instance while
        # still passing. Same-line is guaranteed by ` +` matching spaces and not newlines.
        empty_value = len(re.findall(r"\*\*[A-Z][A-Za-z ]*:\*\* +`\{\}`", text))
        if empty_value:
            fail(rel, f"{empty_value} templated field(s) ship empty (`{{}}`) — "
                      "a field that promises a value and holds none")
        blanks = len(re.findall(r"^-\s*$", text, re.M))
        if blanks:
            fail(rel, f"{blanks} empty list bullet(s) — they render as blank items")

        # A bold section label with nothing under it. This check exists because removing the
        # 192 blank bullets above CREATED the defect: for 52 of the 69 error entries those
        # bullets WERE the whole `**Solutions:**` body, so the heading survived with an empty
        # section beneath it. Three blank bullets were already worthless, but a heading that
        # promises solutions and holds none is worse than one that was never written -- the
        # reader greps, lands on it, and reads the absence as "no fix exists".
        # Terminal only: the section must run to the next `## ` heading or EOF with nothing
        # but whitespace in it. A label followed by a fence, a table or prose is fine.
        hollow = re.findall(r"(?m)^\*\*([A-Z][A-Za-z ]*):\*\*[ \t]*\n\s*(?=^## |\Z)", text)
        if hollow:
            fail(rel, f"{len(hollow)} bold section(s) with an empty body "
                      f"({', '.join(sorted(set(hollow))[:3])}) — a heading that promises "
                      "content and holds none")



def check_reference_counts(skill):
    """Entry counts written in prose, against the files they claim to count.

    SKILL.md's navigation table already said "Counts are verified against the files, not
    asserted" and named the exact `grep -c` to regenerate them. Nothing ran it. That is the
    same shape as the version pin this skill stopped asserting in claude-skills-802600b: a
    number written into prose, correct on the day, with no mechanism tying it to the thing
    it describes. A count only has to be wrong once for a reader to stop trusting the file.

    Rows read from the table itself, so adding a reference needs no change here. Rows whose
    Entries cell is an em dash opt out -- two files are short enough to read end to end and
    carry no heading convention."""
    skill_md = skill / "SKILL.md"
    if not skill_md.is_file():
        return
    row = re.compile(r"^\|\s*`([\w.\-]+\.md)`\s*\|[^|]*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$", re.M)
    for name, counts_cell, handle_cell in row.findall(skill_md.read_text(encoding="utf-8")):
        if not re.search(r"\d", counts_cell):
            continue
        path = skill / "references" / name
        if not path.is_file():
            fail(f"{skill.name}/SKILL.md", f"navigation table names references/{name}, which does not exist")
            continue
        counts = [int(n) for n in re.findall(r"\d+", counts_cell)]
        handles = re.findall(r"`([^`]+)`", handle_cell)
        if len(counts) != len(handles):
            fail(f"{skill.name}/SKILL.md",
                 f"{name}: {len(counts)} count(s) but {len(handles)} grep handle(s) — "
                 "they have to pair up or the row cannot be checked")
            continue
        text = path.read_text(encoding="utf-8")
        for claimed, handle in zip(counts, handles, strict=True):
            actual = len(re.findall(handle, text, re.M))
            if actual != claimed:
                fail(f"{skill.name}/SKILL.md",
                     f"{name} claims {claimed} for `{handle}`, file has {actual}")


def main():
    skills = skill_dirs()
    if not skills:
        fail("repo", "no skill directories found — is this the right root?")

    for skill in skills:
        check_frontmatter(skill)
        check_readme(skill)
        check_relative_script_paths(skill)
        check_shipped_json(skill)
        check_reference_placeholders(skill)
        check_reference_counts(skill)

    check_catalog()
    check_manifest_lists_every_skill(skills)

    for path in [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]:
        if path.exists():
            check_internal_links(path)
    for skill in skills:
        for name in ("SKILL.md", "README.md"):
            if (skill / name).exists():
                check_internal_links(skill / name)
                check_fenced_json(skill / name)

    print(f"checked {len(skills)} skill(s)")
    for note in notes:
        print(f"  note: {note}")
    if failures:
        print(f"\n{len(failures)} problem(s):")
        for problem in failures:
            print(f"  - {problem}")
        return 1
    print("  all structural checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
