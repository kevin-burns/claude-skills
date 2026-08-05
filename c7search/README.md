# c7search

Look up a library's *current* documentation instead of recalling it. Wraps the
[Context7](https://context7.com) v2 API in a single Go binary with on-disk caching,
retries and semantic exit codes.

Part of [claude-skills](../README.md).

## What it does

Two operations: resolve a library name to an ID, then fetch documentation for that ID.
Payload goes to **stdout**, status messages to **stderr**, so stdout pipes straight into
model context without filtering.

```bash
LIB=$(c7search resolve --library-name "next.js" "app router middleware" \
        --json --limit 1 | jq -r '.[0].id')
c7search docs "$LIB" --topic "middleware" --tokens 4000
```

The value is narrow and real: it answers "what does this API actually look like *now*",
which is exactly the question a training cutoff makes unanswerable. Reach for it before
generating code against a library whose surface may have moved.

## What it does NOT do

- **It is not a search engine.** It looks up libraries in Context7's index. A library
  Context7 has not ingested is simply absent, and no phrasing will find it.
- **It does not verify that the docs are right.** Context7 indexes what a project
  publishes. If upstream docs are wrong or stale, so is this.
- **It does not run or test the code it returns.** Snippets are illustrative.
- **`ask` is deliberately discouraged.** It does resolve-and-fetch in one shot over
  free-form search, ranking the *entire query string*, so incidental keywords drag it to
  the wrong library. Measured misses: a query mentioning "mock" resolved to a
  mock-testing library, "plugins" to a plugins SDK, and "register a tool in fastmcp" to a
  Go dependency-injection library. Resolve by library **name** instead, then narrow with
  `--topic`. [`SKILL.md`](./SKILL.md) has the detail.

## Requirements

- The `c7search` binary: `go install github.com/kevin-burns/c7search@latest`, with
  `$(go env GOPATH)/bin` on `$PATH`. Release binaries and per-OS notes (macOS Gatekeeper,
  Windows SmartScreen) are in the [CLI README](https://github.com/kevin-burns/c7search#install).
- `jq`, for the two-step recipe above.
- **No API key needed.** `CONTEXT7_API_KEY=ctx7sk-…` is optional and only lifts rate
  limits; the anonymous tier is fine for casual lookups. `c7search auth status` reports
  which key is in use and whether the service is reachable.

If you cannot install a binary, the curl-based
[`context7` skill](https://github.com/intellectronica/agent-skills/blob/main/skills/context7/SKILL.md)
hits the same endpoints without the caching or retries.

## Worth knowing

**The cache is doing real work.** Search results live 6 hours on disk, documentation
payloads 24 hours — repeated queries run roughly 10× faster. Pass `--no-cache` only when
you genuinely need fresh data, such as a release you just published.

**Budget tokens to the question.** `1500` for one API signature, `4000–6000` for a
feature walkthrough (default `5000`), `10000+` for a whole-library reference — though the
anonymous tier may rate-limit at that size.

**Exit codes are semantic**, so a script can branch on them: `1` no results, `2` API
error, `3` auth, `4` usage. `--debug` is safe to leave on; bearer tokens and URL
credentials are scrubbed before any line reaches stderr.

## Provenance

The `c7search` CLI is an open-source tool (MIT):
<https://github.com/kevin-burns/c7search>. It queries Context7's public documentation
API, a third-party service. Neither the CLI nor this skill is affiliated with or endorsed
by Context7, and Context7's API terms and rate limits apply.
