# travel-planning

> Turn a trip idea into a structured, editable **itinerary + budget** — a Markdown plan you can act on and tweak by hand. Part of [claude-skills](../README.md).

## What it does

Give it a destination, dates, who's going, a rough budget, and what you're into. It produces a single Markdown file: a paced day-by-day itinerary (clustered by geography so no day zig-zags across a city), 2-3 lodging-area options with tradeoffs, and a budget broken down by category and reconciled against your total. Where prices matter, it does a best-effort web lookup to anchor estimates in *typical/seasonal* figures — labeled with a source and an as-of date — and calls out peak-season premiums (cherry-blossom April, Golden Week, holidays).

## How to use it well

- **Give it the essentials up front** — destination, dates (exact is better; lets it place days and flag season), number and type of travelers (kids' ages, mobility needs), a rough budget (say whether it's per-person or group, flights in or out), interests, and pace. Missing pieces become clearly-labeled assumptions you can correct.
- **Say the purpose** — a relaxed family trip and a packed solo city break want different pacing; tell it.
- **Treat the budget as a starting frame**, not a quote — the numbers are labeled estimates to verify.
- **Ask it to adjust** — swap days, change the budget tier, add a side trip. The Markdown is the working document; it can also render a shareable HTML version via `report-builder`.

## What it does NOT do

This is the important part — it plans and price-*anchors*, it does not transact:

- **No booking.** It never reserves flights, hotels, trains, or activities. It points you to where you book.
- **No live/real-time prices or availability.** It gives *typical/seasonal* ranges (labeled, sourced), not the fare showing on a site right now, and never presents a number as a live quote.
- **No "cheapest fare" guarantee or fare arbitrage.** It won't do hidden-city/virtual-interline tricks or claim to beat the aggregators. It offers honest guidance (which days tend to be cheaper, a sensible booking window, nearby airports) and sends you to Google Flights / Skyscanner / Kayak / the airline to compare — because no single site is reliably cheapest.
- **No invented specifics.** It won't fabricate exact opening hours, ticket prices, or a specific restaurant as a personal recommendation; it prefers the type/area and flags "verify."

## Requirements

None to plan. For price-grounding it uses web search if available; if a lookup fails it degrades to a clearly-labeled estimate. Optional: `report-builder` to render an HTML version.
