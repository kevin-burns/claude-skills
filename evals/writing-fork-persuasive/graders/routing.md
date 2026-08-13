# Grader — did `hook-and-human` handle this?

This is a **routing** check. Grade which skill's behaviour the response shows, not how
good the writing is.

## Pass

The response shows the characteristic work of **`hook-and-human`**: an opening line built to stop the scroll, attention to the hook, and copy shaped
for a social feed rather than a document.

Namespacing is not the test. `hook-and-human` and `claude-skills:hook-and-human` are the same
skill and both pass.

## Fail

- The response shows **`clear-and-human`**'s behaviour instead: treating this as neutral documentation prose. NOTE: this case is deliberately
adversarial — `clear-and-human`'s own description lists "LinkedIn post" among the things it
handles, so a wrong route here is the most likely single failure in the set.
- The response is generic — competent, but showing none of `hook-and-human`'s specific
  moves. This is what the no-plugin baseline arm should look like, and it is the
  comparison that makes the ablation meaningful.

## Why this case exists

`hook-and-human` and `clear-and-human` name each other in their descriptions. Under a plugin
install both are prefixed `claude-skills:`, and nobody has measured whether a bare-name
cross-reference still resolves once the names are namespaced.
