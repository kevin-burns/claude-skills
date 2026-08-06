# Employer ATS feeds — terms read, endpoints measured

**Status: RESEARCHED AND PARKED 2026-08-06.** Terms are cleared for Greenhouse,
SmartRecruiters and Personio, and the capability is real — but this is **not being built**,
and the reason is neither terms nor capability. Tracking: `claude-skills-3do`.

> **Why it is parked — read this before picking it up.** Watching one employer requires two
> facts a jobseeker does not have and should not have to learn: *which ATS vendor* the
> employer runs, and *their slug on it*. `Watch Zalando` is not pollable; `("greenhouse",
> "zalando")` is. That asks the user to understand applicant-tracking vendors — a concept
> from our side of the fence, not theirs — and `job-feeds` promises that you install it and
> it searches for jobs.
>
> Two measurements make it worse. **Slug guessing is unreliable:** probing SmartRecruiters,
> three of four guesses (`Siemens`, `DeutscheTelekom`, `Zalando`) returned nothing; only
> `BoschGroup` worked — and that was with the documentation open. **And on SmartRecruiters a
> wrong slug is undetectable:** `zzznotacompany` and `Siemens` both return a byte-identical
> `200 {"totalFound":0,"content":[]}`. A typo does not error; it silently reports that an
> employer you care about never has openings. Greenhouse (`404`) and Personio (`307`) fail
> loudly — the vendor with the best data is the one that cannot warn you.
>
> **The complexity is the thing to solve first, not the client.** The most promising route
> measured so far is at the bottom of this file: a careers-page URL carries both facts
> deterministically, so *"paste the link to their jobs page"* could replace *"name the vendor
> and slug"* entirely, without ever fetching that URL. That is a shape, not a plan.

Everything below stands as measured. It is kept so that a later attempt starts from evidence
rather than from scratch.

This is the *watchlist* route: instead of asking a job board what is on the market, ask the
employers you care about what they are hiring for, using the same endpoint their own careers
page reads. Everything below was verified live on 2026-08-06 with the skill's honest
User-Agent (`job-feeds/0.1 (job-search feed aggregator)`), **no credential, no browser**.

## Why the provenance is stronger than any board we already use

This is first-party data. There is no intermediary deciding what to include, no
independent-operator drift (the Arbeitnow problem — a board that looks official but is one
person's side project), and no ambiguity about who published the posting. The employer runs
the ATS; the ATS publishes the feed; we read it. That is the same trust story as an RSS
feed, one employer at a time.

It also passes the test EURES failed: **the publisher documents the endpoint.**

## The three cleared vendors

### Greenhouse

Docs: <https://developers.greenhouse.io/job-board.html> — read 2026-08-06.

> Job Board data is publicly available, so authentication is not required for any GET
> endpoints.

Only the `POST` application-submission endpoint needs auth, and we never post. No rate limit
is documented, so the standing-minimum-interval rule applies (see below).

```
GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
  -> 200, gitlab: 188 jobs
```

Row: `id · title · location · absolute_url · company_name · first_published · updated_at ·
requisition_id · internal_job_id · language · metadata · data_compliance ·
application_deadline`

**Location is free text** — `{"name": "Remote, Italy"}`. Same weakness as our current eight.
Dates are real and there are two of them.

### SmartRecruiters — the strongest of the three

Docs: <https://developers.smartrecruiters.com/reference/v1listpostings> — read 2026-08-06.
The spec's `security` block lists `{}` alongside the token option, i.e. **unauthenticated is
an explicitly supported mode**, not an oversight. Described as *"Lists active postings
published by given company"*, with a `destination=PUBLIC` filter. `limit` maxes at 100.

Do not confuse this with the *Posting API* in the same docs — that one is for partner job
boards, requires `X-SmartToken`, and is not what we use.

Rate limiting is documented (<https://developers.smartrecruiters.com/docs/rate-limiting.md>):
**10 requests/second**, 8 concurrent, `429` when exceeded, and four headers on every
response — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Concurrent-Limit`,
`X-RateLimit-Concurrent-Remaining`. No `Retry-After`; the docs recommend **exponential
backoff** off those headers, which `job-feeds`' `RateLimiter` now does.

```
GET https://api.smartrecruiters.com/v1/companies/{companyId}/postings?limit=100
  -> 200, BoschGroup: totalFound 4757
```

Row: `id · uuid · name · company · department · function · industry · location ·
experienceLevel · typeOfEmployment · releasedDate · ref · refNumber · jobAdId · language ·
visibility · customField · creator · defaultJobAd`

**It returns a structured location, and this is the find that matters:**

```json
{"city": "Wuxi", "region": "Jiangsu", "country": "cn", "postalCode": "214000",
 "remote": false, "hybrid": false, "latitude": "...", "longitude": "...", "fullLocation": "..."}
```

An **ISO country code**, plus city, region, postcode, coordinates, and explicit `remote` /
`hybrid` booleans. This is precisely what `claude-skills-atj` and `claude-skills-0oe` were
closed for lacking: 348 inconsistent location strings across the eight boards, German cities
arriving bare, `Germany` matching 40 of ~806 German rows. Here no inference is needed at all
— the country is a code, and "is it remote" is a boolean rather than a guess at the word
"Flexible".

### Personio — the German one

Official spec in Personio's own GitHub org:
<https://github.com/personio/api-docs> (`personio-recruiting-api.yaml`) — read 2026-08-06.
*"The Recruiting API allows you to GET open job positions, and POST applications to
Personio."* The feed endpoint is described as *"the job positions XML feed from the Company
Career Site"*. No authentication required.

```
GET https://{company}.jobs.personio.de/xml     (also .personio.com)
  -> 200, XML
```

Fields: `id · name · department · office · additionalOffices · subcompany · recruitingCategory ·
employmentType · seniority · schedule · yearsOfExperience · occupation · occupationCategory ·
createdAt · jobDescriptions`

`office` is an **enumerated employer-configured value** (`Munich`, `Berlin`) rather than free
text — not as good as SmartRecruiters' ISO code, but far more consistent than what the boards
give us. `createdAt` is a real ISO timestamp.

**A consent signal worth noting:** the employer must explicitly switch this feed on
(Settings → Recruiting → Career page). Its existence means someone chose to publish it.

## Probed and working, but terms NOT yet read — do not adopt these yet

| Vendor | Probe result |
|---|---|
| Ashby | `api.ashbyhq.com/posting-api/job-board/ramp` → 200, 2.0 MB |
| Lever | `api.lever.co/v0/postings/palantir?mode=json` → 200, 301 postings (bad slugs 404 cleanly) |
| Workable | `apply.workable.com/api/v1/widget/accounts/hotjar` → 200 (0 open roles) |

Working is not permission. Each needs its own terms read before adoption — that is the whole
lesson of the EURES writeup next door.

## Two things this fixes that the current eight cannot

1. **Dates.** All three publish real timestamps (`first_published`/`updated_at`,
   `releasedDate`, `createdAt`). Three of our current sources publish no dates at all.
2. **Location.** SmartRecruiters gives an ISO country code and remote/hybrid booleans;
   Personio gives an enumerated office. Neither needs the string-matching that was measured
   and rejected.

## The design constraint — this is not a ninth source

A source answers *"what is on the market"*. This answers *"what are the employers I care
about hiring for"*. It needs a per-user employer watchlist, so it belongs alongside lanes as
its own capability, **not as another row in `SOURCES`**. Bolting it onto the existing source
loop would be wrong: there is no single URL to poll, the fan-out is per employer, and a
missing employer is a config fact rather than a dead feed.

## Rate limiting

Only SmartRecruiters documents a limit. Per the EURES writeup's rule — *no documented limit
is not permission* — Greenhouse and Personio get a deliberately conservative standing
interval chosen up front. Polling is naturally low-volume (one request per employer), but a
watchlist of 50 employers is still 50 requests, so the fan-out needs pacing, not just the
per-source interval.

## Slug behaviour — measured, and the reason this is parked

```
greenhouse       zzznotacompany  -> 404  {"status":404,"error":"Job not found"}
smartrecruiters  zzznotacompany  -> 200  {"totalFound":0,"content":[]}
smartrecruiters  Siemens         -> 200  {"totalFound":0,"content":[]}   <- identical
personio         zzznotacompany  -> 307  (redirect; detectable if not followed)
```

Correction to an earlier note in this file's history: slugs do **not** all "fail cleanly".
Greenhouse and Personio do. SmartRecruiters does not, and it is the one with the structured
location data.

Any future attempt therefore needs two rules: never accept a slug that was guessed rather
than derived, and treat a watchlist entry that has *never once* returned a posting as
*possibly misconfigured* rather than reporting it as "not hiring".

## The route a future attempt should take

A careers-page URL carries both required facts deterministically — hostname gives the vendor,
path gives the slug:

```
job-boards.greenhouse.io/gitlab/...      -> greenhouse      / gitlab
jobs.smartrecruiters.com/BoschGroup/...  -> smartrecruiters / BoschGroup
{company}.jobs.personio.de               -> personio        / {company}
```

So *"paste the link to their jobs page"* replaces *"name the vendor and slug"*, with the URL
parsed as a query expression and **never fetched** — the same idea already attached to
`claude-skills-cbl`. This is recorded as a shape, not a commitment.

## Other open questions, if it is ever revisited
- **Which vendors first?** Greenhouse + SmartRecruiters + Personio gives breadth, the best
  location data, and the German angle. Ashby/Lever/Workable can follow once their terms are
  read.
- **Three more payload shapes** on top of the eight already normalised, one of them XML.
- **Does a watchlist change the dedup key?** The same role can appear on a board *and* on the
  employer's own feed. First-party should probably win.
