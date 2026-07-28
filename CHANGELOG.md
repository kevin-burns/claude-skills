# Changelog

Notable changes to the skills in this repo.

Entries are written to be useful to **both a human skimming for what's new and an agent deciding
whether a skill applies**. Each one says what the skill does, *when to reach for it*, and — the part
that usually matters more — **what it deliberately won't do**. A boundary is a design decision here,
not a missing feature, so it is recorded as such.

Dates are the date the work landed on `main`.

---

## 2026-07-29

### Changed — `terragrunt-skill` brought up to Terragrunt v1.1.1

The skill was pinned to **v1.1.0** (2026-07-01) and is now current with
[**v1.1.1**](https://github.com/gruntwork-io/terragrunt/releases/tag/v1.1.1) (2026-07-14).

**What actually changed upstream:** v1.1.1 is a bug-fix release with **no new GA surface**. It adds
two opt-in **experiments**, both on the `terraform` block, and both now documented in
`references/hcl-blocks.md` with the same version-gating the skill already applies elsewhere:

- **`oci`** — module sources from OCI Distribution registries: `source = "oci://ghcr.io/acme/terraform-modules/vpc?tag=1.0.0"`
- **`version-attribute`** — a `version` constraint for `tfr://` registry modules, e.g. `version = "~> 3.3"`, instead of pinning the version inside the source URL

**A correction worth calling out.** `SKILL.md` previously implied only two experiments remained
active after v1.1.0. Ten were active as of v1.1.1, six of which this skill has never documented.
The skill now says so plainly and tells the agent that an unfamiliar `--experiment` value is *not*
evidence of an error — look it up instead of flagging it. The same incomplete list in
`references/scale-and-performance.md` was corrected.

**Also added:** `terragrunt-crash-*.log` panic reports (new in v1.1.1) at the top of
`references/error-patterns.md`, flagged as a Terragrunt crash rather than a config error, so it
isn't diagnosed against a catalogue that cannot explain it. And an explicit note that
`terraform.source` cannot reference `dependency` outputs — module sources must resolve before the
dependency graph runs. v1.1.1 only improved the *error message* for this, but it is a real
constraint that was previously undocumented here.

**Verification honesty.** The twelve other v1.1.1 bug fixes need no documentation change — the skill
never documented any of those behaviours as limitations, so there is nothing to retract. Reference
footers now distinguish what was **spot-checked against docs** at v1.1.0 from what was **reviewed
against the v1.1.1 release notes**, rather than claiming a full re-verification that did not happen.

---

## 2026-07-28 / 2026-07-29

### Added — `cv-and-human` gains a LinkedIn profile mode

**What:** the skill now handles a second career document: a LinkedIn profile, on a **job-seeker
lens** — headline, About, and skills, optimised for LinkedIn Recruiter search and the human scan.

**Reach for it when:** someone wants their LinkedIn profile optimised, a headline or About section
rewritten, asks why they aren't showing up in recruiter searches, or wants their profile to match
their CV. Plain CV/ATS work is unchanged and still the skill's core.

**Why it lives here rather than in a new skill:** LinkedIn Recruiter search *is* automated screening
over a career document, so the host skill's thesis carries over unchanged — lock down the knowable,
controllable surface, feed the noisy judgment layer true material, never promise a score.

**The one structural difference that shapes the whole mode:** a CV is tailored 1:1 to a job
description; a profile is one artifact read by many people. You cannot keyword-tailor to twelve roles
at once without producing soup, which is why positioning comes before keywords, and why target-role
keywords are allowed in skills, experience and the *tail* of About but are **barred from the headline
and the first ~200 characters** — the only parts most humans read.

**Won't do:** any LinkedIn engagement automation — connecting, posting, commenting, messaging,
following or applying. That is a deliberate line, not a gap: it protects a real account against ToS
enforcement. It also won't scrape or fetch linkedin.com, invent roles/metrics/skills/endorsements,
promise search ranking, or write LinkedIn *posts* (those go to `hook-and-human` for persuasive copy,
`clear-and-human` for neutral).

**New tooling:** `scripts/li_profile_check.py` — character counts, the "see more" fold check, keyword
coverage, per-skill length. It counts **UTF-16 code units**, matching the browser-side counter
LinkedIn actually uses, so an emoji costs two characters exactly as it does in the real field.
Getting this wrong in the obvious way (Python's `len()`) would report a headline as fitting when
LinkedIn will truncate it.

**Also:** `cv-and-human` predated the repo's conventions and now has a README, evals and tests.

### Changed — routing between the three writing skills

`cv-and-human`, `clear-and-human` and `hook-and-human` had their trigger descriptions edited
**together**, so "my LinkedIn profile" reaches the profile mode while "write a LinkedIn post" still
reaches the marketing skill.

**If you edit any of those three descriptions, treat them as measured artifacts.** Dropping
`clear-and-human`'s CV carve-out was measured to regress "my resume sounds AI-written" routing from
4/4 to 2/4. `cv-and-human/tests/test_skill_contract.py` guards the invariants in well under a second
with no API cost — run it before assuming an edit is safe.

### Added — `travel-planning`

**What:** turns a trip request into a day-by-day itinerary plus a reconciled budget, as an editable
Markdown document.

**Reach for it when:** someone wants a trip planned, paced and budgeted — even if they never say
"itinerary".

**Won't do:** make bookings, transact, or read live seat/room inventory. It will do a best-effort web
lookup to anchor costs in typical or seasonal prices, and those are **labelled as estimates, not live
quotes**. Booking is steered to the actual booking sites, with the honest note that no single site is
reliably cheapest.

### Added — `business-plan`

**What:** a full narrative business plan, a one-page summary, and a ~300-word investor pitch.

**Reach for it when:** someone wants to plan, pitch or pressure-test a venture — size a market, tear
down competitors, build a go-to-market, produce investor-facing financials.

**Its defining feature is honesty.** It researches and cites market and competitor facts, computes
financials from *your* assumptions via a deterministic projector (`scripts/financials.py`), and marks
anything unknown as an explicit validate-this placeholder. It **never invents a market size, a
competitor's price, or a revenue number**, and it ends with a straight go / no-go / reshape verdict
rather than encouragement.

### Added — `nano-banana-pro-json` gains three creation modes

Beyond its photographic core, the image skill now carries recipes for:

- **Logos and brand identity** — brand brief → flat-vector prompt, then a **free local raster→SVG
  trace** of the winning concept (the step commercial logo generators charge for). Won't do trademark
  clearance or font-licence checks, and text in generated marks can be imperfect — verify any wordmark
  before shipping.
- **Product and marketing images** — e-commerce specs, identity-lock for a real product, consistent
  shot sets. Won't fabricate prices, claims or label text, and can subtly alter a real product's
  details, so verify against reality.
- **Infographics and diagrams** — layout and style vocabulary, labels supplied verbatim. It renders
  the *look* of an infographic, not trustworthy data: it garbles text and **invents numbers**. Supply
  the facts and verify them; for real data visualisation use `report-builder`.

Also added `4:5` and `3:4` aspect ratios, which the product and infographic recipes need.

### Added — the per-skill README convention

Every skill now carries a README covering **what it does / how to use it well / what it does NOT do**,
linking back to the repo README. The "does NOT do" section is the load-bearing one — it is what stops
a skill being reached for in situations it will handle badly. Documented in `CONTRIBUTING.md`.

---

## 2026-07-08

### Changed — `excalidraw-diagram` no longer ships its render engine

The 2.9 MB `excalidraw.mjs` bundle is no longer committed. It is fetched once from a pinned GitHub
Release on first render and verified against a recorded sha256, so the repo stays small and the
engine version stays pinned and tamper-evident.

### Added — `excalidraw-diagram` cloud icon-library ingestion

Ingests named vector icon libraries (AWS, Azure) with deterministic placement, so diagrams use real
provider iconography rather than approximations.
