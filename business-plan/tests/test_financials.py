from financials import Assumptions, project_financials


def test_flat_business_revenue_and_breakeven():
    # 100 customers, no growth/churn, $10/mo each, $2 COGS, $500 fixed, no CAC.
    a = Assumptions(price_per_customer_monthly=10, starting_customers=100,
                    new_customers_per_month=0, monthly_churn_rate=0.0,
                    variable_cost_per_customer_monthly=2, fixed_costs_monthly=500,
                    cac=0, months=12)
    r = project_financials(a)
    m1 = r["months"][0]
    assert m1["customers"] == 100
    assert m1["revenue"] == 1000       # 100 * 10
    assert m1["cogs"] == 200           # 100 * 2
    assert m1["gross_margin"] == 800
    assert m1["net"] == 300            # 800 - 500 - 0
    assert r["break_even_month"] == 1  # positive from month 1
    assert r["month12_revenue"] == 1000
    assert r["avg_monthly_burn_while_negative"] == 0.0


def test_churn_reduces_customers_each_month():
    a = Assumptions(price_per_customer_monthly=10, starting_customers=100,
                    new_customers_per_month=0, monthly_churn_rate=0.10,
                    variable_cost_per_customer_monthly=0, fixed_costs_monthly=0,
                    cac=0, months=3)
    r = project_financials(a)
    assert r["months"][0]["customers"] == 90   # 100 - round(10)
    assert r["months"][1]["customers"] == 81   # 90 - round(9)
    assert r["months"][2]["customers"] == 73   # 81 - round(8.1)=8 -> 73


def test_no_breakeven_returns_none_and_reports_burn():
    a = Assumptions(price_per_customer_monthly=1, starting_customers=1,
                    new_customers_per_month=0, monthly_churn_rate=0.0,
                    variable_cost_per_customer_monthly=0, fixed_costs_monthly=1000,
                    cac=0, months=12)
    r = project_financials(a)
    assert r["break_even_month"] is None
    assert r["avg_monthly_burn_while_negative"] == -999.0  # 1 - 1000 each month


def test_cac_is_charged_on_new_customers():
    a = Assumptions(price_per_customer_monthly=0, starting_customers=0,
                    new_customers_per_month=5, monthly_churn_rate=0.0,
                    variable_cost_per_customer_monthly=0, fixed_costs_monthly=0,
                    cac=20, months=1)
    r = project_financials(a)
    assert r["months"][0]["marketing"] == 100   # 5 * 20
    assert r["months"][0]["net"] == -100


def test_unit_economics():
    a = Assumptions(price_per_customer_monthly=30, starting_customers=0,
                    new_customers_per_month=10, monthly_churn_rate=0.05,
                    variable_cost_per_customer_monthly=5, fixed_costs_monthly=0,
                    cac=40, months=12)
    ue = project_financials(a)["unit_economics"]
    assert ue["contribution_margin_per_customer_monthly"] == 25   # 30 - 5
    assert ue["ltv"] == 500                # 25 / 0.05
    assert ue["cac_payback_months"] == 1.6  # 40 / 25
    assert ue["ltv_cac_ratio"] == 12.5     # 500 / 40


def test_unit_economics_handles_zero_churn_and_zero_margin():
    a = Assumptions(price_per_customer_monthly=5, starting_customers=0,
                    new_customers_per_month=1, monthly_churn_rate=0.0,
                    variable_cost_per_customer_monthly=5, fixed_costs_monthly=0,
                    cac=0, months=1)
    ue = project_financials(a)["unit_economics"]
    assert ue["ltv"] is None                # churn 0 -> LTV undefined
    assert ue["cac_payback_months"] is None  # contribution margin 0 -> undefined
    assert ue["ltv_cac_ratio"] is None


def test_month12_revenue_is_actually_month_12():
    a = Assumptions(price_per_customer_monthly=10, starting_customers=100,
                    new_customers_per_month=0, monthly_churn_rate=0.0,
                    variable_cost_per_customer_monthly=0, fixed_costs_monthly=0,
                    cac=0, months=6)
    assert project_financials(a)["month12_revenue"] is None   # horizon shorter than 12
    a12 = Assumptions(price_per_customer_monthly=10, starting_customers=100,
                      new_customers_per_month=0, monthly_churn_rate=0.0,
                      variable_cost_per_customer_monthly=0, fixed_costs_monthly=0,
                      cac=0, months=12)
    assert project_financials(a12)["month12_revenue"] == 1000
