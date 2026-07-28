"""Deterministic 12-month financial projection from an assumptions register.

Pure arithmetic — no external data, no forecasting. Every output is a function
of the caller-supplied assumptions, so the business-plan skill can honestly
state that each figure is "derived from your inputs" and mean it literally.
The skill still elicits the assumptions from the user; this module only does
the math, correctly and reproducibly, so the plan's numbers trace to inputs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Assumptions:
    price_per_customer_monthly: float          # recurring revenue per active customer / month
    starting_customers: int
    new_customers_per_month: int               # gross new adds each month
    monthly_churn_rate: float                  # 0..1 fraction of customers lost per month
    variable_cost_per_customer_monthly: float  # COGS per active customer / month
    fixed_costs_monthly: float
    cac: float                                 # sales/marketing cost per new customer
    months: int = 12


def project_financials(a: Assumptions) -> dict:
    """Project month-by-month economics. Returns a JSON-serializable dict."""
    rows: list[dict] = []
    customers = a.starting_customers
    cumulative_net = 0.0
    break_even_month: int | None = None

    for m in range(1, a.months + 1):
        churned = round(customers * a.monthly_churn_rate)
        customers = max(0, customers - churned) + a.new_customers_per_month
        revenue = customers * a.price_per_customer_monthly
        cogs = customers * a.variable_cost_per_customer_monthly
        marketing = a.new_customers_per_month * a.cac
        gross_margin = revenue - cogs
        net = gross_margin - a.fixed_costs_monthly - marketing
        cumulative_net += net
        if break_even_month is None and net >= 0:
            break_even_month = m
        rows.append({
            "month": m,
            "customers": customers,
            "revenue": round(revenue, 2),
            "cogs": round(cogs, 2),
            "gross_margin": round(gross_margin, 2),
            "marketing": round(marketing, 2),
            "fixed_costs": round(a.fixed_costs_monthly, 2),
            "net": round(net, 2),
            "cumulative_net": round(cumulative_net, 2),
        })

    burn = [r["net"] for r in rows if r["net"] < 0]

    # Unit economics — the numbers that actually decide viability. Undefined
    # cases (zero churn -> infinite LTV; zero margin -> no payback) return None
    # rather than dividing by zero, so the skill can label them "n/a — needs a
    # churn/margin assumption" instead of printing a fake figure.
    contribution = a.price_per_customer_monthly - a.variable_cost_per_customer_monthly
    ltv = round(contribution / a.monthly_churn_rate, 2) if a.monthly_churn_rate > 0 else None
    cac_payback = round(a.cac / contribution, 2) if contribution > 0 else None
    ltv_cac = round(ltv / a.cac, 2) if (ltv is not None and a.cac > 0) else None

    return {
        "assumptions": asdict(a),
        "months": rows,
        "break_even_month": break_even_month,
        "avg_monthly_burn_while_negative": round(sum(burn) / len(burn), 2) if burn else 0.0,
        "month12_revenue": rows[11]["revenue"] if len(rows) >= 12 else None,
        "unit_economics": {
            "contribution_margin_per_customer_monthly": round(contribution, 2),
            "ltv": ltv,
            "cac_payback_months": cac_payback,
            "ltv_cac_ratio": ltv_cac,
        },
    }


if __name__ == "__main__":
    import json
    import sys
    # Reads an assumptions JSON object from argv[1] (file path) or stdin, prints the projection.
    raw = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
    data = json.loads(raw)
    print(json.dumps(project_financials(Assumptions(**data)), indent=2))
