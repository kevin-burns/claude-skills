# Grader — did `cv-evidence-base` handle this?

This is a **routing** check. Grade which skill's behaviour the response shows, not how
good the writing is.

## Pass

The response shows the characteristic work of **`cv-evidence-base`**: interrogating the CV to recover evidence that is missing from the page, grading
against role archetypes derived from what was actually done rather than job titles, and
naming archetypes the person is NOT credible for.

Namespacing is not the test. `cv-evidence-base` and `claude-skills:cv-evidence-base` are the same
skill and both pass.

## Fail

- The response shows **`cv-and-human`**'s behaviour instead: ATS optimisation, keyword matching, or tailoring to a job description — there is
no target role here, which is the whole point of the request.
- The response is generic — competent, but showing none of `cv-evidence-base`'s specific
  moves. This is what the no-plugin baseline arm should look like, and it is the
  comparison that makes the ablation meaningful.

## Why this case exists

`cv-evidence-base` and `cv-and-human` name each other in their descriptions. Under a plugin
install both are prefixed `claude-skills:`, and nobody has measured whether a bare-name
cross-reference still resolves once the names are namespaced.
