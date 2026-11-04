# String operations: what they return

Every result below was produced by running the expression (Python 3.15.2) and is shown with
`repr()`, so quotes, spaces and `\n` are visible. Use it to explain a miss: put the learner's
answer next to the real value, and for `split()[n]` write out the list with its indices.

Rules of thumb:
- `split()` (no argument) and `split(' ')` are different: the first collapses whitespace and ignores `\n`.
- A slice never raises; a single index does.
- Lines read from a file end in `\n`; slices keep it, `.strip()` removes it.
- `find` returns -1 when absent, and -1 + 1 is 0: the whole string.
- `strip('abc')` strips characters, not a word; use `removeprefix` / `removesuffix`.

## Splitting

`line = 'From ada.lane@example.org Sat Jan  5 09:14:16 2008\n'`

| expression | result | why |
|---|---|---|
| `line.split()` | `['From', 'ada.lane@example.org', 'Sat', 'Jan', '5', '09:14:16', '2008']` | no argument: splits on runs of whitespace (the double space before `5` too), drops empty strings and the `\n` |
| `line.split()[1]` | `'ada.lane@example.org'` | index from 0: the sender |
| `line.split()[3]` | `'Jan'` | the month, not a name: position is all `[n]` knows |
| `line.split()[-1]` | `'2008'` | negative counts from the end |
| `line.split()[9]` | **IndexError**: list index out of range | past the end raises |
| `line.split(' ')` | `['From', 'ada.lane@example.org', 'Sat', 'Jan', '', '5', '09:14:16', '2008\n']` | an explicit `' '` keeps an empty string for the double space and keeps the `\n` |
| `line.split('@')` | `['From ada.lane', 'example.org Sat Jan  5 09:14:16 2008\n']` | split on an exact string |
| `line.split(':', 1)` | `['From ada.lane@example.org Sat Jan  5 09', '14:16 2008\n']` | maxsplit 1: at most two parts, split at the first `:` |
| `len(line.split())` | `7` | number of words |

## Slicing

`line = "Subject: Re: Team's lunch order\n"`

| expression | result | why |
|---|---|---|
| `line[9:]` | `"Re: Team's lunch order\n"` | from index 9 to the end: keeps the trailing `\n` |
| `line[9:].strip()` | `"Re: Team's lunch order"` | strip removes surrounding whitespace, including `\n` |
| `line[:7]` | `'Subject'` | up to, not including, index 7 |
| `line[9:12]` | `'Re:'` | start included, stop excluded |
| `line[-6:]` | `'order\n'` | last 6 characters; the `\n` is one of them |
| `line[100:]` | `''` | out-of-range slices never raise: empty string |
| `line[100]` | **IndexError**: string index out of range | a single index out of range does raise |
| `line[::-1][:6]` | `'\nredro'` | `[::-1]` reverses |

## Find, partition, prefixes

`line = '2026-11-04 12:00:01 ERROR db: timeout after 30s\n'`

| expression | result | why |
|---|---|---|
| `line.find('ERROR')` | `20` | index of the first match |
| `line.find('#')` | `-1` | absent: -1, no exception |
| `line[line.find('#') + 1:]` | `'2026-11-04 12:00:01 ERROR db: timeout after 30s\n'` | the -1 trap: absent gives index 0, so the whole line |
| `line.index('#')` | **ValueError**: substring not found | like find, but raises when absent |
| `line.partition(': ')` | `('2026-11-04 12:00:01 ERROR db', ': ', 'timeout after 30s\n')` | (before, sep, after) at the first sep |
| `line.partition('|')` | `('2026-11-04 12:00:01 ERROR db: timeout after 30s\n', '', '')` | absent: (line, '', '') |
| `line.split(': ', 1)[-1].strip()` | `'timeout after 30s'` | the 'value after the first colon' idiom |
| `line.startswith(('ERROR', '2026'))` | `True` | a tuple of prefixes: any match |
| `line.split()[2]` | `'ERROR'` | the level, by position |

## Strip characters vs remove a prefix

`line = '/var/log/backup/backup-20261104.tar.gz'`

| expression | result | why |
|---|---|---|
| `line.lstrip('/var')` | `'log/backup/backup-20261104.tar.gz'` | strips any of the characters `/`, `v`, `a`, `r` from the left: NOT the prefix `/var` |
| `line.removeprefix('/var/log/')` | `'backup/backup-20261104.tar.gz'` | removes that exact prefix once (Python 3.9+) |
| `line.rpartition('/')` | `('/var/log/backup', '/', 'backup-20261104.tar.gz')` | split at the LAST `/`: (directory, '/', filename) |
| `line.rsplit('.', 1)` | `['/var/log/backup/backup-20261104.tar', 'gz']` | rsplit from the right: the last extension only |
| `line.split('.', 1)` | `['/var/log/backup/backup-20261104', 'tar.gz']` | split from the left: `tar.gz` stays together |

## CSV rows by hand

`line = '1002,Bolt Ltd,,2026-01-06'`

| expression | result | why |
|---|---|---|
| `line.split(',')` | `['1002', 'Bolt Ltd', '', '2026-01-06']` | empty field between two commas is kept as `''` |
| `line.split(',')[2]` | `''` | the empty amount |
| `'-'.join(line.split(',')[:2])` | `'1002-Bolt Ltd'` | join glues strings with the separator between them |
| `line.count(',')` | `3` | non-overlapping occurrences |
| `line.replace(',', ';', 1)` | `'1002;Bolt Ltd,,2026-01-06'` | replace only the first n |
