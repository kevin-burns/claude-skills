# EURES API — local reference snapshot

**Status: REFERENCE ONLY — REJECTED 2026-08-06. EURES is not, and is not becoming, a
`job-feeds` source.** Capability was never the blocker; provenance is. The terms were read
and the reasoning is at the end of this file under *Terms of use*. Kept because the findings
are expensive to re-derive and the service is a recurring "why not just use EURES?"
suggestion. Tracking: `claude-skills-ffp`.

Read `openapi.yaml` beside this file rather than re-fetching from GitHub. It is pinned to
commit `6e5dd81cfb5ad744e6a52814739baef2fe5c5091` (2026-04-08), snapshotted 2026-08-06,
sha256 `a3597bd8741c7826dbb6e9d7aafb11c5b11b372ec3423789fa1131f18c639f3e`. 20 endpoints.

## Provenance, stated plainly

The upstream is **unofficial**: <https://github.com/rorar/EURES-API-Documentation> (MIT),
reverse-engineered and community-maintained, and it says so itself — *"not affiliated with
or endorsed by the European Commission or the EURES network"*. The endpoints it documents
are named `public` by the publisher and require no credential, but that is not the same
thing as an API the publisher offers and documents. `job-feeds`' trust story is the
latter, so **this sits adjacent to the rule, not inside it.**

## What was actually verified

2026-08-06, against the live service, using the skill's own honest User-Agent
(`job-feeds/0.1 (job-search feed aggregator)`) — no token, no cookie, no browser, no
impersonation, no retry:

```
GET  https://europa.eu/eures/api/jv-searchengine/public/statistics/getNumberOfJobs
  -> HTTP 200   {"numberOfJobs": 2865233}

POST https://europa.eu/eures/api/jv-searchengine/public/jv-search/search
  -> HTTP 200   {"numberRecords": 1342, "jvs": [...], "facets": {...}}
```

The search used `keywords: [{keyword: "platform engineer", specificSearchCode: EVERYWHERE}]`
and **`locationCodes: ["ES"]`**, returning 1,342 Spanish results; the first was a genuine
Spanish-language DevOps posting.

`sessionId` is required by the schema but accepted an arbitrary string
(`"job-feeds-probe"`). No XSRF token or session cookie was needed. A third-party project
([tonybenoy/eures-scrape-AI-Rank](https://github.com/tonybenoy/eures-scrape-AI-Rank))
drives EURES with Selenium and manages XSRF tokens — that is browser automation, it is
off-limits for this skill, and our probe shows it is also unnecessary.

## It throttles, and it expresses throttling as HTTP 500

**Read this before writing a client.** Roughly eight requests over five minutes on
2026-08-06 were enough to make the service return `500 Internal Server Error` to
*everything* — including `getNumberOfJobs`, the cheapest GET on the list, which had
returned `200 {"numberOfJobs":2865233}` four minutes earlier from the same machine and the
same honest User-Agent.

The 500 carries **no `Retry-After` header and no rate-limit headers of any kind.** That is
materially worse than a 429, because:

- A naive client reads 500 as a transient server fault and **retries**, which deepens the
  block. This is precisely the loop `job-feeds`' SKILL.md warns about for Arbeitnow.
- `job-feeds`' existing `RateLimiter` classifies 429 and 503 as `throttled` and everything
  else as `failed`. A 500 would therefore be reported as a broken source rather than a
  self-inflicted rate limit — the operator would go looking for schema drift.
- There is no signal to pace against. Arbeitnow at least publishes
  `x-ratelimit-limit`; here there is nothing.

So any EURES integration needs: a conservative fixed pace decided up front, treatment of
500 as *back off*, not *retry*, and a long cool-off. Do not tune this by experiment against
the live service — that is what caused it.

### Required client behaviour, against what `job-feeds` already has

**No documented limit is not permission.** EURES publishes no rate-limit terms, no
`Retry-After` and no headers, and it is a public service run for jobseekers — so it gets a
self-imposed limit rather than an absent one. Three requirements, and only the first is
already satisfied:

| Requirement | Status in `job-feeds` today |
|---|---|
| Persist poll state outside the DB; fail closed on ambiguity; thread-safe | **Present.** `RateLimiter` does all three, and honours `Retry-After` clamped to 60s–86400s |
| A **standing minimum interval** even with nothing documented | Mechanism exists (`source.rate_limit_seconds`, used by Jobicy's 1/hour) — EURES just needs a deliberately conservative value chosen up front |
| **Exponential backoff** on repeated throttling | **Missing.** `DEFAULT_BACKOFF_SECONDS = 3600` is flat. Being throttled five times records 3600 every time; it never escalates |

And one gap specific to this service:

> `fetch_all` only routes **429 and 503** into the backoff path (`job_feeds.py:442`).
> EURES throttles with **500**, which falls through to the generic error branch and is
> recorded as `failed` — no backoff written, so the next run walks straight back into the
> wall, which is the exact behaviour that comment at `:444` says it exists to prevent.

Fixing that for EURES alone is safe. Making 500 mean "throttled" for *all* sources is
**not** an obvious win: a genuinely broken feed returning 500 would be silently backed off
for an hour instead of surfacing as failed, which hides a real outage behind a
politeness feature. That should be a per-source policy, not a global rule.

Whether this is a rate limit or a coincident outage is **not established**. Both readings
fit the evidence; the timing points at us. Re-probe once, after hours, before concluding.

## Why this matters more than "another source"

**It filters by location server-side.** That is the exact capability `claude-skills-atj`
and `claude-skills-0oe` were closed over, on the measured finding that the eight current
feeds cannot support geography: 348 inconsistent location strings, German cities arriving
bare, `Germany` matching 40 of roughly 806 German rows. EURES needs none of that
inference. The Spain case that yielded **2 usable rows out of 1,323** returns **1,342**
here.

## Minimal working request

Base URL `https://europa.eu/eures/api`. Every field below is `required` by the schema —
empty arrays mean "no filter", they cannot be omitted.

```json
{
  "resultsPerPage": 10,
  "page": 1,
  "sortSearch": "BEST_MATCH",
  "keywords": [{"keyword": "platform engineer", "specificSearchCode": "EVERYWHERE"}],
  "publicationPeriod": null,
  "occupationUris": [], "skillUris": [], "requiredExperienceCodes": [],
  "positionScheduleCodes": [], "sectorCodes": [],
  "educationAndQualificationLevelCodes": [], "positionOfferingCodes": [],
  "locationCodes": ["ES"],
  "euresFlagCodes": [], "otherBenefitsCodes": [], "requiredLanguages": [],
  "minNumberPost": null,
  "sessionId": "job-feeds",
  "userPreferredLanguage": null,
  "requestLanguage": "en"
}
```

`resultsPerPage` is capped at **50**; `page` is 1-based. `publicationPeriod` accepts
`LAST_DAY`, `LAST_THREE_DAYS`, `LAST_WEEK`, `LAST_MONTH`, `LAST_VISIT` or `null` — the
recency control the other feeds lack.

## Response shape

Top level: `numberRecords`, `jvs[]`, `facets`. Each vacancy carries:

```
id · title · description · employer · locationMap · creationDate ·
lastModificationDate · numberOfPosts · positionScheduleCodes ·
jobCategoriesCodes · euresFlag · availableLanguages · translations · score
```

Note `description` arrives in the posting's own language (Spanish results are Spanish),
and `translations` / `availableLanguages` exist — a normaliser would need a language
decision the other eight sources never forced.

## Endpoints worth knowing (20 total, see `openapi.yaml`)

| Endpoint | Use |
|---|---|
| `POST /jv-searchengine/public/jv-search/search` | The one that matters |
| `GET /jv-searchengine/public/jv/id/{id}` | Single vacancy detail |
| `GET /jv-searchengine/public/statistics/getNumberOfJobs` | Cheapest liveness probe |
| `GET /jv-searchengine/public/statistics/getCountryStats` | Coverage by country |
| `GET /shared-data-rest-api/public/reference/countries` | Valid `locationCodes` — see below |
| `GET /shared-data-rest-api/public/esco/occupation/tree` | ESCO occupation hierarchy |
| `GET /autocomplete-repository-rest-api/public/v2.0/occupations` | Occupation autocomplete |

## Permissible `locationCodes` — partially captured, finish this first

`GET /shared-data-rest-api/public/reference/countries` returned **HTTP 200 and a flat array
of 31 ISO 3166-1 alpha-2 strings** on 2026-08-06. Verified from the response: the array
length is `31`, and its first two entries are `"AT"` and `"BE"`.

**The full enumeration was not captured before the service began returning 500s, and it is
deliberately not written out here from memory.** Thirty-one is exactly the size of EU-27
plus Iceland, Liechtenstein and Norway plus Switzerland, which is EURES' stated coverage —
so that is very likely the set. *Likely is not verified*, and a country list that is quietly
wrong is the kind of detail nobody re-checks. Run this once the service recovers and paste
the result in:

```bash
curl -s -H 'User-Agent: job-feeds/0.1 (job-search feed aggregator)' \
  https://europa.eu/eures/api/shared-data-rest-api/public/reference/countries
```

Two further things to capture in the same pass, since each is one request:

- **Labels.** The endpoint returns bare codes, no names. Check whether
  `/shared-data-rest-api/public/reference/countries` accepts a language parameter, or
  whether labels come from `/shared-data-rest-api/public/esco/label/{lang}`.
- **Volume per country.** `getCountryStats` is listed in the unofficial spec but returned
  **HTTP 500 on the very first call**, before any throttling — so treat that endpoint as
  documented-but-broken. Per-country counts may instead come from the `facets` block of a
  search response.

### Two schema claims that did not survive contact

Recorded because the unofficial spec asserts both:

- `keywords: []` is documented as "performs an unfiltered search across all vacancies". It
  returned **500**. Whether that is the empty array or the throttling is unresolved — the
  first empty-keyword call failed before other symptoms appeared, so it is probably real.
- Every array field is marked `required`, so none can be omitted even when empty. That part
  held: the working search sent all of them.

## Terms of use — read 2026-08-06. Outcome: DO NOT ADOPT

This was the gate. It has now been walked, and EURES **is not being adopted as a
`job-feeds` source**. What follows separates what was read first-party from what was not.

### Read first-party, verbatim

**European Commission legal notice** (<https://commission.europa.eu/legal-notice_en>):

> © European Union, 1995-2026

EU-owned content is licensed **CC BY 4.0** *"unless otherwise indicated"*, under Commission
Decision **2011/833/EU**. Two carve-outs matter here: *"Third-party content requires direct
permission from rightholders"*, and industrial property (logos, trademarks, names) is
excluded.

**EURES / ELA legal notice** (<https://eures.europa.eu/eures-legal-notice_en>) — this is the
notice the search portal's own footer links to (bundle key `url.eures.legal.notice`):

> Copyright © for the entire content of this website unless otherwise stated: European
> Labour Authority (ELA).

> Re-use is authorised, provided that ELA is acknowledged as the source of the material.

> For individual documents, the general principle of re-use outlined above may be subject to
> specific conditions as indicated in individual copyright notices contained therein.

### NOT read first-party — and this is the one to resolve if EURES is ever revisited

Two independent web searches both report that the **"Find a job" service** carries its own
terms, distinct from the legal notice above, prohibiting *"screen scraping" or any other
automated or manual system to extract job vacancy data in order to further process or
re-publish the information*, and barring *unreasonable or disproportionately large load on
the website*.

**That wording is a search-engine summary, not a source, and it is recorded here as
unverified.** It could not be retrieved: `/eures/portal/jv-se/legal-notice` is an Angular
SPA that returns a 69 KB shell to any non-JS client, and the text is in none of the shell,
the ten preloaded chunks, or the i18n bundles. The Wayback Machine returned no usable
snapshot. Reading it would need a browser, which is off-limits for this skill.

### Why the outcome is the same either way

The unread clause is **not load-bearing**, which is why chasing it further was dropped:

1. **The vacancies are not ELA's content to license.** The ELA grant covers *"the content of
   this website"*; the vacancies are supplied by national public employment services. Both
   notices carve out third-party rights — *"unless otherwise stated"*, *"individual copyright
   notices"*, *"direct permission from rightholders"*. A blanket CC BY reading of two million
   third-party postings is an assumption, and assuming was the thing this gate existed to
   prevent.
2. **It fails the source rule on its own.** `job-feeds` admits *a documented JSON API or RSS
   feed the publisher offers*. EURES publishes no API documentation at all; the only spec is
   reverse-engineered and disclaims affiliation. That was true before any terms were read.
3. **There is no sanctioned alternative channel.** `data.europa.eu` was queried directly:
   EURES appears there only as **statistics** (placement counts, mostly Romanian national
   uploads). There is no vacancy dataset and no open-licensed feed.
4. **Republication risk is unchanged.** The *sui generis* database right (§§ 87a–87e UrhG,
   from Directive 96/9/EC) attaches to a substantial extract regardless of the licence on any
   individual posting.

So: capability was never the problem, and the server-side `locationCodes` filter remains
genuinely attractive. Provenance is the problem. **Do not adopt.**

### What would actually reopen this

Not a better probe — a better *channel*. Any one of: EURES publishing an official API with
terms; the vacancy data appearing on `data.europa.eu` under a named licence; or ELA
confirming in writing that reuse extends to vacancy data. Absent one of those, re-probing
the endpoint answers a question that was never the blocker.

### Still open, if the channel question is ever settled

1. Check `robots.txt` again at that point. A prior spike found no `Disallow` for `/eures/`
   (re-confirmed 2026-08-06: the only global rules are `/cgi-bin/`, `/eur-lex/`, `/archives/`
   plus `Crawl-delay: 10`). Absence of a `Disallow` is not a licence.
2. Decide the language question: store the original, the English translation, or both.
3. Re-verify the endpoints against this snapshot. It is pinned to April 2026 upstream and
   the service can move without the unofficial docs following.
