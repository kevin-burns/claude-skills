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
