# External sources for review rounds

Links only. Nothing below is copied into this skill; read the source, then write a fresh script.
Collected by a web search on 2026-11-04. UNVERIFIED means the page could not be opened at the time.

## The classic mailbox-parsing exercises

Python for Everybody (Charles Severance), book licence CC BY 4.0 (verified on https://www.py4e.com/book).
The licence of its code and data files is not stated on a page: link, do not copy.

- Files, lists, dictionaries, tuples, regex, databases chapters all use `mbox-short.txt`:
  https://www.py4e.com/html3/07-files · /08-lists · /09-dictionaries · /10-tuples · /11-regex · /15-database
- On an mbox `From ` separator line, `split()` gives `[1]` sender, `[2]` weekday, `[3]` month,
  `[5]` time. `[3]` = month matches our own run on `fixtures/sample.mbox` (`['Jan', 'Jan', 'Jan']`).
- Lists chapter: a "guardian" exercise on blank lines raising IndexError: the same crash as `m6`.
- `emaildb.py` (https://www.py4e.com/code3/emaildb.py) loads `From: ` senders into SQLite. The web
  agent's reading of its weak points (its own, not a cited list): commit on every line, no UNIQUE
  constraint, DROP TABLE on every run, file not opened with `with`.

## Code-review exercises

- https://dev.to/iamibi/code-review-exercises-that-actually-work-python-edition-junior-to-senior-57kf: three snippets with answer lists
- https://opensource.com/article/19/9/common-pitfalls-python: SQLAlchemy commit placement, per-object updates, bulk import (closest to the mailbox-to-database review scripts)
- https://extreme-coding.pages.dev/phase-08-practical-engineering/labs/lab-08-log-parser: log parser; memory and streaming
- https://github.com/snyk/snyk-code-review-exercise: review exercise; answer key not public
- https://github.com/martinpeck/broken-python and https://github.com/Brainstorma/Fix_My_Code_Challenge: MIT; contents not read
- https://www.fastnexa.com/guides/code-review-as-an-interview: argues interviewers grade the order of review comments, not the count. That is the three-pass shape in `review-round.md`
- UNVERIFIED (no content returned): dataford.io, prachub.com, Toptal

## Gotcha references

- Mutable defaults, modifying while iterating, `return` in `finally`: https://docs.python.org/3/faq/programming.html, https://docs.python.org/3/tutorial/errors.html
- Late-binding closures: https://docs.python-guide.org/writing/gotchas/ (CC BY-NC-SA 3.0), https://martinheinz.dev/blog/37
- Bare except, `with` for files, `is` vs `==`: https://docs.quantifiedcode.com/python-anti-patterns/ (licence UNVERIFIED)
