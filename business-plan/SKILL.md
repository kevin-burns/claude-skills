---
name: business-plan
description: >
  Build a realistic, investor-credible business plan from a founder's idea — full narrative plan,
  a one-page summary, and a ~300-word investor pitch — as an editable Markdown document. Use this
  whenever the user wants to plan, pitch, or pressure-test a venture: "write a business plan for
  my [idea]", "is my startup idea worth building", "build my go-to-market", "size this market",
  "do a competitor teardown", "make me an investor one-pager", "3-year financials for my SaaS",
  "should I raise for this". This skill's defining feature is honesty: it researches-and-cites
  market/competitor facts, computes financials from YOUR assumptions, marks anything unknown as a
  validate-this placeholder, and never invents a market size, a competitor's pricing, or a revenue
  number. It ends every plan with a straight go / no-go / reshape verdict, not cheerleading.
---

# Business Plan

Turn a founder's idea into a business plan they can actually act on — and, just as often, into an
honest signal that the idea isn't ready yet. "Business plan" prompts circulate as McKinsey-cosplay
("act as a world-class consultant and build my plan") that happily invent a TAM, a competitor's
price list, and a month-one revenue number. That output *looks* authoritative and is exactly the
kind of confidently-wrong artifact that falls apart the moment a founder shows it to an investor or
a loan officer. The value here isn't the polished document — plenty of things produce a polished
document. The value is that every number in it can be traced to somewhere real.

**The hard rule:** no market or financial figure appears as fact unless it's researched-and-cited
or user-supplied; unknowns are labeled placeholders, never guesses. That discipline is the product.
Everything below exists to make it easy to follow and hard to slip on.

## Sourcing rules by content-type

A business plan is three different kinds of content, and each has its own rule for where its facts
come from. Keep them straight — this is the thing that goes wrong first.

1. **Structure & reasoning — generate.** Exec summary framing, problem narrative, solution logic,
   business-model reasoning, GTM strategy, risk analysis. This is genuine LLM value-add: judgment
   and structure, not facts pulled from nowhere. No citation needed, no placeholder needed — write
   it well.
2. **External market facts — research, or ask, or placeholder. Never invent.** TAM/SAM/SOM,
   the competitor set and their pricing/positioning, market benchmarks. Do a best-effort lookup and
   cite it; if that's not possible, ask the founder directly; if neither works, leave a visible,
   labeled placeholder. Label convention: `(researched — <source>, as of <date>; verify)` or
   `(you supplied)`. A number with no label attached is a number nobody should trust — including you,
   two sections later.
3. **Financial projections — compute from the assumptions register.** Revenue, expenses, burn,
   break-even, unit economics. The model does arithmetic on the founder's own numbers; it never
   invents revenue. Label convention: `(derived from your inputs)`. See "Financials via the helper"
   below — this is arithmetic you run through a script, not math you do in your head.

If you can't label a figure with one of these three, you don't have a figure yet — you have a gap.
Gaps are fine. Silently-filled gaps are not; put them in the validation-gaps checklist instead.

## Refuse the fabrication asks

Founders under deadline pressure will sometimes push past the placeholder and ask you to just make
something up. Three asks come up repeatedly, and all three are asking for confident nonsense:

- **"Just fill in the TAM."** A market size invented to fill a blank is worse than an honest "not
  yet sized" — it's the exact figure an investor will poke at first, and it won't survive.
- **"Invent realistic competitor numbers."** There is no such thing as a realistic invented
  competitor price. Either it's a real competitor's real published price (cite it) or it's fiction
  wearing a business suit.
- **"Give me a 5-year revenue figure."** Five years out is not a projection, it's a guess dressed
  as a projection — and it will anchor decisions it has no business anchoring.

Decline all three, and say why in one sentence: an invented number is exactly what makes a plan
worthless the moment someone who knows the space looks at it. Then offer the honest version instead
— run the research, ask the question, or mark the placeholder and add it to validation gaps. Don't
just refuse and stop; refusing without an alternative is unhelpful. Offering the sourced or
assumption-driven version in the same breath is the actual point.

## Workflow

1. **Gather.** Get the idea, the target customer, the stage (pre-launch / early traction /
   scaling), the **purpose** (investor pitch, internal planning, loan application), and anything
   the founder already knows — named competitors, a price point they've tested, existing traction
   numbers. Ask one short batched question for the essentials rather than a long interview; if they
   want a fast first draft, make reasonable assumptions instead of stalling and record them in the
   assumptions register.
2. **Research market & competitor facts.** Best-effort web lookup for market size and the real,
   named competitor set plus their public pricing and positioning. Cite the source and the as-of
   date on everything you retrieve. If a lookup fails, is blocked, or comes back thin, degrade to
   asking the founder or to a labeled placeholder — never paper over the gap with an invented
   number.
3. **Elicit the assumptions register.** Price, customer growth, monthly churn, unit (variable) cost,
   fixed costs, and CAC — the inputs `scripts/financials.py` needs. Ask for these; don't estimate
   them yourself. Everything in the Financials section traces back to this register.
4. **Assemble the plan**, tuned to the stated purpose (see "Purpose adaptation" in the section
   guides), and generate the one-pager and investor summary alongside it.
5. **Surface validation gaps and the verdict.** List everything still unverified, then close with
   the honest go / no-go / reshape call — see below.

## Financials via the helper

Never hand-compute the 12-month model and never invent a revenue or burn number — run the
deterministic helper on the assumptions register you elicited in Step 3:

```bash
echo '<assumptions json>' | uv run python scripts/financials.py
```

Run it from the skill's own directory (the script lives in this skill's `scripts/`, a sibling of
`references/`). The JSON needs these keys — all required except `months`, which defaults to 12:

```json
{
  "price_per_customer_monthly": 49,
  "starting_customers": 10,
  "new_customers_per_month": 8,
  "monthly_churn_rate": 0.04,
  "variable_cost_per_customer_monthly": 8,
  "fixed_costs_monthly": 6000,
  "cac": 150
}
```

It returns a dict with `months` (the 12-row monthly table: customers, revenue, cogs, gross_margin,
marketing, fixed_costs, net, cumulative_net), `break_even_month`, `avg_monthly_burn_while_negative`,
and `unit_economics` (`contribution_margin_per_customer_monthly`, `ltv`, `cac_payback_months`,
`ltv_cac_ratio` — each a float or `None` when the math is undefined, e.g. zero churn makes LTV
undefined). Render the monthly table and break-even month straight into the Financials section, and
label every figure `(derived from your inputs)` — it's a literally true label because the script
does nothing but arithmetic on what the founder gave you.

Flag the **3 make-or-break assumptions** — usually churn, price, and CAC, since small changes to
these swing break-even and viability far more than the others — and say so explicitly next to the
table. See `references/section-guides.md` for how to present unit economics as the headline, not
top-line revenue.

## The three artifacts

Every run produces all three; which one is foregrounded depends on purpose:

- **Full plan** (`business-plan-<venture>.md`) — the working document, always produced in full.
- **One-page summary** — exec summary, revenue model, competitive edge, and the 90-day action plan.
  Foreground this for internal/planning purposes.
- **~300-word investor summary** — problem, solution, market, model, traction, team, ask, and a
  closing line. Foreground this for investor purposes; lead the whole plan with it.

## The honest verdict

Every plan closes with a required section: a straight **go / no-go / reshape** call, with the
reason stated plainly — "worth building as scoped," "too crowded as-is; here's the narrower wedge
that isn't," or "the unit economics don't work yet — churn and CAC need to move before this is
fundable." This is not a formality tacked onto the end. A plan willing to tell a founder *not* to
build, or to narrow the wedge, is the entire point of running this discipline instead of a
McKinsey-cosplay prompt: the founder gets a real signal instead of manufactured confidence, before
they've spent the money to find out the hard way.

## Output & pointer

Default output is Markdown (`business-plan-<venture>.md`, plus the one-pager and investor summary
as their own files or sections). If the founder wants something polished to actually hand to
someone, the `report-builder` skill can render a shareable single-page HTML version — Markdown
stays the working document either way.

For how to write each section well, read `references/section-guides.md`.
