# WACC Builder

CAPM-based cost of capital calculator -- built to feed the `--wacc` parameter of [`Parametrized-DCF`](https://github.com/lucanap98/Parametrized-DCF), the fourth module in this due diligence toolkit.

Takes risk-free rate, beta (levered or unlevered), equity risk premium, an optional country risk premium, cost of debt, tax rate, and the debt/equity mix, and computes cost of equity, after-tax cost of debt, capital structure weights, and the weighted average cost of capital -- with the full breakdown shown, not just the final number.

## Why a separate module, not part of the DCF

The DCF already takes WACC as a direct parameter -- that was a deliberate v1 choice (see its README). This tool computes that number from first principles, but stays decoupled on purpose: run it once, read the breakdown, and either paste the result straight into the DCF's `--wacc` flag or override it with your own judgment call. Coupling the two would mean touching the DCF's tested engine every time a capital-structure assumption changes. Keeping them separate means each does one thing, and you stay the one deciding what WACC the valuation actually uses.

## Quick demo

```bash
pip install pandas openpyxl
python sample_assumptions.py       # generates a sample CAPM assumptions sheet
python wacc_builder.py sample_assumptions.xlsx
```

Output:

```
==============================================================================
WACC BUILDER -- COST OF CAPITAL (CAPM)
==============================================================================
Unlevered (asset) beta:                            0.90
Relevered beta (Hamada, target D/E):               1.00
Risk-free rate:                                    6.5%
Equity risk premium:                               5.0%
Country risk premium:                              2.0%
------------------------------------------------------------------------------
Cost of equity (Ke):                              13.5%
  = Rf + Beta x ERP + Country risk premium
------------------------------------------------------------------------------
Cost of debt, pre-tax (Kd):                       10.0%
Tax rate:                                         34.0%
Cost of debt, after-tax:                           6.6%
------------------------------------------------------------------------------
Debt:                                             1,500
Equity:                                           9,085
Weight of debt:                                   14.2%
Weight of equity:                                 85.8%
==============================================================================
WACC:                                            12.51%
==============================================================================
```

Debt (1,500) and Equity (9,085) here are the same net debt and equity value used in the `Parametrized-DCF` demo -- so the two tools tell one consistent story: a company valued at a 13% assumed WACC turns out to justify roughly 12.5% once you build the rate up from CAPM instead of guessing it.

## Two ways to supply beta

Provide **either** a levered `Beta` (if you already have one for the target company) **or** an `Unlevered Beta` plus the `Debt` / `Equity` mix, and the tool relevers it to the target capital structure via the Hamada equation. Supplying both is treated as an error -- ambiguous which one should drive the calculation. Unlevering a comparable's beta and relevering it to your target's own structure is the more defensible move when the target itself doesn't have a clean observable beta, which is the common case for a PME.

```bash
# quick sensitivity without touching the file
python wacc_builder.py sample_assumptions.xlsx --beta 1.1
python wacc_builder.py sample_assumptions.xlsx --country-risk-premium 0.03
```

Any CLI flag overrides the same-named value in the assumptions sheet, so you can sensitize one input at a time without editing the file.

## Using it on your own assumptions

Input format: Excel or CSV with the parameter name in the first column and its value in the next -- same "line item in, value out" spirit as the other modules. Required: `Risk-Free Rate`, `Equity Risk Premium`, `Cost of Debt`, `Tax Rate`, `Debt`, `Equity`, plus one of `Beta` or `Unlevered Beta`. `Country Risk Premium` is optional and defaults to 0.

```python
from wacc_builder import load_assumptions, compute_wacc

values = load_assumptions("premissas.xlsx", aliases={
    "Taxa livre de risco": "Risk-Free Rate",
    "Premio de risco de mercado": "Equity Risk Premium",
})
result = compute_wacc(**{
    "risk_free_rate": values["Risk-Free Rate"],
    "equity_risk_premium": values["Equity Risk Premium"],
    "cost_of_debt_pretax": values["Cost of Debt"],
    "tax_rate": values["Tax Rate"],
    "debt": values["Debt"],
    "equity": values["Equity"],
    "unlevered_beta": values.get("Unlevered Beta"),
    "beta": values.get("Beta"),
    "country_risk_premium": values["Country Risk Premium"],
})
result.print_summary()
```

## Design notes

- **Fails fast, like the DCF.** A WACC estimate built on incomplete inputs isn't a smaller estimate, it's an arbitrary one -- missing required parameters, an ambiguous beta (both or neither supplied), or a zero debt-plus-equity all raise a clear error and stop, rather than silently returning a number nobody should trust.
- **Country risk premium is separate from beta, not folded into it.** Some practitioners inflate beta to capture country risk; this tool keeps it as its own additive term in the cost of equity, which is more transparent and easier to challenge in a review.
- **Every intermediate number is shown**, not just the final WACC -- cost of equity, after-tax cost of debt, and both weights are printed, so the output doubles as the audit trail for how the rate was built.

## Roadmap

- [ ] Pull a default equity risk premium and risk-free rate from a public source (e.g. Damodaran's dataset) instead of requiring manual entry
- [ ] Support market-value weights computed automatically from a ticker (for the rare PME with a liquid comparable)
- [ ] Multi-scenario mode: low / base / high country risk premium in one run

## About

Built by [Luca Rivitti](https://www.linkedin.com/) -- Valuation & Transaction Advisory @ Grant Thornton Brasil. Fourth module in a series translating transaction advisory workflows into Python, alongside [`Financial-Model-Validator`](https://github.com/lucanap98/Financial-Model-Validator), [`Financial-Analysis`](https://github.com/lucanap98/Financial-Analysis), and [`Parametrized-DCF`](https://github.com/lucanap98/Parametrized-DCF).
