# Section guides

Per-section how-to for the full business plan. `SKILL.md` covers the sourcing rules, the
workflow, and the financials helper; this file is where the per-section depth lives. Read the
relevant subsection while drafting that section, not all of it up front.

## Contents

- [Exec summary](#exec-summary)
- [Problem](#problem)
- [Solution / product](#solution--product)
- [Market (TAM/SAM/SOM)](#market-tamsamsom)
- [Competition](#competition)
- [Business model + pricing](#business-model--pricing)
- [Go-to-market](#go-to-market)
- [Financials](#financials)
- [Team](#team)
- [Funding ask](#funding-ask)
- [Risks & milestones](#risks--milestones)
- [Assumptions register](#assumptions-register)
- [Validation gaps](#validation-gaps)
- [Purpose adaptation](#purpose-adaptation)

## Exec summary

Keep it tight — a handful of short paragraphs, not a page. It doubles as the core of the one-pager,
so write it to stand alone: what the venture does, who it's for, why now, how it makes money, and
where it stands today. Every other section expands on a claim made here; don't introduce a claim in
the exec summary that no later section backs up. If you don't yet have a number for something it
touches (market size, traction), say the general shape here and push the specific, sourced figure to
its own section rather than dropping an unsourced number into the summary just because it reads
well.

## Problem

State who hurts and how much, in that order. "Who" needs to be a specific, recognizable customer,
not "businesses" or "people." "How much" is where the discipline bites: a cost, a time-sink, a
frequency — these are either something the founder has actually observed (user-supplied, label it
that way) or something you found in a survey/report (researched, cited, as-of). Never assert a pain
severity ("this costs SMBs $40B a year") as a bare fact. If you have neither, describe the pain
qualitatively and flag the severity as unverified in the validation gaps — a qualitative problem
statement without a fabricated number beats a quantified one you made up.

## Solution / product

Describe what it is and, more importantly, why it wins against the alternative the customer uses
today (including "doing nothing" or a spreadsheet). Avoid feature-listing — a bullet list of
capabilities reads like a spec sheet, not an argument. Instead, walk the mechanism: because the
product does X, the customer stops needing to do Y, which is the actual pain from the Problem
section. Tie every claimed advantage back to something in Problem or Competition; an advantage that
doesn't map to a named pain or a named competitor gap is filler.

## Market (TAM/SAM/SOM)

**Build it bottoms-up, not top-down.** The lazy version — "the global widget market is $50B, if we
capture just 1% that's $500M" — is a tell that no real sizing happened; investors have seen it
enough times to discount it on sight, and it should get the same discount from you. The credible
version multiplies things you can actually defend: realistic units × realistic price × the segment
you can actually reach.

- **TAM** (total addressable): everyone who could ever be a customer, sized bottoms-up where
  possible (number of target businesses/people × price they'd pay) rather than quoting an industry
  report's top-line figure as if it were this venture's opportunity.
- **SAM** (serviceable addressable): the slice reachable with this product and go-to-market —
  narrowed by geography, segment, or channel.
- **SOM** (serviceable obtainable): what's realistically capturable in the plan's time horizon,
  given real constraints (sales capacity, marketing budget, competition).

Every figure gets its provenance label — `(researched — <source>, as of <date>; verify)` if you
pulled a market report or comparable-company data point, `(you supplied)` if the founder gave you
the segment size from their own knowledge, or a placeholder (`[SAM — validate: no reliable segment
data found]`) if you have neither. A market section with three placeholder figures and honest labels
is more useful — and more credible — than one with three confident invented ones.

## Competition

Teardown **real, named competitors only** — either ones the founder named or ones you found and can
cite. Never invent a competitor, a competitor's price, or a competitor's positioning to fill out the
section; a fictional competitor is worse than no competitor, because it creates a false sense that
the landscape has been mapped when it hasn't.

For each real competitor, cover: what they do well, where they're weak, their pricing (cited, with
as-of date, or `(you supplied)` if the founder already knows it), and how they position themselves.
Then synthesize: where is there a positioning gap — a segment underserved, a price point unclaimed,
a workflow nobody's nailed — and how does this venture plan to win there. If research turns up
nothing (obscure niche, no public pricing), say so plainly and ask the founder who they think of as
competition rather than filling the gap with a plausible-sounding name.

## Business model + pricing

Present 2–3 revenue-model options — e.g. subscription, one-time/perpetual, usage-based, hybrid —
each with: how it actually makes money, a pricing structure, and its computed break-even (from the
financials helper, run once per option if the assumptions differ enough to matter). Then recommend
one, with the reasoning stated — why this model fits this customer's buying behavior and this
venture's cost structure better than the alternatives. Don't present options neutrally and stop;
the founder is asking you to reason, not to enumerate.

## Go-to-market

Make this concrete and near-term: a **first-10-paying-customers plan**, not a channel strategy
deck. Cover the fastest one or two channels that plausibly reach this specific customer (not a
generic list — cold outreach, a niche community, a partnership, content in a specific place they
already look), the core message that gets someone to say yes, and the move founders commonly skip:
usually **talking to the first customers by hand before automating anything**, or **pricing
confidently instead of underpricing to "get anyone in the door"** — name whichever applies. A
GTM section that reads like a marketing textbook (SEO + paid + content + partnerships, all at once,
with no sequencing) hasn't actually planned anything; force a real first move.

## Financials

Run the helper (see `SKILL.md`'s "Financials via the helper") and render its 12-month table
directly — don't re-derive or round the numbers by hand. Call out the burn (how negative it gets,
and for how long) and the break-even month explicitly near the top of the section, not buried in the
table.

**Note on break-even:** The break-even month reported here is the first month where that month's
operating net turns positive (revenue covers that month's costs) — not the month when cumulative
losses are fully repaid. A venture with strong unit economics can still show no operating
break-even within 12 months if fixed costs are high relative to early volume; flag this plainly
rather than letting readers misinterpret the number as a sign of poor health.

**Lead with unit economics, not top-line revenue.** Revenue growing is not the same as a business
that works; the helper's `unit_economics` block — contribution margin per customer, LTV, CAC
payback months, and the LTV:CAC ratio — is what actually decides viability, and a plan that leads
with "$50K MRR by month 12" while burying a sub-1.0 LTV:CAC ratio is misleading by omission. Put
unit economics first, revenue table second. When a value comes back `None` (undefined, not zero —
e.g. zero churn makes LTV undefined, zero contribution margin makes CAC payback undefined), render
it as **"n/a — needs a churn/margin assumption"**, never as 0 or a blank, since either of those
reads as a real number.

Flag the **3 make-or-break assumptions** explicitly — the ones where a plausible change (price
10% lower, churn 2 points higher, CAC 50% more expensive) would flip the verdict. Usually churn,
price, and CAC, but check against the actual sensitivity for this venture rather than assuming.

## Team

List who's involved and what they bring — user-supplied only. If the founder hasn't told you about
co-founders, advisors, or key hires, don't invent a "strong technical team" or a plausible-sounding
advisor; put `[team — not yet described]` as a placeholder and ask, especially for investor-purpose
plans where team is often the actual thing being evaluated. Gaps here (a technical solo founder with
no go-to-market background, say) belong in Risks, not smoothed over.

## Funding ask

Only include this section when purpose is `investor` or `loan`. State the amount, the specific use
of funds (not "general operations" — break it into the 2-4 things the money actually buys: a hire, a
mkt spend run, N months of runway), and the milestones that amount is meant to buy (the point where
the next raise, or loan repayment, becomes credible). Tie the milestones back to the 90-day plan and
the break-even month from Financials so the ask isn't a round number pulled from nowhere.

## Risks & milestones

Five risks, one from each category — market, execution, financial, legal, competitive — each with
**likelihood × impact × mitigation**. Resist the temptation to write generic risks ("the market
might not adopt the product") that apply to every venture ever pitched; make each one specific to
this venture (a single-supplier dependency, a regulatory approval this specific business needs, a
competitor with an obvious counter-move). A risk section that could be copy-pasted into any plan
isn't doing its job.

Follow it with a concrete **90-day action plan** — the specific next moves, roughly sequenced,
that de-risk the biggest unknowns first. This is what makes Risks read as something the founder can
act on Monday rather than a list to feel bad about.

## Assumptions register

Collect every assumption the plan rests on in one place — the financial ones (price, growth,
churn, unit cost, fixed costs, CAC) plus any narrative ones (assumed customer segment, assumed
channel effectiveness, assumed team hire timing). The point of centralizing them is that they can be
challenged individually: a reader should be able to look at this one table, disagree with a single
number, and immediately see which downstream figures move. Never let an assumption live only inside
a sentence elsewhere in the plan — if it's load-bearing, it belongs here too.

## Validation gaps

An explicit checklist of what the founder needs to verify before spending real money or time on this
— every placeholder from Market, Competition, and Team should show up here as a concrete
to-do ("confirm SAM with 10 customer interviews," "get real pricing from the top 3 named
competitors," "validate churn assumption against a pilot cohort"). This section is the deliberate
opposite of false confidence: it's where the plan admits, in one place, exactly what it doesn't
know yet.

## Purpose adaptation

Purpose changes what's foregrounded, not what's true. Same facts, same discipline, different
emphasis:

| Purpose | Leads with | Emphasizes |
|---|---|---|
| **investor** | The ~300-word investor summary | Traction, market opportunity, the funding ask, expected returns |
| **internal** | The one-page summary | Execution plan, milestones, the 90-day action plan, unit economics |
| **loan** | Cash-flow and break-even | Repayment capacity, downside scenario, conservative unit economics |

Ask for purpose in Step 1 of the workflow; if the founder doesn't state one, default to `internal`
and say so, since it's the least likely to overclaim.
