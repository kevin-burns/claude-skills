# Review scenarios

Short original scripts for review rounds and quick-fire items. All code here was written for this
skill. The domains follow Automate the Boring Stuff projects (regex extraction, CSV/JSON, date
renaming) and a common interview shape (parse a mailbox, store it in a database); no book code is reproduced.

Scripts live in `fixtures/scenarios/<family>/`, inputs in `fixtures/`. Run from
`fixtures/scenarios/`, with the input that belongs to the family:

| scripts | input argument |
|---|---|
| `mailbox/m1`–`m6` | `../sample.mbox` (plain `python3 -I`) |
| `mailbox/m0_reference.py`, `mailbox/m7_sqlalchemy_fstring.py` | `../sample.mbox`, under `uv run --no-project --with sqlalchemy python -I` |
| `regex/*` | `../contacts.txt` |
| `csvjson/c1`, `csvjson/c2` | `../orders.csv` |
| `csvjson/j1_weather.py` | `../weather.json` |
| `dates/*`, `gotchas/g1`–`g5` | none |
| `gotchas/g6_commit_per_row.py` | none, under `uv run --no-project --with sqlalchemy python -I` |

**The tables below hold the answers, and the filenames name the bug** (`g2_late_binding.py`).
Show the learner only the script's contents and the input's contents: never a row, a filename or a
path. **Re-run the script before asking.** The outputs below were recorded on 2026-11-04 (Python 3.12),
and they are a check on the fixture, not a substitute for running it. After the first time the learner
has seen a scenario, mutate it before reuse: change the index, the `startswith` condition, a
variable name or one fixture line, then run it again for the new answer.

## Family M: the mailbox (`fixtures/sample.mbox`, 3 messages)

The question learners most often get wrong: **what actually ends up in the list?** The
subject, the body, the sender, or a word that happens to sit at that index? Every variant answers
it differently. Ask "what does `print` show?" first, before any improvement talk.

Fixture facts to keep in mind: each message has an mbox separator `From addr Day Mon DD hh:mm:ss
YYYY`, then headers (`From:`, `Subject:`…), a blank line, a body. Message 2's `From:` header has a
quoted display name (`"Bo Chen" <bo.chen@...>`) and its subject contains an apostrophe. Message
3's subject is one word.

| Script | What it tests | Output (2026-11-04) | Topics |
|---|---|---|---|
| `m1_separator_index.py` | `split()[3]` on the separator line; file never closed | `['Jan', 'Jan', 'Jan']`: the month, not the sender (`[1]`) | rv.trace-output, rv.fragile-parsing, rv.files-encoding |
| `m2_header_sender.py` | `split()[1]` on the `From:` header | `['ada.lane@example.org', '"Bo', 'carol@example.com']`: a display name breaks positional parsing; `email.utils.parseaddr` is the fix | rv.fragile-parsing |
| `m3_startswith_from.py` | `startswith("From")` matches both separator and header | `{'ada.lane@example.org': 2, 'bo.chen@example.net': 1, '"Bo': 1, 'carol@example.com': 2}`: double counts, plus a junk key | rv.trace-output, core.dict-ops |
| `m4_sender_subject_pairs.py` | state carried across lines: does each subject get *its* sender? | three `(sender, subject)` tuples, correctly paired, but every subject ends in `'\n'` (no strip), visible because a list prints reprs | rv.trace-output, core.strings-methods |
| `m5_body_accumulate.py` | stateful body parsing | prints `2` then two bodies: the body is never reset (message 2's body contains message 1's), and the last message's body is never appended; the `Author:` line counts as body | rv.fragile-parsing, rv.trace-output |
| `m6_subject_word.py` | `split()[3]` on subjects | `IndexError` on the one-word subject; **nothing is printed**, because the crash happens before `print` | rv.trace-output, rv.fragile-parsing |
| `m7_sqlalchemy_fstring.py` | f-string SQL via SQLAlchemy `text()` | `OperationalError: near "s": syntax error` on `Team's`: injection shown with an innocent input; nothing printed; no transaction; DB URL hardcoded | rv.sql-safety, rv.transactions, rv.structure |
| `m0_reference.py` | the answer, not a question | `mailbox` + `parseaddr`, bound parameters, `engine.begin()`, primary key + `INSERT OR IGNORE` so a second run adds nothing (rows=3 after two stores) | show after a round, as the "what good looks like" |

Good follow-ups for this family: "the file is 4 GB — what changes?" (generator, don't build the
list), "run it twice — what happens to the table?" (idempotency), "how do you test it?" (a
three-message fixture like this one).

## Family R: regex extraction (`fixtures/contacts.txt`)

| Script | What it tests | Output | Topics |
|---|---|---|---|
| `r1_findall_groups.py` | `findall` with groups returns tuples, not strings; phone pattern too narrow | emails as `('help', 'example.org')` tuples, duplicates kept; phones `[('555', '0199'), ('555', '0142')]` — area code and `+49` mobile missed; `len(set(emails))` = 2 | auto.regex, rv.fragile-parsing |
| `r2_search_first_only.py` | `search` finds only the first match per line; `None` padding | `['help@example.org', 'anna.berg@example.co.uk', 'anna.berg@example.co.uk', None]` | auto.regex |

## Family C: CSV and JSON (`fixtures/orders.csv`, `fixtures/weather.json`)

| Script | What it tests | Output | Topics |
|---|---|---|---|
| `c1_sum_amounts.py` | `csv.reader` handles the quoted comma, but `float('1,200.00')` fails; `amount or 0` hides the empty value; the bad date `2026-13-01` is never checked | `ValueError: could not convert string to float: '1,200.00'` | rv.fragile-parsing, auto.csv-json |
| `c2_split_comma.py` | hand-splitting CSV on `,` | `ValueError: too many values to unpack (expected 4, got 5)` on the quoted amount: why the `csv` module exists | rv.fragile-parsing |
| `j1_weather.py` | `weather: []` → `[0]` fails; same-day keys would overwrite each other | `IndexError: list index out of range` on the third item; even without it, the 12:00 entry for 2026-11-04 is overwritten by 15:00 | rv.fragile-parsing, core.dict-ops |

## Family D: dates and functions (no input file)

| Script | What it tests | Output | Topics |
|---|---|---|---|
| `d1_rename_us_dates.py` | regex on US-style dates in filenames | `{'report-12-31-2025.txt': 'report-31-12-2025.txt', 'spam-4-1-2026.csv': 'spam-1-4-2026.csv'}`: the ISO name is correctly skipped, the two-digit-year `invoice-1-15-26.pdf` is silently skipped too; no check that month ≤ 12 | auto.regex, rv.fragile-parsing |
| `d2_mutable_default.py` | mutable default argument | `['eu', 'us'] ['eu', 'us'] ['apac']` then `True` | core.functions, core.mutability |

## Family G: gotchas interviewers plant (no input file)

Categories from the sources in `sources.md` (python.org docs, python-guide, QuantifiedCode); the
scripts are original. Good as one-line quick-fires or as the "one more problem" in a longer script.

| Script | What it tests | Output | Topics |
|---|---|---|---|
| `g1_remove_while_iterating.py` | removing from a list while looping over it | `['web1', 'tmp-b', 'db1']`: every second `tmp-` survives; fix with a comprehension | core.list-methods, core.mutability |
| `g2_late_binding.py` | lambdas in a loop capture the variable, not the value | `['deploy to prod', 'deploy to prod', 'deploy to prod']`; fix `lambda env=env:` | core.scope-closures |
| `g3_return_in_finally.py` | `return` in `finally` swallows the exception | `defaults`, and the FileNotFoundError is gone. Python 3.14 emits a SyntaxWarning for this (PEP 765) | core.exceptions |
| `g4_exhausted_generator.py` | a generator can be consumed once | `3 []`: the count used it up | core.iterators-generators |
| `g5_bare_except.py` | bare `except:` hides every error | `80 8080 8080 8080`: bad value, missing key and `None` all silently become the default | core.exceptions, rv.structure |
| `g6_commit_per_row.py` | commit per row vs one bulk execute (SQLAlchemy) | `4000 True`: same rows, per-row commits slower. The second value is a timing and could vary; re-run before stating it | rv.transactions |
