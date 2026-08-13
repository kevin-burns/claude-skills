# Grader — did `markdown-converter` handle this?

This is a **routing** check. Grade which skill's behaviour the response shows, not how
good the writing is.

## Pass

The response shows the characteristic work of **`markdown-converter`**: converting local files with markitdown, run via `uv`/`uvx`.

Namespacing is not the test. `markdown-converter` and `claude-skills:markdown-converter` are the same
skill and both pass.

## Fail

- The response shows **`source-snapshot`**'s behaviour instead: snapshotting a web source, or reaching for a fetch-and-pin workflow. These are
local files that already exist on disk.
- The response is generic — competent, but showing none of `markdown-converter`'s specific
  moves. This is what the no-plugin baseline arm should look like, and it is the
  comparison that makes the ablation meaningful.

## Why this case exists

`markdown-converter` and `source-snapshot` name each other in their descriptions. Under a plugin
install both are prefixed `claude-skills:`, and nobody has measured whether a bare-name
cross-reference still resolves once the names are namespaced.
