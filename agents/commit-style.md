# Skill: Commit & PR/MR Message Style

How to write commits and PR/MR descriptions in this repo. Used by the `commit-pr`
subagent. Defers to `AGENTS.md` "Git Conventions" for prefixes/branches and to the global
git rules for attribution.

## Commit messages
- **Subject:** `<type>: <imperative summary>` — types per AGENTS.md (`feat`, `fix`, `docs`,
  `test`, `refactor`). Imperative mood ("add", not "added"), no trailing period, ≤ ~72 chars.
- **Body** (when the change isn't trivial): wrap ~72 cols. Explain *why* and the impact —
  not a restatement of the diff. Reference issue IDs.
- **Traceability:** for pipeline/infra changes, name the design-doc section or graph area
  touched (supports AGENTS.md Constitution #4).

Example:
```
fix: stop CIDR validator passing on overlapping spoke ranges

The validator only checked exact-match overlaps, so adjacent /24s that
partially overlapped slipped through and produced an invalid graph.
Now compares ranges with ipaddress.overlaps(). Closes #142.
Ref: prd §4.3 (network validation rules).
```

## PR/MR descriptions
Cover, in plain prose: summary of the change and why; what changed; testing done
(tests/type checks/lint per AGENTS.md PR requirements); linked issues; any spec citations.
Platform-neutral — same body works for GitHub or GitLab.

## Hard rules
- **No** `Co-Authored-By`, AI/tool attribution, or "Generated with Claude Code" line —
  anywhere (commit, title, or body). This is non-negotiable (global git rules).
- No secrets, tokens, or subscription IDs in any message.
- Don't auto-push or open/merge — that's the caller's job (AGENTS.md "Landing the Plane").

