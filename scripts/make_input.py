"""Create ``g2pp_input.xlsx``, the Excel input of BasicG2PP, with example values.

The curves are copied from lifelib's
``appliedlife/economic_data/risk_free_202312.xlsx`` (sheets BASE, UP and DOWN; source
stated in that file: EIOPA, https://eiopa.europa.eu/). In that file row k is the
maturity k+1 years, so the maturities are converted explicitly.

Run it once to create the workbook. After that the workbook is the input to edit, and
this script refuses to overwrite it unless ``--force`` is given::

    python scripts/make_input.py [--source PATH] [--force]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "g2pp_input.xlsx"

PARAMS = [
    ("a", 0.773, "mean reversion of x, > 0"),
    ("b", 0.082, "mean reversion of y, > 0"),
    ("sigma", 0.022, "volatility of x, > 0"),
    ("eta", 0.0104, "volatility of y, >= 0"),
    ("rho", -0.7, "correlation of W1 and W2, in [-1, 1]"),
    ("scen_size", 1000, "number of stochastic scenarios N, even when antithetic"),
    ("step_size", 600, "number of monthly steps n: at least the liability max_proj_len(), "
                       "and n/12 no later than the curve's last maturity"),
    ("seed", 1234, "random seed"),
    ("antithetic", True, "antithetic variates"),
    ("curve_id", "EUR_BASE", "column of the Curve sheet to use"),
    ("compounding", "annual", "compounding of the input spot rates: annual or continuous"),
    ("fund_id", "BOND_MIX", "column of the Fund sheet to use"),
]

FUNDS = pd.DataFrame({
    "maturity": ["cash", 5, 10],
    "CASH": [1.0, np.nan, np.nan],
    "BOND_MIX": [0.2, 0.3, 0.5],
    "BOND_10Y": [np.nan, np.nan, 1.0],
})

NOTES = [
    "Input to the BasicG2PP model (G2++ interest rate scenario generator). The model reads "
    "this file at run time. After editing it in place, call model.clear_all().",
    "Params: G2++ parameters and run settings. The example G2++ parameters are illustrative "
    "only; replace them with calibrated values.",
    "Curve: spot rates by maturity in years, one column per curve ID, compounded as set by "
    "the compounding parameter. A curve ends at its last non-blank row. The curve is not "
    "extrapolated: it must reach the projection horizon (step_size/12 years), and yields "
    "need the horizon plus their tenor.",
    "Curve source: lifelib appliedlife/economic_data/risk_free_202312.xlsx, sheets BASE, UP "
    "and DOWN, whose stated source is EIOPA - European Insurance and Occupational Pensions "
    "Authority, https://eiopa.europa.eu/",
    "Fund: shares of each fund by years to maturity of zero-coupon bonds (a whole number of "
    "months), or cash for the bank account. Each month the fund sells its bonds and buys new "
    "ones at the same maturities. Blank shares are 0, and each fund's shares sum to 1.",
]


def default_source():
    import lifelib
    return (Path(lifelib.__file__).parent / "libraries" / "appliedlife" / "economic_data"
            / "risk_free_202312.xlsx")


def curve_sheet(source):
    sheets = pd.read_excel(source, sheet_name=["BASE", "UP", "DOWN"], index_col=0)
    base = sheets["BASE"]
    for name, df in sheets.items():
        if not (df.index.equals(base.index) and df.columns.equals(base.columns)):
            raise ValueError(f"sheet {name} of {source} is not laid out like BASE")
    if not np.array_equal(base.index.to_numpy(), np.arange(len(base))):
        raise ValueError(f"expected rows 0, 1, 2, ... in {source}")
    data = {"maturity": base.index.to_numpy() + 1}      # row k is maturity k+1
    for ccy in base.columns:
        for scen in ("BASE", "UP", "DOWN"):
            data[f"{ccy}_{scen}"] = sheets[scen][ccy].to_numpy(dtype=float)
    return pd.DataFrame(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=None,
                        help="risk_free_202312.xlsx (default: from the installed lifelib)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing workbook")
    args = parser.parse_args()

    if TARGET.exists() and not args.force:
        raise SystemExit(f"{TARGET} exists; edit it directly or pass --force to recreate it")
    source = args.source or default_source()

    sheets = {
        "Params": pd.DataFrame(PARAMS, columns=["parameter", "value", "description"]),
        "Curve": curve_sheet(source),
        "Fund": FUNDS,
        "Notes": pd.DataFrame({"note": NOTES}),
    }
    widths = {"Params": {"A": 14, "B": 12, "C": 90}, "Notes": {"A": 120}}
    with pd.ExcelWriter(TARGET, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            for col, width in widths.get(name, {}).items():
                writer.sheets[name].column_dimensions[col].width = width
    print(f"wrote {TARGET}")


if __name__ == "__main__":
    main()
