"""Create ``lmm_input.xlsx``, the Excel input of BasicLMM, with example values.

The ``Curve`` and ``Fund`` sheets are copied from ``g2pp_input.xlsx``, the input of
BasicG2PP, so that the two generators run on the same curves and funds. Those curves come
from lifelib's ``appliedlife/economic_data/risk_free_202312.xlsx``, whose stated source is
EIOPA. The ``Vol`` sheet is the example volatility table of section 5 of LMM_PLAN.md, and
of the design note made from it, ``_research/lmm_design.md``: two exponential factors with
correlation -0.7, written as two independent ones and rounded to six decimals.

Run it once to create the workbook. After that the workbook is the input to edit, and
this script refuses to overwrite it unless ``--force`` is given::

    python scripts/make_input_lmm.py [--source PATH] [--force]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

LIBRARY = Path(__file__).resolve().parents[1] / "lifelib" / "libraries" / "economic"
TARGET = LIBRARY / "lmm_input.xlsx"
SOURCE = LIBRARY / "g2pp_input.xlsx"

PARAMS = [
    ("shift", 0.02, "shift of the forward rates, as a rate: rates stay above -shift. At "
                    "least 0 and below 12/tenor_mth; 0 gives the lognormal LMM"),
    ("tenor_mth", 12, "tenor of the forward rates in months: 1, 2, 3, 4, 6 or 12"),
    ("maturity_size", 120, "number of monthly bond maturities carried at every month: at "
                           "least tenor_mth, the longest maturity of the fund and the "
                           "longest tenor of any yield used"),
    ("scen_size", 1000, "number of stochastic scenarios N, even when antithetic"),
    ("step_size", 600, "number of monthly steps n: at least the liability max_proj_len(). "
                       "The curve must reach the first tenor date at or after "
                       "step_size + maturity_size months"),
    ("seed", 1234, "random seed"),
    ("antithetic", True, "antithetic variates"),
    ("curve_id", "EUR_BASE", "column of the Curve sheet to use"),
    ("compounding", "annual", "compounding of the input spot rates: annual or continuous"),
    ("fund_id", "BOND_MIX", "column of the Fund sheet to use"),
]

# The example volatility table: two exponential factors with correlation RHO, written as
# two independent ones. At time to expiry u in years,
#     f1(u) = S1 exp(-K1 u) + RHO S2 exp(-K2 u),    f2(u) = sqrt(1 - RHO^2) S2 exp(-K2 u)
S1, K1, S2, K2, RHO = 0.30, 0.8, 0.20, 0.08, -0.7
VOL_GRID = [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30, 40,
            50, 75, 100, 150]

NOTES = [
    "Input to BasicLMM, the LIBOR market model (LMM) interest rate scenario generator, and "
    "to the ESG space of CashValue_ME_LMM, a copy of BasicLMM's LMM space. Both models read "
    "this file at run time. After editing it in place, call clear_all() on each model that "
    "has read it.",
    "Params: the shift and the tenor of the forward rates, the bond maturities to carry, and "
    "the run settings. The example shift is illustrative only; replace it with a calibrated "
    "value.",
    "Curve: spot rates by maturity in years, one column per curve ID, compounded as set by "
    "the compounding parameter. A curve ends at its last non-blank row. The curve is not "
    "extrapolated: it must reach the first tenor date at or after step_size + maturity_size "
    "months.",
    "Curve and Fund: the same sheets as in g2pp_input.xlsx, the input of BasicG2PP. Curve "
    "source: lifelib appliedlife/economic_data/risk_free_202312.xlsx, sheets BASE, UP and "
    "DOWN, whose stated source is EIOPA - European Insurance and Occupational Pensions "
    "Authority, https://eiopa.europa.eu/",
    "Vol: the volatility of the forward rates by time to expiry in years (maturity), one "
    "column per factor (f1, f2, ...). A row is the volatility vector of a forward rate with "
    "that time to expiry: its length is the rate's volatility, and the angle between two "
    "rows gives the correlation of two rates. Values are linear between rows and flat before "
    "the first row. The table is not extrapolated: it must reach the expiry of the last "
    "forward rate of a run, one tenor before the date that the curve must reach.",
    "Vol, example: two exponential factors with correlation -0.7, written as two independent "
    "ones and rounded to six decimals: f1(u) = 0.30 exp(-0.8u) - 0.14 exp(-0.08u) and "
    "f2(u) = 0.20 sqrt(0.51) exp(-0.08u). The volatility falls from 21% at expiry to 9% at "
    "10 years and 2% at 30 years. Like the shift, it is illustrative only; replace it with a "
    "calibrated table.",
    "Vol, warning: volatility must fall with time to expiry. If it stays at 10% for long "
    "expiries, rates explode over long horizons: with a 2% shift, the 99th percentile of the "
    "1-year rate at 50 years is about 350%.",
    "Vol, warning: a table is calibrated for one tenor. With the same table, a shorter "
    "tenor_mth gives a more volatile bank account, and so higher values of options and "
    "guarantees.",
    "Fund: shares of each fund by years to maturity of zero-coupon bonds (a whole number of "
    "months), or cash for the bank account. Each month the fund sells its bonds and buys new "
    "ones at the same maturities. Blank shares are 0, and each fund's shares sum to 1. The "
    "longest maturity must not exceed maturity_size months.",
]


def vol_sheet():
    """The example volatility table, rounded to six decimals."""
    u = np.array(VOL_GRID, dtype=float)
    f1 = S1 * np.exp(-K1 * u) + RHO * S2 * np.exp(-K2 * u)
    f2 = np.sqrt(1 - RHO**2) * S2 * np.exp(-K2 * u)
    return pd.DataFrame({"maturity": u,
                         "f1": [round(float(v), 6) for v in f1],
                         "f2": [round(float(v), 6) for v in f2]})


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="workbook whose Curve and Fund sheets are copied "
                             "(default: g2pp_input.xlsx in the library folder)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing workbook")
    args = parser.parse_args()

    if TARGET.exists() and not args.force:
        raise SystemExit(f"{TARGET} exists; edit it directly or pass --force to recreate it")
    copied = pd.read_excel(args.source, sheet_name=["Curve", "Fund"])

    sheets = {
        "Params": pd.DataFrame(PARAMS, columns=["parameter", "value", "description"]),
        "Curve": copied["Curve"],
        "Vol": vol_sheet(),
        "Fund": copied["Fund"],
        "Notes": pd.DataFrame({"note": NOTES}),
    }
    widths = {"Params": {"A": 15, "B": 12, "C": 100}, "Notes": {"A": 120}}
    with pd.ExcelWriter(TARGET, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            for col, width in widths.get(name, {}).items():
                writer.sheets[name].column_dimensions[col].width = width
    print(f"wrote {TARGET}")


if __name__ == "__main__":
    main()
