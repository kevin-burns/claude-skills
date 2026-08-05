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

```bash
jfeeds fetch                    # poll the sources
jfeeds digest --window 7        # what matched, as a table
jfeeds report --out jobs.html   # self-contained page, opens with no network
jfeeds sources                  # per-source status and why
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

## What it does NOT do

- **It does not scrape.** Only documented APIs and feeds. It parses no HTML, follows no
  sitemaps, and renders no JavaScript.
- **It does not work around a block.** Two boards were dropped from the source list for
  exactly this reason: Himalayas returns 403 to any honestly-identified client despite
  its `robots.txt` saying otherwise, and aijobs.net has no feed at its documented path.
  Spoofing a browser to get past either would be circumventing an access control.
- **It does not touch LinkedIn.** That needs a signed-in session and a different risk
  model entirely.
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
  sources publish no dates at all.
- **It does not rank, score, or judge fit.** It matches your regexes and shows you what
  matched. Deciding what is worth applying to is yours.

## Requirements

- Python 3.9 or newer. Standard library only — no third-party packages, so `python3`
  works as a runner alongside `uv`.
- macOS or Linux.
- No API keys, no accounts, no authentication of any kind. Every source is public.

## Configuration

`~/.config/job-feeds/config.json` — copy `scripts/config.example.json` to start. See
[`SKILL.md`](./SKILL.md) for the full field reference and the per-source notes
(pagination depth, rate limits, and which feeds carry no dates).

Data lives in `~/.config/job-feeds/jobs.db`. Rate-limit state is kept separately in
`ratelimit.json`, deliberately: deleting the database must never make the tool forget it
already polled a source.
