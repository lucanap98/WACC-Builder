"""
wacc_builder.py -- CAPM-based cost of capital (WACC) calculator.

Given risk-free rate, beta (levered or unlevered), equity risk premium,
an optional country risk premium, cost of debt, tax rate, and the
debt/equity mix, computes cost of equity, after-tax cost of debt, and the
weighted average cost of capital. Meant to feed the --wacc parameter of
Parametrized-DCF -- run this first, then paste (or override) the result.

Usage:
    python wacc_builder.py sample_assumptions.xlsx
    python wacc_builder.py sample_assumptions.xlsx --beta 1.1 --country-risk-premium 0.02
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Optional

import pandas as pd

REQUIRED_PARAMS = [
    "Risk-Free Rate",
    "Equity Risk Premium",
    "Cost of Debt",
    "Tax Rate",
    "Debt",
    "Equity",
]
OPTIONAL_PARAMS = ["Country Risk Premium", "Beta", "Unlevered Beta"]
ALL_PARAMS = REQUIRED_PARAMS + OPTIONAL_PARAMS


def load_assumptions(path: str, aliases: Optional[dict] = None) -> dict:
    """Load a single-column assumptions sheet: first column is the
    parameter name, the (first) remaining column is its value.

    If your sheet uses different labels (e.g. Portuguese), map them via
    `aliases`, e.g. {"Taxa livre de risco": "Risk-Free Rate"}.
    """
    lower = path.lower()
    if lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(path, index_col=0)
    elif lower.endswith(".csv"):
        df = pd.read_csv(path, index_col=0)
    else:
        raise ValueError(f"Unsupported file type: {path}. Use .xlsx, .xls or .csv.")

    if aliases:
        df = df.rename(index=aliases)

    value_col = df.columns[0]
    values = {}
    for name in df.index:
        if name in ALL_PARAMS:
            v = df.loc[name, value_col]
            values[name] = float(v) if pd.notna(v) else None

    missing = [p for p in REQUIRED_PARAMS if p not in values or values[p] is None]
    if missing:
        raise ValueError(
            "Missing required parameter(s): " + ", ".join(missing) + ". "
            "Found: " + ", ".join(str(i) for i in df.index) + ". "
            "Map non-English labels via the `aliases` argument to load_assumptions()."
        )

    has_beta = "Beta" in values and values["Beta"] is not None
    has_unlevered = "Unlevered Beta" in values and values["Unlevered Beta"] is not None
    if not has_beta and not has_unlevered:
        raise ValueError("Provide either 'Beta' (levered) or 'Unlevered Beta' in the assumptions sheet.")
    if has_beta and has_unlevered:
        raise ValueError(
            "Provide only one of 'Beta' (levered) or 'Unlevered Beta', not both -- "
            "ambiguous which one should drive the calculation."
        )

    values.setdefault("Country Risk Premium", 0.0)
    if values.get("Country Risk Premium") is None:
        values["Country Risk Premium"] = 0.0

    return values


def relever_beta(unlevered_beta: float, debt: float, equity: float, tax_rate: float) -> float:
    """Hamada equation: relevers an unlevered (asset) beta to the target
    capital structure given by debt and equity."""
    if equity <= 0:
        raise ValueError("Equity must be positive to relever beta.")
    return unlevered_beta * (1 + (1 - tax_rate) * (debt / equity))


@dataclass
class WACCResult:
    risk_free_rate: float
    equity_risk_premium: float
    country_risk_premium: float
    beta: float
    beta_was_relevered: bool
    unlevered_beta: Optional[float]
    cost_of_debt_pretax: float
    tax_rate: float
    cost_of_debt_aftertax: float
    debt: float
    equity: float
    weight_debt: float
    weight_equity: float
    cost_of_equity: float
    wacc: float

    def print_summary(self) -> None:
        print("=" * 78)
        print("WACC BUILDER -- COST OF CAPITAL (CAPM)")
        print("=" * 78)
        if self.beta_was_relevered:
            print(f"{'Unlevered (asset) beta:':<40}{self.unlevered_beta:>15.2f}")
            print(f"{'Relevered beta (Hamada, target D/E):':<40}{self.beta:>15.2f}")
        else:
            print(f"{'Beta (levered):':<40}{self.beta:>15.2f}")
        print(f"{'Risk-free rate:':<40}{self.risk_free_rate:>15.1%}")
        print(f"{'Equity risk premium:':<40}{self.equity_risk_premium:>15.1%}")
        print(f"{'Country risk premium:':<40}{self.country_risk_premium:>15.1%}")
        print("-" * 78)
        print(f"{'Cost of equity (Ke):':<40}{self.cost_of_equity:>15.1%}")
        print(f"{'  = Rf + Beta x ERP + Country risk premium':<78}")
        print("-" * 78)
        print(f"{'Cost of debt, pre-tax (Kd):':<40}{self.cost_of_debt_pretax:>15.1%}")
        print(f"{'Tax rate:':<40}{self.tax_rate:>15.1%}")
        print(f"{'Cost of debt, after-tax:':<40}{self.cost_of_debt_aftertax:>15.1%}")
        print("-" * 78)
        print(f"{'Debt:':<40}{self.debt:>15,.0f}")
        print(f"{'Equity:':<40}{self.equity:>15,.0f}")
        print(f"{'Weight of debt:':<40}{self.weight_debt:>15.1%}")
        print(f"{'Weight of equity:':<40}{self.weight_equity:>15.1%}")
        print("=" * 78)
        print(f"{'WACC:':<40}{self.wacc:>15.2%}")
        print("=" * 78)


def compute_wacc(
    risk_free_rate: float,
    equity_risk_premium: float,
    cost_of_debt_pretax: float,
    tax_rate: float,
    debt: float,
    equity: float,
    beta: Optional[float] = None,
    unlevered_beta: Optional[float] = None,
    country_risk_premium: float = 0.0,
) -> WACCResult:
    if beta is None and unlevered_beta is None:
        raise ValueError("Provide either beta (levered) or unlevered_beta.")
    if beta is not None and unlevered_beta is not None:
        raise ValueError("Provide only one of beta or unlevered_beta, not both.")
    if debt < 0 or equity < 0:
        raise ValueError("Debt and equity must be non-negative.")
    if debt + equity <= 0:
        raise ValueError("Debt + equity must be positive to compute capital structure weights.")

    beta_was_relevered = unlevered_beta is not None
    if beta_was_relevered:
        beta = relever_beta(unlevered_beta, debt, equity, tax_rate)

    cost_of_equity = risk_free_rate + beta * equity_risk_premium + country_risk_premium
    cost_of_debt_aftertax = cost_of_debt_pretax * (1 - tax_rate)

    weight_equity = equity / (debt + equity)
    weight_debt = debt / (debt + equity)

    wacc = weight_equity * cost_of_equity + weight_debt * cost_of_debt_aftertax

    return WACCResult(
        risk_free_rate=risk_free_rate, equity_risk_premium=equity_risk_premium,
        country_risk_premium=country_risk_premium, beta=beta,
        beta_was_relevered=beta_was_relevered, unlevered_beta=unlevered_beta,
        cost_of_debt_pretax=cost_of_debt_pretax, tax_rate=tax_rate,
        cost_of_debt_aftertax=cost_of_debt_aftertax, debt=debt, equity=equity,
        weight_debt=weight_debt, weight_equity=weight_equity,
        cost_of_equity=cost_of_equity, wacc=wacc,
    )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="CAPM-based WACC calculator from an assumptions sheet, with CLI overrides.")
    parser.add_argument("assumptions_file", help="Excel or CSV file: Parameter name in col 1, value in col 2.")
    parser.add_argument("--risk-free-rate", type=float, default=None, help="Override risk-free rate, e.g. 0.06.")
    parser.add_argument("--equity-risk-premium", type=float, default=None, help="Override equity risk premium.")
    parser.add_argument("--country-risk-premium", type=float, default=None, help="Override country risk premium.")
    parser.add_argument("--beta", type=float, default=None, help="Override levered beta.")
    parser.add_argument("--unlevered-beta", type=float, default=None, help="Override unlevered (asset) beta.")
    parser.add_argument("--cost-of-debt", type=float, default=None, help="Override pre-tax cost of debt.")
    parser.add_argument("--tax-rate", type=float, default=None, help="Override tax rate.")
    parser.add_argument("--debt", type=float, default=None, help="Override debt value.")
    parser.add_argument("--equity", type=float, default=None, help="Override equity value.")
    args = parser.parse_args(argv)

    try:
        values = load_assumptions(args.assumptions_file)

        beta = args.beta if args.beta is not None else values.get("Beta")
        unlevered_beta = args.unlevered_beta if args.unlevered_beta is not None else values.get("Unlevered Beta")
        if args.beta is not None:
            unlevered_beta = None
        if args.unlevered_beta is not None:
            beta = None

        result = compute_wacc(
            risk_free_rate=args.risk_free_rate if args.risk_free_rate is not None else values["Risk-Free Rate"],
            equity_risk_premium=args.equity_risk_premium if args.equity_risk_premium is not None else values["Equity Risk Premium"],
            cost_of_debt_pretax=args.cost_of_debt if args.cost_of_debt is not None else values["Cost of Debt"],
            tax_rate=args.tax_rate if args.tax_rate is not None else values["Tax Rate"],
            debt=args.debt if args.debt is not None else values["Debt"],
            equity=args.equity if args.equity is not None else values["Equity"],
            beta=beta,
            unlevered_beta=unlevered_beta,
            country_risk_premium=args.country_risk_premium if args.country_risk_premium is not None else values["Country Risk Premium"],
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    result.print_summary()


if __name__ == "__main__":
    main()
