# Review round: read a script, explain it, improve it

## Why this exists

Many Python interviews are not "write a function". They hand over a short script and ask:
**would it run, what does it do, what does it output, what would you improve?** The script is
usually plausible automation code with deliberate problems, and often it does not run at all.
A typical shape: read a mailbox or log file line by line, pull fields out with something like
`line.split()[3]`, write them to a database, print a list. Typical planted problems:

- names used but never imported or defined, so the script stops with `NameError`
- fields taken by position (`split()[n]`, `line[9:]`) that break on short lines or keep `\n`
- hardcoded input paths and database URLs
- SQL built with f-strings; a table never created; commits per row; no key, so re-runs duplicate
- a database connection opened inside a function on every call and never closed
- no `if __name__ == "__main__":` guard or handler (for example for AWS Lambda), no error
  handling, no docstrings, `print` instead of logging

Verified on `fixtures/sample.mbox` (3 messages):
- `line.split()[3]` on mbox `From ` separator lines gives the month (`['Jan', 'Jan', 'Jan']`), not
  the sender; the sender is `[1]`.
- Applied to every line, it raises `IndexError` on the first blank or short line.
- An f-string `INSERT` breaks on a subject containing an apostrophe (`near "s": syntax error`);
  a `?` / bound parameter works. That is SQL injection, shown with an innocent input.

## The answer shape interviewers listen for

0. **Will it run?** Before anything else, scan for names used but never imported or defined, and
   say where it would stop (`NameError` at line N, before any output).
1. **Narrate the data flow**: input → parse → store → output, in one or two sentences, before
   any criticism. Name the shape of the input (what does one record look like?).
2. **Correctness**: what crashes, what returns the wrong thing, on which input. Trace one real
   line through the code and say the value out loud. Magic indices, missing guards, encoding,
   unclosed files, state that line-by-line parsing loses (multi-line bodies), injection.
3. **Production readiness**: config out of code (input path, DB URL from argv or env), one
   connection opened in `main` or a class and passed in, transactions and bulk writes,
   idempotency (re-run = duplicates; unique key + upsert), functions behind
   `if __name__ == "__main__":` or a handler, error handling, docstrings, logging instead of
   print, generators for large input, type hints, one small test with a fixture. Prefer the
   stdlib parser for the format (`email`, `mailbox`, `csv`, `json`, `pathlib`) over hand-splitting.

If an API name will not come, say what it should do ("the stdlib has an mbox parser that
handles multi-line headers"): the reasoning scores even when the name is missing.

## Running one (~15 minutes)

1. **Get a script.** `scripts/make_variant.py new --rotate` (or `--family sql`, `--topic
   rv.sql-safety`; exit 3 means no generator covers that topic). It prints an id, the script and
   input paths and the question. Its answer file (`answers/<id>.json`, separate folder) holds the
   real stdout or exception, the `planted_problems` list, the topics, and the family and seed.
   Generated scripts are short (about 5–15 lines). For a full round, **extend it by hand** with
   2–3 of the problems listed above that are not already in it (connection opened per call, no error handling,
   undefined helper, missing import), **run it again** with `python3 -I script.py <input>` in its
   folder, and add what you planted to the rubric. **For an extended script the answer file is
   stale: the re-run's output replaces its `stdout`/`error`.** To repeat a missed exercise exactly:
   `make_variant.py rebuild FAMILY SEED`.
   The fixed set in `references/scenarios.md` also works; its table rows hold the answers, so
   never show a row or a filename.
2. **The rubric is written before showing anything**: read the answer file now (you need it to
   grade; the learner must not see it) and take its `planted_problems` plus anything you added, each
   with the line it is on.
3. **Show the script by pasting its contents and the input's contents**, never a path or
   directory listing. Then ask in order, one at a time, as an interviewer would, with no feedback
   in between:
   - "Would this run as written?"
   - "Walk me through what this does."
   - "What does it print for this input?" (or where does it stop)
   - "What would you change before this runs in production?"
   - One follow-up on the weakest answer, asked after the question above is answered (for
     example "how would you make re-runs safe?"). A problem named only here counts as found
     after a hint.
4. **Explain, then score.** Only after all of them are answered, go through the answers in
   order and explain each miss, following the Feedback section of `SKILL.md`:
   - **Would it run / output:** if the answer was wrong, trace the script from the top with the real
     input to the line that decides it (the first line that raises, or the line that produces
     the printed value), saying the actual values at each step, until the prediction and the
     real output part ways. Then show the real output.
   - **Each planted problem missed:** where it is (the line), what goes wrong because of it
     and on which input, and the fix in one line of code. Problems found get a one-word tick.
   - **Anything called a problem that is not one:** say why it is fine.
   Then grade with the table in `SKILL.md` (review column). "Would it run" is part of the output
   answer: for a script that stops, the right answer is where and why. Record every topic in the
   answer file (`--note=` with the equals sign).
5. Optionally, have the learner write the fixed version and run it on the input with `run_tests.py`.

Rotate the domain (`--rotate`) so the skill is reading code, not recognising one script.
