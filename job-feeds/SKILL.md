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

## First run — write the config FOR the user

`jfeeds doctor` exits 2 with `no config yet` until `~/.config/job-feeds/config.json`
exists. **Do not tell the user to copy the example and edit it.** The example encodes one
person's career; used unedited it matches the wrong jobs, and hand-editing regexes is the
part a user is least equipped to do well.

Instead, ask them three questions and write the file yourself:

1. **What roles are you after?** Plain English — "platform engineering and SRE", "data
   engineering", "engineering management". One lane per distinct track.
2. **Where?** Ask, but **be honest about the answer: there is no location filter.**
   There is no geography control at all. `--remote` is not one, and is worth
   understanding before you reach for it: it is **effectively a source selector, not a row
   filter.** Five of the eight feeds are remote-only boards whose normaliser sets the flag
   to a constant `1`, while Arbeitnow — 78% of the corpus — sets it on 6.8% of rows. So
   `--remote` roughly means "drop Arbeitnow and 4 Day Week", not "show me remote jobs".
   Measured on 1,323 rows: of the rows whose location plainly says remote, **52% carry
   `remote = 0`**, and 19% carry `remote = 1` while naming a specific office. It also
   discards rows whose flag is unset (all 20 Python.org rows), because the filter is SQL
   `AND remote = 1` and `NULL = 1` is falsy.

   Use `jfeeds locations` instead to see where the rows actually are.

   Coverage is decided by the source mix, not by config, and the mix is
   **German-weighted**: on a real run Arbeitnow supplied 84 of 98 matches. A test install
   for a Spain-based data engineer fetched 1,321 rows of which **two mentioned Spain**,
   neither a data role. So if the user is outside Germany and not targeting remote, say so
   *before* they invest in lanes — and then **measure it on their corpus, not on mine**:
   write a first-cut config, `jfeeds fetch`, then `jfeeds locations`, and read them their
   own top twenty. On the install those figures come from, thirteen of the top twenty
   locations were German and covered 606 rows — which answers the question far better than
   any warning.

   Order matters: `load_config` requires lanes, so `fetch` is impossible before a config
   exists. First-cut config → fetch → locations → *then* tune the lanes against what came
   back.
3. **Anything to rule out?** Agencies, previous employers, seniority levels. These become
   `exclude_company` and `exclude_title` — plain case-insensitive substrings, not regex.

   **Ask; do not assume.** Both lists ship empty on purpose. Excluding intermediaries is a
   preference, not a correction — a contractor or a freelancer may want exactly the
   marketplace postings someone else finds noise. If the user says they do want agencies
   filtered, offer the reference list under [Common intermediaries](#common-intermediaries)
   rather than making them recall names they have not seen yet.

Then write `~/.config/job-feeds/config.json`, run `jfeeds doctor` to confirm it parses, and
`jfeeds fetch && jfeeds digest` to show them real output. Tune the lanes against what comes
back rather than in the abstract — a lane is only judgeable once you see what it catches.

### Writing lanes that work

Three rules, each learned from a lane that misfired on live data:

- **Set `"match_in": "title"` on role-shaped lanes.** Measured across 229 real postings:
  every one of a Platform lane's *description* matches was wrong — an agency ad listing
  every discipline it staffs, a "Finance, Project Management, DevOps, Data" services blurb,
  an "e.g., Systems Engineer" aside, and one job advertising "**No** Kubernetes". Every
  *title* match was right. Role identity lives in the title.
- **Start narrow, widen after seeing results.** A lane of `\bai\b` matched 49 of 52 rows,
  including "Administrative Assistant" and "NO CURRENT OPENINGS", because their ad copy
  genuinely says "AI tools". Prefer role-shaped phrases: `ai engineer`, `machine learning
  engineer`, `llm`, `agentic`.
- **Anchor word boundaries.** `platform engineer` without a trailing `\b` also matches
  "Platform Engineer**ing**", which is exactly the phrase in agency boilerplate.

Keep the default `title+description` only where the *body* carries the signal — spotting a
niche tool like `terragrunt` in an otherwise generic "Senior Engineer" ad is the catch worth
having.

### A worked example

> "I'm after platform engineering or SRE work, Germany or remote-EU, and I don't want
> agencies."

```json
{
  "defaults": {
    "window": 14,
    "exclude_company": ["randstad", "hays"],
    "exclude_title": ["recruiter", "werkstudent"]
  },
  "lanes": [
    { "name": "platform", "label": "Platform", "match_in": "title",
      "match": "\\b(platform|infrastructure|devops|cloud|site reliability)\\s*(engineer|architect|lead)\\b|\\bsre\\b" }
  ],
  "highlight": ["terraform", "kubernetes"],
  "sources": {}
}
```

`sources` may be left empty — every source is enabled unless explicitly disabled.

**Only these keys are read.** Top level: `defaults`, `lanes`, `highlight`, `sources`.
Inside `defaults`: `window`, `contact`, `exclude_company`, `exclude_title`. Inside a lane:
`name`, `label`, `match`, `match_in`. Anything else is ignored — `jfeeds doctor` lists
unrecognised keys so a typo or an invented field is visible rather than silently dropped.

Two other flags exist for pointing at non-default locations, useful when testing:
`--config <path>` and `--db <path>`.

## Commands

```bash
jfeeds fetch                      # poll every enabled source into the local database
jfeeds fetch --only arbeitnow,wwr # poll a subset
jfeeds digest                     # matched roles as a table
jfeeds digest --window 7 --remote # narrower window; see the --remote caveat below
jfeeds digest --json              # machine-readable, always valid JSON even when empty
jfeeds report --out jobs.html     # self-contained HTML, opens with no network
jfeeds sources                    # per-source status, staleness, and WHY
jfeeds locations                  # where the fetched rows actually are
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
jfeeds locations
jfeeds digest
jfeeds report --out /tmp/jobs.html                   # zero network calls
```

`python.org` is the lightest source — 20 items, no pagination, no documented limit.

**If a source starts returning 429, look at your own request volume first.** During
development Arbeitnow throttled us repeatedly, and the cause was ours every time: the page
cap was 50, which is its entire advertised budget. Capping at 10 and pacing pages a second
apart fixed it completely — 1075 rows, status `ok`. Note its `x-ratelimit-remaining` header
cannot help you here: every response is a Cloudflare cache HIT, so it reports a constant
`49` rather than your real consumption.
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

- **`lanes`** — a job is shown only if it matches at least one lane's `match` regex. A job
  can match several; all are shown.
- **`match_in`** (per lane) — `"title"` or `"title+description"` (the default).

  **Use `"title"` for role-shaped lanes.** Measured on 229 live rows: of twelve
  Platform-lane hits, all four *title* matches were right and all eight *description*
  matches were wrong — an agency ad listing every discipline it staffs, a "Finance,
  Project Management, DevOps, Data" services blurb, an "e.g., Systems Engineer" aside, a
  section heading. Role identity lives in the title; a description lists everything a
  candidate might ever touch. Two rounds of regex tightening did not fix that, because it
  is not a regex problem.

  Keep the default when the *body* carries the signal you want — spotting `terragrunt` in
  an otherwise generic "Senior Engineer" ad is exactly the catch worth having.
- **`highlight`** — terms that star a row. They do not filter.
- **`exclude_company` / `exclude_title`** — plain case-insensitive substrings, not regex.
  `jfeeds digest` reports how many rows each rule removed and which terms fired, so an
  over-broad entry is findable rather than silently eating half your results.

  **Both ship empty**, and that is deliberate. A fresh install should show you what the
  feeds actually contain before anything is filtered out of them. Exclusions are a
  reaction — you run it, notice the same firm four times, add the name, and the exclusion
  report confirms it fired. Shipping someone else's conclusions inverts that: you would be
  pre-filtering firms you have never seen, and a contractor may want precisely the
  marketplace ads another user calls noise.

  There is deliberately **no automatic agency detection** either, and that one is a
  measured decision rather than a gap. Across 1,276 live rows no signal separated an
  intermediary from a direct employer: "our client" appeared in 7% of known-agency ads and
  4% of everything else, and posting volume was dominated by genuine employers hiring hard.
  A heuristic would be guesswork that silently drops real jobs.

  <a id="common-intermediaries"></a>
  **Common intermediaries — a reference list, not a default.** These are marketplaces and
  staff-augmentation firms that post under their *own* brand, so they read like direct
  employers and a substring like `recruitment` never catches them. Offer this list when a
  user asks to filter agencies; do not apply it unasked.

  ```
  randstad · hays · adecco · manpower · michael page · robert walters · robert half
  experis · gulp · hunting heads · proxify · toptal · turing · lemon.io · andela
  x-team · crossover · gun.io · arc.dev · zartis · globant · luxoft · epam
  grid dynamics · distributed systems · scalable path · gigster
  ```

  Verified against live postings on 2026-08-05. It is a starting point, not a taxonomy —
  the list any given user ends up with is the one they built from their own results.

  For `exclude_title`, the terms that come up most often are `recruiter` (ads *for*
  recruiters), and `werkstudent` / `praktikant` / `intern` on the German-weighted sources.
  Same rule: useful to offer, wrong to assume.
- **`sources`** — omit a source or set `enabled: false` to skip it.

The `lanes` shape deliberately mirrors `li-assist`'s `archetypes.json`, so lane
definitions copy across between the two tools. There is no `query` field here: these
feeds have no server-side boolean search, so matching is entirely local.

## What the sources actually give you

Verified 2026-08-05. Re-check before trusting any of it in six months.

| Source | Notes |
|---|---|
| Arbeitnow | Largest share of our German rows — 84 of 98 matches on a real run. **Share is not coverage:** it is an independent free job board built by one developer, carrying a sample of the market rather than the market. Roles seen on the Bundesagentur within the last week (NTT Data forward-deployed engineer, observed 2026-08-06) were absent here. Paginates; board is **~7 days deep, 40 pages**, `links.last` always null. Publishes `x-ratelimit-limit: 50` and is **burst-sensitive**: ten uncached pages in a second is enough to earn a 429. Pages are paced 1s apart and capped at 10 by default for exactly this reason. |
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
  in a loop. The wait **escalates on consecutive throttles** — one hour, then two, then
  four, up to a day — and resets the moment a poll succeeds. A server-sent `Retry-After`
  always wins over that curve, clamped to between a minute and a day. So a source that
  stays unhappy is left alone for progressively longer rather than being poked hourly
  forever.
- **`failed`** — network or parse error. The other sources still ran.

If `fetch` reports nothing at all, check `doctor` first: an empty `lanes` list or a
disabled-everything `sources` block is a config problem, not a feed problem.

## Boundaries

This skill will not scrape HTML, follow sitemaps, spoof a user agent, or work around a
403 — Himalayas and aijobs.net were **dropped from the source list** for exactly that
reason. It does not touch LinkedIn. It strips recruiter emails and phone numbers at
ingest and is for personal aggregation only, not redistribution.
