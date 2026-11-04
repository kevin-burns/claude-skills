# Curriculum

Every topic is one line in the exact format below; `scripts/progress.py` parses it, so keep the
format: backticked id, bracketed track, title, an em dash, then what to drill and its source.

Tracks: `core` (the basics a live-coding round tests, the gaps a rusty practitioner usually has), `algo` (small
interview problems), `auto` (automation, Automate the Boring Stuff 2e), `review` (reading an unfamiliar
script: will it run, what does it print, what would you change), `pandas` (Pandas Workout +
Effective Pandas).

Sources are further reading, not something the skill needs: ATBS = Automate the Boring Stuff
with Python 2e (Sweigart); PW = Pandas Workout (Lerner); EP = Effective Pandas (Harrison).
`none` = common interview material, no book behind it. Questions are always written fresh.

## core

- `core.types-truthiness` [core] Types and truthiness — int/float division, `//` and `%`, None vs falsy, `is` vs `==`, int/str conversion errors (ATBS ch1)
- `core.slicing` [core] Slicing and indexing — negative indices, steps, `[::-1]`, slice copies vs aliases, IndexError vs empty slice (ATBS ch4)
- `core.list-methods` [core] List methods — append vs extend, insert, pop, remove, index, sort vs sorted, in-place methods returning None (ATBS ch4)
- `core.comprehensions` [core] Comprehensions — list/dict/set comprehensions, conditional filter vs ternary, nested comprehension order (none)
- `core.dict-ops` [core] Dictionaries — get with default, setdefault, items/keys/values, iteration order, `|` merge, KeyError, dict comprehension inversion (ATBS ch5)
- `core.sets` [core] Sets — membership, union/intersection/difference, dedupe, set of tuples, unhashable list error (none)
- `core.sorting` [core] Sorting — sorted with key=, reverse=, multi-key tuples, stable sort, sorting dict by value, operator.itemgetter (ATBS ch4)
- `core.strings-methods` [core] String methods — split/join, strip, replace, find vs index, startswith, upper/lower/title, isdigit/isalpha, f-strings and format specs (ATBS ch6)
- `core.string-algos` [core] String algorithms — reverse, palindrome, anagram, character and word counts, first non-repeating char, vowels (none)
- `core.collections` [core] collections — Counter.most_common, defaultdict(list), deque appendleft/popleft, namedtuple (none)
- `core.functions` [core] Functions — positional/keyword args, defaults, *args/**kwargs, the mutable default argument trap, return None (ATBS ch3)
- `core.scope-closures` [core] Scope and closures — local/global, nonlocal, late-binding closures in a loop (ATBS ch3)
- `core.iterators-generators` [core] Iteration — enumerate, zip, range, generators with yield, generator expressions, itertools basics (none)
- `core.exceptions` [core] Exceptions — try/except/else/finally order, raising, custom exception classes, catching specific errors (ATBS ch3, ch11)
- `core.classes` [core] Classes — __init__, instance vs class attributes, methods, __repr__ vs __str__, __eq__, a small class from a spec (none)
- `core.inheritance` [core] Inheritance — super(), overriding, classmethod vs staticmethod, @property, isinstance (none)
- `core.dunder` [core] Dunder methods — __len__, __getitem__, __iter__, __lt__ for sorting, __hash__ with __eq__ (none)
- `core.dataclasses` [core] dataclasses — @dataclass fields, defaults, field(default_factory=list), frozen, ordering (none)
- `core.mutability` [core] Mutability and copying — aliasing, copy vs deepcopy, list of lists `[[0]*3]*3` trap, tuples holding lists (ATBS ch4)
- `core.big-o` [core] Complexity — cost of list vs set membership, dict lookup, list.insert(0), string concatenation in a loop (none)
- `core.typing` [core] Type hints — annotations, Optional/`X | None`, list[int], what hints do and do not enforce (none)

## algo

- `algo.two-sum` [algo] Two-sum family — dict of complements, O(n) vs O(n^2), pairs and indices (none)
- `algo.frequency` [algo] Frequency counting — top-k, most common word, group anagrams (none)
- `algo.dedupe-order` [algo] Dedupe preserving order — dict.fromkeys, seen-set loop (none)
- `algo.brackets` [algo] Stack problems — balanced brackets, reverse Polish notation (none)
- `algo.sliding-window` [algo] Sliding window — max sum of k, longest substring without repeats (none)
- `algo.binary-search` [algo] Binary search — iterative, off-by-one boundaries, bisect module (none)
- `algo.matrix` [algo] Nested lists — transpose with zip(*m), flatten, rotate, grid neighbours (none)
- `algo.recursion` [algo] Recursion — factorial/fibonacci, memoisation with functools.cache, recursion vs iteration (none)
- `algo.fizzbuzz-family` [algo] Warm-up loops — fizzbuzz, prime check, sum of digits, number to words (none)

## auto

- `auto.regex` [auto] Regular expressions — re.search vs match vs fullmatch, groups, findall, sub, raw strings, greedy vs non-greedy (ATBS ch7)
- `auto.input-validation` [auto] Input validation — loops until valid, converting input safely (ATBS ch8)
- `auto.files-pathlib` [auto] Files and paths — pathlib.Path, open with `with`, read/write modes, encoding, glob (ATBS ch9)
- `auto.organising-files` [auto] Organising files — shutil copy/move, os.walk, zipfile, safe deletes (ATBS ch10)
- `auto.debugging` [auto] Debugging — assert, logging levels and config, traceback reading, breakpoint() (ATBS ch11)
- `auto.web` [auto] Web — requests get/raise_for_status, JSON responses, BeautifulSoup select (ATBS ch12)
- `auto.csv-json` [auto] CSV and JSON — csv.reader/DictReader/DictWriter, newline='', json.load vs loads, dumps indent (ATBS ch16)
- `auto.time-subprocess` [auto] Time and processes — datetime/timedelta, strftime/strptime, time.sleep, subprocess.run with check and capture_output (ATBS ch17)
- `auto.cli` [auto] Command-line scripts — sys.argv, argparse, `if __name__ == "__main__"`, exit codes (none)

## review

Read-a-script rounds (a common interview format); see `review-round.md`.

- `rv.narrate` [review] Narrate the data flow — input → parse → store → output before criticising; name the record shape (none)
- `rv.trace-output` [review] Trace and predict output — run one real input line through the code by hand; `split()[n]` on real lines (none)
- `rv.fragile-parsing` [review] Fragile parsing — magic indices, IndexError on short lines, regex with named groups, stdlib parsers (email, mailbox, csv, json) (ATBS ch7, ch16)
- `rv.files-encoding` [review] Files and encoding — `with open`, encoding= and errors=, pathlib, streaming with generators (ATBS ch9)
- `rv.sql-safety` [review] SQL from Python — f-string SQL injection, bound parameters (sqlite3 `?`, SQLAlchemy `text()` with `:name`), the apostrophe test, parameter shapes (`executemany` needs tuples), NULL semantics (`IS NULL`, `count(col)`) (none)
- `rv.transactions` [review] Writes and re-runs — one transaction, bulk insert, commit placement, idempotency with a unique key and upsert (none)
- `rv.will-it-run` [review] Will it run as written? — missing imports, a helper called but never defined, hardcoded input paths; say where it fails before predicting output (none)
- `rv.structure` [review] Script structure — functions behind `__main__` or a handler (e.g. Lambda), one connection opened in main or a class and passed in, error handling, docstrings, logging not print, config from env, type hints, one fixture test (ATBS ch11)

## pandas

- `pd.series-basics` [pandas] Series basics — creation, index alignment in arithmetic, describe, NaN propagation (PW ch1, EP ch03-ch05)
- `pd.boolean-masks` [pandas] Boolean masks — `&`/`|` with parentheses, isin, between, `~` (PW ch1, EP ch09)
- `pd.loc-iloc` [pandas] Indexing — loc vs iloc, label slices inclusive, setting values safely, SettingWithCopy (PW ch2, ch4; EP ch09, ch23)
- `pd.dtypes` [pandas] Types and memory — astype, nullable Int64, category, memory_usage(deep=True) (PW ch3, EP ch07, ch19)
- `pd.value-counts` [pandas] Counting — value_counts(normalize=True), nunique, idxmax, nlargest (PW ch1, EP ch06)
- `pd.assign-chaining` [pandas] Method chaining — assign with lambdas, pipe, why not inplace (EP ch19, ch20)
- `pd.apply-vectorise` [pandas] apply vs vectorised — when apply is slow, np.where/np.select, map with dict (EP ch08, ch18)
- `pd.missing` [pandas] Missing data — isna, fillna, dropna subset, interpolate, duplicated/drop_duplicates (PW ch5, EP ch21)
- `pd.groupby` [pandas] groupby — agg with named aggregations, transform vs agg, multiple keys, reset_index (PW ch6, EP ch26, ch27)
- `pd.pivot-crosstab` [pandas] Pivot and crosstab — pivot_table aggfunc and margins, crosstab normalize (PW ch4, EP ch26, ch28)
- `pd.merge` [pandas] Joining — merge how/on/validate, join on index, concat axis (PW ch6, EP ch31)
- `pd.str` [pandas] String accessor — str.split(expand=True), str.contains, str.extract (PW ch8, EP ch10)
- `pd.dt` [pandas] Dates — to_datetime, .dt accessor, resample, date offsets (PW ch9, EP ch11, ch12, ch30)
- `pd.io` [pandas] Reading and writing — read_csv usecols/dtype/parse_dates, to_csv index=False, parquet (PW ch3, EP ch32)
- `pd.reshape` [pandas] Reshaping — melt, stack/unstack, get_dummies (EP ch25, ch29)
- `pd.cut-query` [pandas] Binning and query — cut vs qcut, query and eval (PW ch1, ch11; EP ch23)
- `pd.modern` [pandas] pandas 3.x changes — pd.col, case_when, Copy-on-Write, str dtype, ME/QE aliases, .agg('std') not np.std (EP modern-pandas.md)
