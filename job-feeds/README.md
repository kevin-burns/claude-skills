# job-feeds

Aggregate eight sanctioned public job feeds into one deduplicated local database, match
them against your career lanes, and get a filterable HTML report you can open offline.

Part of [claude-skills](../README.md).

## What it does

Polls eight documented JSON APIs and RSS feeds — [Arbeitnow](https://www.arbeitnow.com),
[Jobicy](https://jobicy.com), [Remotive](https://remotive.com),
[Remote OK](https://remoteok.com), [Working Nomads](https://www.workingnomads.com),
[4 Day Week](https://4dayweek.io), [We Work Remotely](https://weworkremotely.com) and
[Python.org Jobs](https://www.python.org/jobs/) — normalises eight different payload
shapes into one, deduplicates across them, and stores the result in SQLite.

Because it keeps a `first_seen` per posting, it can answer the question the feeds
themselves cannot: **what is actually new since you last looked.** Every feed returns a
rolling window with no notion of newness, so without a local store each fetch looks like
a fresh set of results.

You define *lanes* — a name and a regex — and a job is shown only if it matches at least
one. A role can belong to several; all are shown, which is usually the interesting
signal.

### The sources, and what each is actually good for

Coverage is uneven by design — these are not interchangeable. Verified 2026-08-05.

**This table is about choosing.** The one in [`SKILL.md`](./SKILL.md) covers the same eight
sources operationally — exact rate limits, pagination depth, payload quirks — and is worth
reading only when something looks wrong. You do not need both to get started.

| Source | Good for | Worth knowing |
|---|---|---|
| [Arbeitnow](https://www.arbeitnow.com) | **Germany** — most of our German rows | An independent free board, not an official aggregator: it holds a sample, not the market. Only ~7 days deep, so a 14-day window can't get 14 days from it. Burst-sensitive: pages are capped and paced |
| [Jobicy](https://jobicy.com) | Europe-weighted remote | Documents 1 poll/hour fair use, which the tool enforces |
| [Remotive](https://remotive.com) | Remote, broad | Ignores its own `limit` parameter |
| [Remote OK](https://remoteok.com) | Volume — 100 rows/fetch | Requires a dofollow backlink; the report carries it. Some listings are low quality |
| [Working Nomads](https://www.workingnomads.com) | Remote, curated | Undocumented endpoint — could vanish without notice |
| [4 Day Week](https://4dayweek.io) | Reduced-hours roles | Small but distinctive inventory |
| [We Work Remotely](https://weworkremotely.com) | Remote engineering | Per-category RSS |
| [Python.org](https://www.python.org/jobs/) | Python roles, high signal | Tiny volume, and publishes **no dates at all** — those rows show `—` |

[`SKILL.md`](./SKILL.md) carries the rest: exact endpoints, pagination behaviour, rate-limit
details and how to read `jfeeds sources` when something looks thin.

## Install

Three commands from a clone to your first results. Nothing lands on your PATH, and
nothing is installed system-wide.

```bash
# 1. Link the skill (from your claude-skills clone)
ln -s "$(pwd)/job-feeds" ~/.claude/skills/job-feeds

# 2. Define the shell function — once per terminal, since shell state does not persist
jfeeds() { python3 "$HOME/.claude/skills/job-feeds/scripts/job_feeds.py" "$@"; }

# 3. Find out what you still need
jfeeds doctor
```

`doctor` makes no network calls. Until a config exists it exits 2 and prints a complete,
valid starter config you can paste — so step 3 tells you exactly what to do next rather
than failing at you. **Asking Claude to write the config is the better path**, because the
lanes are regexes and they are the part people get wrong; the starter exists for when you
are working alone at a shell.

Python 3.9+ and standard library only, so `python3` works. If you prefer `uv`, or need it
resolved when it is off PATH, [`SKILL.md`](./SKILL.md) has that variant — use one or the
other, not both.

It is called `jfeeds`, **not `jobs`** — `jobs` is a shell builtin.

## Everyday use

Re-declare the function in each new shell, then:

```bash
jfeeds() { python3 "$HOME/.claude/skills/job-feeds/scripts/job_feeds.py" "$@"; }

jfeeds doctor                   # config + counts, zero network calls
jfeeds fetch                    # poll the sources
jfeeds digest --window 7        # what matched, as a table
jfeeds sources                  # every source, its status, and why
jfeeds locations                # where the fetched rows actually are
jfeeds report --out jobs.html   # self-contained page, opens with no network
```

## How to use it well

**Spend your time on the lanes.** Everything else has a sensible default; the lane
regexes are what decide whether the output is useful or noise. Start narrow. A lane like
`\bai\b` will match a startling number of jobs that merely mention AI in passing.

**Set `"match_in": "title"` on role-shaped lanes.** On a real run, every one of the
Platform lane's description matches was wrong — agency ads listing every discipline they
staff, services blurbs, section headings — while every title match was right. Role
identity lives in the title. Leave the default where you want the body searched, such as
catching a niche tool named deep in an otherwise generic ad.

**Run `fetch` occasionally, `digest` freely.** Fetching is rate-limited and polite;
reading is free. `digest` and `report` make zero network calls, so re-run them as often
as you like.

**Read `sources` when something looks thin.** It reports *why* — a documented rate limit,
a 429, or an upstream that renamed a field — rather than leaving you to guess whether a
quiet day is real.

**Expect Arbeitnow to dominate the German results** and Python.org to be tiny but high
signal. Coverage is uneven by design; the sources are not interchangeable.

**Dominating our results is not the same as covering the market.** Every source here is a
free job board, most run by small teams or one person, each carrying whatever employers
chose to post there. A role can be live on a national employment service and absent from
all eight — observed 2026-08-06, when forward-deployed engineer roles posted to the
Bundesagentur für Arbeit within the previous week did not appear in Arbeitnow. So read a
quiet week as "quiet on these boards", never as "quiet in the market". Run
`jfeeds locations` to see the split on your own fetch rather than taking that on trust —
on one real 1,323-row fetch, thirteen of the top twenty locations were German and Arbeitnow
alone was 78% of the corpus. Every `digest` also prints a one-line summary of where its
rows are, so a wrong-country result announces itself instead of looking like a quiet week.

## What it does NOT do

- **It does not scrape.** Only documented APIs and feeds. It parses no HTML, follows no
  sitemaps, and renders no JavaScript.
- **It does not work around a block.** Two boards were dropped from the source list for
  exactly this reason: Himalayas returns 403 to any honestly-identified client despite
  its `robots.txt` saying otherwise, and aijobs.net has no feed at its documented path.
  Spoofing a browser to get past either would be circumventing an access control.
- **It does not touch LinkedIn.** That needs a signed-in session and a different risk
  model entirely.
- **It counts location strings; it does not understand them.** `jfeeds locations` reports
  what the feeds stored, so `Berlin`, `Berlin HQ` and `Berlin, Germany` are three separate
  entries, and `Munich` and `München` are two. Grouping them would be a guess, and there
  is still **no location filter** — the tool can show you the corpus is German, it cannot
  hand you Spanish jobs it never fetched.
- **It does not republish.** This is personal aggregation. The database is not a dataset
  to redistribute — in the EU the *sui generis* database right (§§ 87a–87e UrhG, from
  Directive 96/9/EC) attaches to a substantial extract even though no individual posting
  is copyrightable.
- **It does not store recruiter contact details.** Emails and phone numbers are stripped
  from descriptions at ingest, before anything is written to disk.
- **It does not strip attribution.** Remote OK requires a dofollow backlink as a
  condition of API access; the report carries it, and removing it breaks your side of
  that arrangement.
- **It does not invent data.** A posting with no date renders as `—`, not as today. Three
  sources publish no dates at all — for those rows the report adds *when we first saw it*
  (`— seen 2d`), clearly labelled, because that is a fact about this tool and not a
  publication date.
- **It does not rank, score, or judge fit.** It matches your regexes and shows you what
  matched. Deciding what is worth applying to is yours.
- **It does not see the whole market.** These are eight free job boards, not an index of
  every vacancy. Employers post where they choose, and national employment services carry
  roles that never reach a free board. Absence here is not evidence a job does not exist.
  This gap is real and currently has no fix available to us: the roles in question sit
  behind interfaces built for their operators' own front-ends, and checked 2026-08-06,
  the EU's EURES portal does not mirror them either. Use a national employment service
  directly alongside this tool — it is not a substitute for one.

## Requirements

- Python 3.9 or newer. Standard library only — no third-party packages, so `python3`
  works as a runner alongside `uv`.
- macOS, Linux, or **WSL** — WSL is Linux as far as this is concerned, and the code is pure standard library with no shell-outs and no platform-specific paths. Config and database live under `~/.config/job-feeds/`, which on WSL means your WSL home, not `C:\Users\...`.
- No API keys, no accounts, no authentication of any kind. Every source is public.

## Configuration

`~/.config/job-feeds/config.json`. **The easiest way to create it is to ask Claude** —
describe the roles you want, where, and anything to rule out, and it writes the file. That
is the intended path: the lanes are regexes, and hand-writing them is the part most people
get wrong. `scripts/config.example.json` is there if you would rather edit JSON, but note
it encodes one person's career and matches the wrong jobs unedited.

Nothing is excluded by default. `exclude_company` and `exclude_title` both ship empty on
purpose — a first run should show you what the feeds actually contain before it hides any
of it. Once a firm you do not want has turned up three times, add its name; `jfeeds
digest` then reports how many rows each rule removed, so an over-broad entry is visible
rather than silently eating half your results. `SKILL.md` carries a reference list of
common staffing intermediaries for when you want it.

`jfeeds doctor` tells you if the config is missing or malformed before you fetch anything.

See [`SKILL.md`](./SKILL.md) for the full field reference, the rules for writing lanes that
do not misfire, and the per-source notes (pagination depth, rate limits, and which feeds
carry no dates).

Data lives in `~/.config/job-feeds/jobs.db`. Rate-limit state is kept separately in
`ratelimit.json`, deliberately: deleting the database must never make the tool forget it
already polled a source.
