# Grader — did nothing fire?

This is a **negative** routing check. The correct behaviour is that no skill in this
collection engages.

## Pass

A direct, correct answer about concurrency primitives, with no skill announcing itself
and no skill-specific workflow being run.

## Fail

Any skill from this plugin firing. Nothing here covers concurrency theory. A false
positive is not harmless: 21 descriptions are already loaded on every request, and a
skill that fires on unrelated work spends context and misleads the user about what the
collection is for.

## Why this case exists

A routing suite made only of positive cases measures eagerness, not accuracy. Without a
negative case, a plugin whose skills fire on everything scores perfectly.
