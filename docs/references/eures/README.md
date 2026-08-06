# EURES API — local reference snapshot

**Status: REFERENCE ONLY. EURES is not an adopted `job-feeds` source.** The blocker is
terms of use, not capability. Tracking: `claude-skills-ffp`.

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

## Before adopting — the actual gate

1. Read europa.eu's terms of use and any EURES-specific reuse or API terms. The EU's
   general reuse policy (Decision 2011/833/EU) is permissive, but that must be **read, not
   assumed** — this is the whole reason EURES is not yet a source.
2. Check `robots.txt` again at adoption time. A prior spike found no `Disallow` for
   `/eures/`, but that was recorded on 2026-08-05 and is not a licence.
3. Decide the language question: store the original, the English translation, or both.
4. Re-verify the endpoints against this snapshot. It is pinned to April 2026 upstream and
   the service can move without the unofficial docs following.
