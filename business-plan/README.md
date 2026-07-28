# business-plan

> Turn a founder's idea into a realistic, investor-credible **business plan** — full narrative plan, a one-page summary, and a ~300-word investor pitch — as editable Markdown. Its defining feature is honesty. Part of [claude-skills](../README.md).

## What it does

From your idea, purpose, and stage it builds a full plan: exec summary, problem, solution, market (bottoms-up TAM/SAM/SOM), competitor teardown, business model + pricing options, go-to-market (a concrete "first 10 paying customers" plan), a 12-month financial model with unit economics, risks (likelihood × impact × mitigation), a 90-day action plan, an **assumptions register**, a **validation-gaps** checklist, and a straight **go / no-go / reshape verdict**. Emphasis adapts to purpose — **investor** (traction, market, the ask), **internal** (execution, milestones), or **loan** (cash-flow, break-even, repayment).

The whole point is that every number is trustworthy: market/competitor facts are **researched and cited** (with an as-of date) or asked or left as a visible placeholder; financials are **computed from your assumptions** by a deterministic helper (`scripts/financials.py`) and labeled "derived from your inputs."

## How to use it well

- **State the purpose** — investor vs internal vs loan changes what it foregrounds.
- **Bring what you know** — your price point, target customer, stage, any competitors or traction. The more real facts you supply, the fewer placeholders.
- **Supply financial assumptions** for real numbers — price, expected growth/new customers, churn, unit cost, fixed costs, CAC. It runs these through the model; without them it uses clearly-labeled draft assumptions you can replace.
- **Trust the verdict** — if it says "too crowded" or "the unit economics don't work yet," that's the feature. A plan that only cheerleads isn't useful.
- **Close the validation gaps** it lists before you show the plan to anyone or spend real money.

## What it does NOT do

The honesty boundary is the point — it will not manufacture credibility:

- **It never invents a market size, a competitor's pricing/positioning, or a revenue figure.** Unknown facts are researched-and-cited, asked, or marked `[… — validate]` — never guessed.
- **It refuses the "make it look impressive" asks** — fill in the TAM, invent competitor numbers, produce a 5-year revenue forecast — and explains why fabricating those makes a plan worthless to an investor or bank.
- **Financials are computed from *your* assumptions, not forecast.** It does the arithmetic on your inputs; it does not predict the future or guarantee outcomes.
- **It is not legal, tax, or investment advice, and does not guarantee funding.** It structures and pressure-tests a plan; the facts and the decision are yours to verify.

## Requirements

`uv` (for the stdlib financials helper — no runtime dependencies; `scripts/financials.py` runs via `uv run`). For market/competitor research it uses web search if available; where research fails, it falls back to labeled placeholders rather than inventing. Optional: `report-builder` to render a shareable HTML version.
