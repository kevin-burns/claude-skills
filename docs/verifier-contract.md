# The portable verifier contract

A small, domain-agnostic contract for any agent or pass whose job is to decide
whether a claim is *true* before it is trusted, committed, or sent — and to say so
in a way the caller can act on. It is the shared backbone under two things in this
repo that look unrelated but aren't:

- [`agents/fact-verifier.md`](../agents/fact-verifier.md) — verifies code/config
  claims (versions, API shapes, resource IDs) against cloud and library sources.
- [`cv-and-human`](../cv-and-human)'s red-team **Truth lens** — verifies that each
  notable CV claim is defensible, never fabricated.

Both are the *same* contract pointed at a different set of sources. This file holds
the part that never changes; each consumer supplies a **source profile** (below) for
the part that does. Write a new profile and you have a verifier for a new domain
without re-deriving the discipline.

## The core (never changes)

1. **Memory is not evidence.** Never assert a fact from training or recall. Every
   verdict must trace to a source you opened *during this run*; if none does, the
   verdict is UNVERIFIABLE. Fabricating a value — a GUID, a version, a metric, a
   job title — is the worst possible failure: it is caught downstream (a production
   incident, an interview), and it burns trust. When in doubt, return the lookup,
   not a guess.

2. **Three verdicts, exactly one per claim.**
   - **SUPPORTED** — a source you read confirms it. Carry the evidence (the quote or
     value) and the citation.
   - **REFUTED** — a source contradicts it. Carry the **correct value** and the
     citation. (Refuting *down* to the true, smaller claim is a fix, not an attack.)
   - **UNVERIFIABLE** — nothing in the available sources settles it. Carry the
     **exact lookup** the caller must run to resolve it. Never downgrade this to a
     guess; an honest UNVERIFIABLE beats a confident wrong answer.

3. **Source precedence — higher tier wins, conflicts reported.** When sources
   disagree, the higher tier governs and you state the conflict explicitly. The
   tiers are generic; the profile fills them in:
   1. **Sources of record** — the domain's ground truth (the repo for code; the
      candidate's real history for a CV).
   2. **Official / corroborating authority** — upstream docs, vendor specs, public
      evidence that independently backs the claim.
   3. **Memory-store hints** — a prior note; a *hint*, corroborate against (1)/(2)
      before a decision rests on it. Skip silently if absent.
   4. **Model memory** — NEVER. Not a source. If 1–3 can't settle it, UNVERIFIABLE.

4. **Read-only, least privilege.** A verifier observes; it does not mutate. No
   edit, commit, push, or apply. For live/runtime state you cannot safely read
   yourself (offline-first; auth may be absent), **return the read-only command**
   the caller should run and mark the claim UNVERIFIABLE rather than running a write
   or guessing. The verifier *finds*; someone else *fixes*.

5. **Structured and terse.** Emit a machine-readable verdict object, no prose
   padding. A clean pass with zero findings is a valid, common result — never
   manufacture findings to look busy.

The minimal verdict shape (a profile may rename fields or add domain ones):

```json
{
  "claim": "verbatim claim text",
  "verdict": "SUPPORTED | REFUTED | UNVERIFIABLE",
  "evidence": "what the source says / the value found (empty if unverifiable)",
  "correct_value": "REFUTED only — the right value",
  "citation": "path:line | url | id (empty if unverifiable)",
  "lookup_command": "UNVERIFIABLE only — exact read-only step to resolve it"
}
```

## The source profile (swaps per domain)

A profile is the only thing a new domain must write. It specifies four things:

- **What fills each precedence tier** — the concrete sources of record and
  authority for this domain.
- **How to read each source** — the exact read-only tool/command, and what a
  citation looks like.
- **The verdict vocabulary**, if the domain renames the three verdicts.
- **The live state you must not touch** — what to return a lookup for instead of
  reading.

### Profile A — code & cloud facts (`fact-verifier`)

- **Tier 1 (record):** repo sources — specs, schemas, lockfiles, `CLAUDE.md`/
  `AGENTS.md` — via `Grep`/`Glob`/`Read`; cite `path:line`.
- **Tier 2 (authority):** MS Learn MCP for Azure service/CLI facts; `c7search`
  (Context7) for library/framework/API behaviour; `WebFetch` for other official doc
  URLs. Cite the URL or library ID.
- **Tier 3 (hints):** Ogham/OpenBrain memory store, corroborated.
- **Live state, don't touch:** cloud resource GUIDs and deployed config — return the
  read-only command (`az account show --query id -o tsv`, …) and mark UNVERIFIABLE.
- Verdict vocabulary: the three names as-is. Full instance:
  [`agents/fact-verifier.md`](../agents/fact-verifier.md).

### Profile B — CV truth floor (`cv-and-human` Truth lens)

The claim under test is a notable CV statement — a metric, a title, a scope, an
"open source" label. The profile keeps the candidate honest *and* keeps the tailor
from inventing.

- **Tier 1 (record):** the candidate's real history — their own confirmation, the
  CV they supplied, their employment record, their public commits/repos, their
  certifications. Cite which.
- **Tier 2 (authority):** corroborating public evidence — a linked repo that
  actually shows the contribution, a credential-verification URL, a live demo.
- **Tier 3 / 4:** no memory tier; model memory NEVER — i.e. never invent a number,
  skill, employer, or title to fill a gap.
- **Verdict mapping:**
  - **SUPPORTED** → *defensible in an interview* — candidate-confirmed or backed by
    public evidence.
  - **REFUTED** → *overstated* — contradicted by the candidate's real history;
    carry the **true, smaller value** and correct the claim down to it.
  - **UNVERIFIABLE** → neither the candidate nor public evidence backs it yet;
    return the lookup ("ask the candidate for the real figure / the repo URL"). Until
    resolved it is a **candidate-decision gap**, never a fabricated fill.
- **Read-only:** the Truth lens *finds*; the tailor *fixes only the truthful ones*.
  A lens that writes the fix has left its lane (matches the red-team house rule
  "critique, don't propose"). Source: [`cv-and-human/references/red-team.md`](../cv-and-human/references/red-team.md).

## Writing a new profile

Name the four slots for your domain — record sources, authority sources, the
read-only lookups, the live state you won't touch — keep the core five rules
verbatim, and you have a verifier whose discipline you don't have to re-argue. The
contract is the moat; the profile is the adapter.

## Provenance

Distilled from this repo's `fact-verifier` and `coherence-checker` agents and the
`dev-fleet` fact-gate, generalised so non-code domains (starting with CV truth) can
reuse the same never-assert-from-memory / cite-refute-or-return-the-lookup floor.
