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
| `GET /shared-data-rest-api/public/reference/countries` | Valid `locationCodes` |
| `GET /shared-data-rest-api/public/esco/occupation/tree` | ESCO occupation hierarchy |
| `GET /autocomplete-repository-rest-api/public/v2.0/occupations` | Occupation autocomplete |

## Before adopting — the actual gate

1. Read europa.eu's terms of use and any EURES-specific reuse or API terms. The EU's
   general reuse policy (Decision 2011/833/EU) is permissive, but that must be **read, not
   assumed** — this is the whole reason EURES is not yet a source.
2. Check `robots.txt` again at adoption time. A prior spike found no `Disallow` for
   `/eures/`, but that was recorded on 2026-08-05 and is not a licence.
3. Decide the language question: store the original, the English translation, or both.
4. Re-verify the endpoints against this snapshot. It is pinned to April 2026 upstream and
   the service can move without the unofficial docs following.
