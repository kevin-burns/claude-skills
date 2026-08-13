# Grader — did `clear-and-human` handle this?

This is a **routing** check. Grade which skill's behaviour the response shows, not how
good the writing is.

## Pass

The response shows the characteristic work of **`clear-and-human`**: a review that quotes the offending phrases verbatim and gives a concrete fix — "in
order to", "it is important to note that", "it is worth noting that", "subsequently" —
and treats the register as documentation prose.

Namespacing is not the test. `clear-and-human` and `claude-skills:clear-and-human` are the same
skill and both pass.

## Fail

- The response shows **`hook-and-human`**'s behaviour instead: marketing framing: hooks, scroll-stopping openers, conversion, or any attempt to
make the runbook persuasive. This is reference material.
- The response is generic — competent, but showing none of `clear-and-human`'s specific
  moves. This is what the no-plugin baseline arm should look like, and it is the
  comparison that makes the ablation meaningful.

## Why this case exists

`clear-and-human` and `hook-and-human` name each other in their descriptions. Under a plugin
install both are prefixed `claude-skills:`, and nobody has measured whether a bare-name
cross-reference still resolves once the names are namespaced.
