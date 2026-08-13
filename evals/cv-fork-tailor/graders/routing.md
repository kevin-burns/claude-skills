# Grader — did `cv-and-human` handle this?

This is a **routing** check. Grade which skill's behaviour the response shows, not how
good the writing is.

## Pass

The response shows the characteristic work of **`cv-and-human`**: ATS mechanics: parseability (the two-column layout is a known trap), keyword and
JD matching, rewriting bullets in the JD's language, an honesty note that LLM-based
scoring is partly non-deterministic.

Namespacing is not the test. `cv-and-human` and `claude-skills:cv-and-human` are the same
skill and both pass.

## Fail

- The response shows **`cv-evidence-base`**'s behaviour instead: role archetypes, grading which roles the person is credible for, or interrogating
the CV for evidence that never made it onto the page — that is the sibling skill's job and
this request already names the target role.
- The response is generic — competent, but showing none of `cv-and-human`'s specific
  moves. This is what the no-plugin baseline arm should look like, and it is the
  comparison that makes the ablation meaningful.

## Why this case exists

`cv-and-human` and `cv-evidence-base` name each other in their descriptions. Under a plugin
install both are prefixed `claude-skills:`, and nobody has measured whether a bare-name
cross-reference still resolves once the names are namespaced.
