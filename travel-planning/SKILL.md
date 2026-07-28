---
name: travel-planning
description: >
  Turn a trip request into a structured, editable travel plan — a day-by-day itinerary plus a
  reconciled budget — as a Markdown document. Use this whenever the user wants to plan a trip,
  vacation, or holiday: "help me plan a week in Portugal", "build an itinerary for 5 days in
  Tokyo with my kids", "map out a road trip", "we have $3k for a long weekend, what can we do",
  "organize my Japan trip", or any request to structure travel across days and a budget — even
  if they don't say the word "itinerary". This is a reasoning-and-structuring skill: it plans,
  paces, and budgets, and will do a best-effort web lookup to anchor cost estimates in typical or
  seasonal prices (labeled, sourced, not live quotes). It does NOT make bookings, transact, or read
  real-time seat/room inventory — steer those to the actual booking sites and keep planning.
---

# Travel Planning

Turn a loose trip idea into a plan someone can actually act on: a paced day-by-day itinerary and a
budget that's been reconciled against what the traveler can spend. The output is a single editable
Markdown file they can tweak by hand afterward.

## What this skill is — and the hard boundary

The durable value here is **structure and judgment**: sequencing days so they flow, clustering
things by geography so no day zig-zags across a city, matching pace to the travelers, and turning a
budget number into a defensible allocation. That's what an LLM is genuinely good at and what a
traveler staring at a blank page actually needs.

**It does not book, and it never presents a number as a live quote it read off a site.** No
reservations, no "this exact flight is $142 right now", no availability or seat checks. Booking
needs accounts, payment, and liability a skill shouldn't take on; real-time fares render live and
usually can't be fetched reliably anyway.

What it *can* do — and should, when it helps — is **ground its estimates in retrieved data**: a
best-effort web lookup for *typical / seasonal* price levels for the route and dates, so the budget
is anchored in something real rather than guessed (see Step 3a). That's grounding, not a live quote,
and it's always labeled with an as-of date, a source, and "verify live." When cost comes up, this
skill gives **clearly-labeled estimate ranges** (grounded where possible) and tells the traveler
where to check current prices and book themselves. If the user asks you to actually book, or to
guarantee the single cheapest fare, say plainly that this skill plans and price-anchors the trip
but doesn't transact or read live inventory — then point them at the right tools, honestly, because
**no single site is reliably cheapest**; the real savings come from comparing a couple across
flexible dates:

- **Flights:** Google Flights is usually the best starting point (its date grid / price calendar and
  the "Explore" map are strongest for flexible dates and open destinations). Cross-check an
  aggregator or two — Skyscanner, Kayak, Momondo — knowing each misses some fares and none wins
  every time. Kiwi.com is worth a look for creative/virtual-interline routings. And check the
  **airline's own site** directly: it sometimes matches or undercuts the aggregators, and it's
  better for changes, cancellations, and loyalty points.
- **Hotels:** compare Booking.com and Google Hotels, and check the property **direct** — booking
  direct sometimes gets a better rate, free cancellation, or perks the OTAs don't show.

Name these as options to compare, not as a single recommendation — and never present a price from
any of them, since this skill isn't reading them live.

Beyond *where* to look, you can offer honest **general flight guidance** — always as rules of thumb,
never as predictions: which days/times of week tend to run cheaper for the route, a sensible booking
window (often ~1–3 months out for short-haul, ~2–5 for long-haul — verify for the specific route),
nearby or secondary airports worth pricing, and a **"book-it-now" target** — a fare that, for the
season, is good enough to just take rather than gamble on a drop. Ground these with retrieved
fare-trend data where you can (Step 3a). What you never do is *predict* a specific future price or
attach a fake confidence level to it.

## Accuracy discipline (this is what keeps the plan trustworthy)

A travel plan is full of specifics, and it's tempting to invent them. Don't. The difference between
a plan a traveler trusts and one they quietly discard is whether the specifics hold up.

- **Cost figures are always estimates, always labeled**, e.g. "≈ $700–1,100 (estimate — verify)".
  Never present a number as a real quote.
- **Well-known anchors are fine** — major sights, famous neighborhoods, typical activity *types*
  ("a kaiseki dinner", "a day trip to the coast"). These are general knowledge.
- **Don't fabricate operational specifics** you can't stand behind: exact opening hours, "open
  Tuesdays", precise ticket prices, "reserve at 2pm", the name of a specific small restaurant
  presented as a personal recommendation. Prefer the *type* or *area* and add a "verify hours/
  booking" flag. If the user supplied specifics (a hotel they booked, a show they have tickets
  for), use those verbatim.
- **State what you assumed.** Every plan you generate from incomplete input carries assumptions
  (pace, interests, home airport, season). Surface them in an Assumptions section so the traveler
  can correct them rather than discover them mid-trip.
- **Refuse the three flight-hack asks that only produce confident nonsense.** They circulate as
  "cheap flight" prompts and each one begs the model to fabricate — decline all three and offer the
  honest version instead:
  - *Predicting future fares* ("what will this route cost over the next 60 days, with a confidence
    level"). You can't, and a percentage is false precision. Give general booking-window rules of
    thumb instead, labeled as such.
  - *"Secret airlines that don't show on search sites," with direct booking links.* This reliably
    invents carriers and fake URLs. Name only real, checkable options (aggregators, the airline's
    own site).
  - *Specific promo codes or coupons.* Hallucinated discounts. You may note that a route or season
    tends to see sales, but never invent a code.

## Step 1 — Gather the inputs (ask, or assume and flag)

You need these to plan well. If the user gave them, use them. If key ones are missing and the user
wants a real plan, ask a short batched question. If they want a quick first draft, make reasonable
assumptions and record them in the Assumptions section rather than stalling.

Essential:
- **Destination(s)** — one place, or a multi-stop route.
- **Dates or duration** — exact dates (better: lets you place days and note season) or a length.
- **Travelers** — how many, and any that shape the plan (kids and their ages, mobility needs,
  someone who can't do stairs all day).
- **Budget** — a rough total, and whether it's per-person or for the group, and whether it
  includes flights. If they don't give one, plan the itinerary and give estimate ranges without
  reconciling.

Shape-the-trip:
- **Interests / trip style** — food, history, outdoors, nightlife, relaxation, photography; and the
  vibe (budget backpacking vs. mid-range vs. splurge).
- **Pace** — packed and efficient, or slow with downtime. When unsure, default to moderate:
  2–3 anchor activities a day with breathing room, not a forced march.
- **Constraints** — dietary needs, must-dos, hard no's, fixed fixtures (a wedding, a conference,
  a flight already booked).

## Step 2 — Design the itinerary (the judgment part)

Plan the days before you write them. Good itineraries share a few moves:

- **Cluster by geography.** Group each day around one area so travelers aren't crossing the city
  twice. This single move saves more real-world time than anything else.
- **Offer lodging as a choice, not a single pick.** Where they stay drives both budget and daily
  logistics, so give 2–3 candidate neighborhoods/areas, each with a rough nightly range (labeled
  estimate) and the tradeoff — the cheapest area usually costs commute time or a quieter scene;
  central costs money. Balance price, safety, and proximity to what they're actually doing, and let
  them pick their point on that curve.
- **Mix free/low-cost with one worthwhile splurge, and keep each day realistic on energy *and*
  money.** A day of all-paid attractions burns both; thread parks, neighborhoods, markets, and
  walks between the anchors, and save the splurges (a standout meal, one big ticket) for where they
  land best.
- **Match pace to the travelers.** Families with young kids and older travelers need slack, nap
  windows, fewer hard transitions. High-energy trips can pack more. Don't schedule every hour —
  leave gaps for meals, rest, and the good unplanned stuff.
- **Shape the arc.** Ease in on arrival day (jet lag, late check-in), put a marquee day mid-trip,
  wind down before departure. Front-load must-dos in case a later day gets rained out.
- **Give each day a spine, not a script.** A morning anchor, an afternoon anchor, a loose evening —
  plus a couple of "if you have time / rainy-day" alternates. Over-scripting makes a plan brittle;
  travelers deviate, and that's fine.
- **Account for transit and logistics** — arrival/departure days are partial, note rough travel
  time between stops on a multi-city route, flag anything that genuinely needs booking ahead
  (popular timed-entry sights, a specific train) as a "book ahead" note without inventing the price.

## Step 3 — Build the budget (hybrid: ranges + reconcile)

Two moves, combined:

1. **Bottom-up estimate ranges.** For each category — lodging, food, local transport, activities,
   and flights if in scope — give a rough range appropriate to the destination and the stated
   style, clearly labeled as an estimate to verify. Ranges, not point values, because you genuinely
   don't know the exact number and a range is the honest representation.
2. **Reconcile against their budget.** If the traveler gave a total, sum your estimate ranges and
   compare. Say whether it looks comfortably within, tight, or over — and if over, suggest concrete
   levers (cheaper lodging tier, fewer paid activities, shoulder-season dates, a shorter trip)
   rather than just flagging the gap.

Keep per-person vs. group and flights-in-or-out consistent with what they told you, and state which
you used. If they gave no budget, produce the estimate ranges and skip the reconciliation line.

## Step 3a — Ground the estimates in retrieved data (do this when prices matter)

Guessed ranges are weakest exactly where the traveler most needs them right: peak dates and
specific routes. Cherry-blossom April in Japan, Golden Week, Christmas, school holidays, a big
local event — these can *double* a baseline fare or hotel rate, and a plan that misses that is
misleading. So when dates and route are known and cost matters, do a **best-effort web lookup to
anchor the numbers** before you finalize the budget.

How to do it honestly:
- **Retrieve typical / seasonal levels, not live inventory.** Search for what the route and season
  actually cost — fare-trend and "how much does a trip to X cost / best time to fly to X" data,
  average nightly hotel rates for the area and season. You will usually get *ballpark ranges and
  seasonal signals*, and that is the right target — real-time seat-level fares render live and often
  can't be fetched, and that's fine.
- **Call out the peak-season premium explicitly.** If the dates fall in a known high-demand window,
  say so and reflect it in the range ("early-April = cherry-blossom peak; fares run well above the
  annual average"). This is the single most valuable thing grounding adds.
- **Label every retrieved figure** with an as-of date and where it came from, e.g.
  "≈ $1,400–1,800 round-trip — typical early-April NYC⇄Tokyo, retrieved 2026-07-28 from <source>;
  verify live before booking." Keep it a range; never launder a retrieved ballpark into a precise
  quote.
- **Degrade gracefully.** If a lookup fails, is blocked, or returns junk, fall back to a clearly
  labeled model estimate and *say* it's ungrounded. Never let a failed fetch block the plan, and
  never present a stale or shaky number as current.

Then feed these anchors into the Step 3 budget so the reconciliation is against real-ish numbers.
Grounding tells the traveler what to expect; the booking tools listed above are where they transact.

## Step 4 — Write the plan

Write to a Markdown file named for the trip, e.g. `trip-<destination>-<year>.md`. Use this
structure (adapt lengths to the trip — a long weekend doesn't need all of it):

```markdown
# <Destination> · <N> days · <travelers>
<one-line framing: dates/season, style, the shape of the trip>

## Overview
- Dates: … (season note if relevant)
- Travelers: …
- Style / pace: …
- Budget: <their total, per-person/group, flights in/out> — or "not specified"

## Itinerary
### Day 1 — <area/theme> (<date>)
- Morning: <anchor>
- Afternoon: <anchor>
- Evening: <loose>
- *If time / rainy day:* <alternate>
- *Notes:* <transit, book-ahead flags, verify-hours flags>
### Day 2 — …
… one section per day …

## Budget (estimates — verify before booking)
| Category   | Basis        | Estimate        |
|------------|--------------|-----------------|
| Lodging    | N nights     | $…–…            |
| Food       | per day ×N   | $…–…            |
| Local transit |           | $…–…            |
| Activities |              | $…–…            |
| Flights    | (if in scope)| $…–…            |
| **Est. total** |          | **$…–…**        |

<reconciliation line: "vs. your $X budget → comfortably within / tight / ~$Y over; to close the
gap, consider …">

## Prep checklist
<passport/visa reminder to verify, travel insurance, bookings to make ahead, packing notes tied to
season/activities, anything time-sensitive>

## Assumptions
<every gap you filled: assumed pace, interests, home airport, season, budget scope — so the
traveler can correct them>
```

## Step 5 — Offer refinement

A first plan is a starting point. Offer to adjust pace, swap days, shift the budget tier, add a
side trip, or export a shareable version. If the user later wants a polished, styled version to
share, it can be rendered to a single-page HTML plan via the `report-builder` skill — Markdown
stays the working document.
