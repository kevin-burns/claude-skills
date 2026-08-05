---
name: job-feeds
description: >
  Aggregate sanctioned public job feeds into one deduplicated local database, match
  postings against the user's career lanes, and render a filterable self-contained HTML
  report. Use whenever the user wants to search or monitor job boards - "find me remote
  platform engineering roles", "what jobs came up this week", "check the job boards",
  "aggregate job listings", "what's new since I last looked" - or wants a report of
  current openings across multiple sites. Covers eight documented JSON APIs and RSS
  feeds (Arbeitnow, Jobicy, Remotive, Remote OK, Working Nomads, 4 Day Week, We Work
  Remotely, Python.org Jobs), weighted towards the German and EU-remote market. NOT for
  LinkedIn - that needs a signed-in session and is a separate tool. This skill never
  scrapes HTML, never works around a block, and never republishes what it collects.
---

# job-feeds

Eight job boards, one deduplicated database, one report. Every source is a **documented
JSON API or RSS feed the publisher offers** — this is not a scraper.

## Provenance

Data comes from, and credit is due to:
[Arbeitnow](https://www.arbeitnow.com) · [Jobicy](https://jobicy.com) ·
[Remotive](https://remotive.com) · [Remote OK](https://remoteok.com) ·
[Working Nomads](https://www.workingnomads.com) · [4 Day Week](https://4dayweek.io) ·
[We Work Remotely](https://weworkremotely.com) ·
[Python.org Jobs](https://www.python.org/jobs/)

**Remote OK requires attribution and a dofollow backlink** as a condition of API access,
and Arbeitnow's `meta.terms` asks the same. The generated report carries these
automatically. Do not strip them.

## Setup

The script is stdlib-only, so `python3` works as well as `uv`. Define the function at the
**start of each command block** — shell state does not persist between calls, and a
relative path will not resolve from another repo:

```bash
# uv preferred; resolve it even when it is off PATH:
UV="$(command -v uv || ls "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)"
jfeeds() { "$UV" run python "$HOME/.claude/skills/job-feeds/scripts/job_feeds.py" "$@"; }

# stdlib-only, so this fallback is fully supported:
jfeeds() { python3 "$HOME/.claude/skills/job-feeds/scripts/job_feeds.py" "$@"; }
```

The function is named `jfeeds`, **not `jobs`** — `jobs` is a shell builtin.

First run:

```bash
mkdir -p ~/.config/job-feeds
cp "$HOME/.claude/skills/job-feeds/scripts/config.example.json" ~/.config/job-feeds/config.json
jfeeds doctor
```

Then edit `~/.config/job-feeds/config.json` — the `lanes` are the part that matters; they
decide what counts as a match.

## Commands

```bash
jfeeds fetch                      # poll every enabled source into the local database
jfeeds fetch --only arbeitnow,wwr # poll a subset
jfeeds digest                     # matched roles as a table
jfeeds digest --window 7 --remote # narrower window, remote only
jfeeds digest --json              # machine-readable, always valid JSON even when empty
jfeeds report --out jobs.html     # self-contained HTML, opens with no network
jfeeds sources                    # per-source status, staleness, and WHY
jfeeds doctor                     # config and counts, makes no network calls
```

`fetch` and `digest` are separate on purpose: fetching is rate-limited, so re-reading
what you already have must cost nothing. `digest` and `report` make **zero network
calls**.

Exit codes: `0` clean, `1` one or more sources failed or drifted (the rest still
printed), `2` config or usage error.

## Smoke testing without tripping rate limits

Free feeds are free because they are not abused. Verify the pipeline with the
**smallest possible footprint**, not the full sweep:

```bash
jfeeds doctor                                        # zero network calls
jfeeds fetch --only pythonorg --max-pages 1          # ONE request, ~70KB
jfeeds sources
jfeeds digest
jfeeds report --out /tmp/jobs.html                   # zero network calls
```

`python.org` is the lightest source — 20 items, no pagination, no documented limit.
`doctor`, `digest` and `sources` never touch the network at all, and `report` reads only
what is already stored, so the whole check above costs exactly one HTTP request.

For a check with **zero** requests, run the offline eval instead — it exercises drift
rejection, dedupe, backoff, escaping and attribution against recorded fixtures:

```bash
python3 "$HOME/.claude/skills/job-feeds/evals/grade.py"
```

Do **not** disguise the client to get more throughput. A browser-shaped User-Agent evades
the fair-use terms under which these feeds are handed out with no API key, and it does not
work anyway: rate limits key on request volume, not on the name attached to it. If you are
hitting limits the fix is fewer requests — `--only`, `--max-pages`, and letting the cache
do its job.

### Identifying yourself

The default User-Agent names the **tool**, never its author:

```
job-feeds/0.1 (job-search feed aggregator)
```

That is deliberate. This skill is installed by other people, so an author-tagged agent
would attribute every downstream user's traffic to one person — an operator investigating
abuse would find the wrong party, and that person's account name would be broadcast from
machines they have never touched.

If **you** want to be reachable — worth doing if you poll often — set your own contact:

```json
{ "defaults": { "contact": "mailto:you@example.org" } }
```

which sends `job-feeds/0.1 (job-search feed aggregator; +mailto:you@example.org)`. It is
optional, off by default, and yours alone. Control characters are stripped and the value
is capped, because a header value containing CRLF is header injection.

## Configuration

`~/.config/job-feeds/config.json`:

```json
{
  "defaults": {
    "window": 14,
    "exclude_company": ["randstad", "hays"],
    "exclude_title": ["recruiter", "werkstudent"]
  },
  "lanes": [
    { "name": "platform", "label": "Platform",
      "match": "platform engineer|terraform|kubernetes|landing zone" }
  ],
  "highlight": ["terragrunt", "finops", "agentic"],
  "sources": { "jobicy": { "enabled": false } }
}
```

- **`lanes`** — a job is shown only if it matches at least one lane's `match` regex,
  tested against title *and* description. A job can match several; all are shown.
- **`highlight`** — terms that star a row. They do not filter.
- **`exclude_company` / `exclude_title`** — plain case-insensitive substrings, not regex.
- **`sources`** — omit a source or set `enabled: false` to skip it.

The `lanes` shape deliberately mirrors `li-assist`'s `archetypes.json`, so lane
definitions copy across between the two tools. There is no `query` field here: these
feeds have no server-side boolean search, so matching is entirely local.

## What the sources actually give you

Verified 2026-08-05. Re-check before trusting any of it in six months.

| Source | Notes |
|---|---|
| Arbeitnow | Best single source for Germany. Paginates; board is **~7 days deep, 40 pages**. `links.last` is always null. |
| Jobicy | Documents **1 poll/hour fair use** — enforced; a second poll inside the hour is refused without a request. |
| Remotive | **Ignores `limit`.** Ships a legal notice in the payload. |
| Remote OK | First array element is a ToS object, not a job. Requires the backlink. |
| Working Nomads | Undocumented endpoint — treat as liable to vanish without notice. |
| 4 Day Week | `robots.txt` disallows `/api/` broadly but explicitly allows v1, v2 and mcp. |
| We Work Remotely | Per-category RSS. Titles are `"Company: Role"`. |
| Python.org | Tiny volume, high signal. **Carries no dates at all** — those rows are always undated. |

**`--window 14` cannot get 14 days from Arbeitnow**, which only holds about 7. Per-source
coverage is visible in `jfeeds sources`.

## When something looks wrong

Run `jfeeds sources` first — it reports *why*, not just what:

```
arbeitnow   throttled  2026-08-05T14:24:30Z   0 rows  HTTP 429 — backing off
remotive    degraded   2026-08-05T14:24:30Z   0 rows  schema-drift: missing publication_date
```

- **`degraded`** — the upstream renamed or removed a field. Every row from that source is
  rejected on purpose: half-parsing a changed feed yields rows full of silent nulls,
  which looks like a quiet day rather than a broken source. Fix the key set in
  `scripts/sources.py`.
- **`throttled`** — either a documented limit (Jobicy) or a 429/503. Wait; do not retry
  in a loop.
- **`failed`** — network or parse error. The other sources still ran.

If `fetch` reports nothing at all, check `doctor` first: an empty `lanes` list or a
disabled-everything `sources` block is a config problem, not a feed problem.

## Boundaries

This skill will not scrape HTML, follow sitemaps, spoof a user agent, or work around a
403 — Himalayas and aijobs.net were **dropped from the source list** for exactly that
reason. It does not touch LinkedIn. It strips recruiter emails and phone numbers at
ingest and is for personal aggregation only, not redistribution.
