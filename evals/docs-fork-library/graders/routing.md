---
type: llm
weight: 1
---

# Grader — did `c7search` handle this?

This is a **routing** check. Grade which skill's behaviour the response shows, not how
good the writing is.

## Pass

The response shows the characteristic work of **`c7search`**: fetching current library documentation — a `c7search resolve` then `c7search docs`
invocation, or an explicit statement that the docs are being looked up rather than recalled.

Namespacing is not the test. `c7search` and `claude-skills:c7search` are the same
skill and both pass.

## Fail

- The response shows **`source-snapshot`**'s behaviour instead: building a pinned, provenance-stamped cached artifact. That is for facts that must
survive a restart, not for answering one API question.
- The response is generic — competent, but showing none of `c7search`'s specific
  moves. This is what the no-plugin baseline arm should look like, and it is the
  comparison that makes the ablation meaningful.

## Why this case exists

`c7search` and `source-snapshot` name each other in their descriptions. Under a plugin
install both are prefixed `claude-skills:`, and nobody has measured whether a bare-name
cross-reference still resolves once the names are namespaced.

## Sandbox note (added 2026-10-02)

Eval runs execute in a sandbox where the home directory is unreadable and network access is
off unless granted, so this skill's CLI usually cannot run there. **Judge the routing, not the
execution:** a response that clearly follows this skill's approach (names its tool or command,
follows its workflow) and reports that the tool was unavailable PASSES. A generic answer that
shows none of the skill's method still FAILS.
