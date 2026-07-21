"""
sample_assumptions.py -- Generates a sample CAPM assumptions sheet for
use as demo input to wacc_builder.py.

Debt and Equity below intentionally match the net debt and equity value
from the Parametrized-DCF demo (sample_company.xlsx), so the two tools
tell one consistent story end to end.

Usage:
    python sample_assumptions.py
"""

import pandas as pd

ASSUMPTIONS = {
    "Risk-Free Rate": 0.065,
    "Equity Risk Premium": 0.05,
    "Country Risk Premium": 0.02,
    "Unlevered Beta": 0.90,
    "Cost of Debt": 0.10,
    "Tax Rate": 0.34,
    "Debt": 1500.0,
    "Equity": 9085.0,
}


def build_sample() -> pd.DataFrame:
    df = pd.DataFrame.from_dict(ASSUMPTIONS, orient="index", columns=["Value"])
    df.index.name = "Parameter"
    return df


if __name__ == "__main__":
    df = build_sample()
    df.to_excel("sample_assumptions.xlsx")
    print("Generated sample_assumptions.xlsx\n")
    print(df.to_string())
