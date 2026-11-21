# lifelib-economic

A draft of lifelib's `economic` library, kept here until it is merged into lifelib. So far
it holds a G2++ interest rate scenario generator built as a modelx model, for calculating
the time value of options and guarantees (TVOG) of lifelib insurance liabilities. The
design is in [PLAN.md](PLAN.md), and the plan for the merge in
[INTEGRATION_PLAN.md](INTEGRATION_PLAN.md).

**Status:** Phases 0–4 of the plan are done: the input workbook, a pure-numpy reference
implementation, the `BasicG2PP` model with its `G2PP` and `Validation` spaces, the
statistical tests, and the TVOG example `CashValue_ME_G2PP`, lifelib's
`savings/CashValue_ME_EX4` driven by the G2++ scenarios. Two notebooks show the
scenarios and the TVOG. Phase 5 moves the contents to `lifelib/libraries/economic/`, the
library's path in lifelib, next to a copy of lifelib's own library, and then into lifelib.
Phase 6 lists optional extensions.

## Layout

| Path | Contents |
|---|---|
| `g2pp_input.xlsx` | Excel input, read by the model at run time |
| `BasicG2PP/` | the modelx model: space `G2PP` (the scenarios) and space `Validation` (checks) |
| `CashValue_ME_G2PP/` | TVOG example: lifelib's `CashValue_ME_EX4` with a copy of `G2PP` as space `ESG` |
| `notebooks/g2pp_scenarios.ipynb` | fan charts, martingale check, yield distributions, bond fund, validation summary |
| `notebooks/tvog_example.ipynb` | model points, TVOG on the delivered input, GMAB TVOG by fund against the closed form |
| `scripts/make_input.py` | creates `g2pp_input.xlsx` from lifelib's appliedlife curves (bootstrap only) |
| `scripts/build_model.py` | creates `BasicG2PP/` with the `G2PP` space through the modelx API (bootstrap only) |
| `scripts/add_validation_space.py` | adds the `Validation` space to the written model (bootstrap only) |
| `scripts/build_cashvalue_g2pp.py` | builds `CashValue_ME_G2PP/` from lifelib's EX4 and `G2PP` (bootstrap only) |
| `tests/` | pytest suite, and `reference_g2pp.py`, a pure-numpy reference implementation |

After the first build, edit the model folders (directly or in Spyder-modelx) and
`g2pp_input.xlsx` themselves. The scripts are not kept in sync, and they refuse to
overwrite what they created unless given `--force`. To bootstrap from nothing, run
`make_input.py`, `build_model.py`, `add_validation_space.py` and
`build_cashvalue_g2pp.py` in that order. lifelib's own files are only read.

Requirements: modelx, numpy, pandas, scipy, openpyxl and pytest. lifelib is needed by
`make_input.py` to find the source curves, and by two tests, which are skipped without it.

## Use

```python
import modelx as mx

model = mx.read_model("BasicG2PP")
g2pp = model.G2PP

g2pp.disc_factor_paths()   # deflators D(t_i), shape (N+1, n+1)
g2pp.fund_return_paths()   # bond-fund returns over each month, shape (N+1, n)
g2pp.scenario_table()      # deflators, returns and short rates in long format

model.Validation.summary() # largest |z| of each check against its limit
```

The TVOG example reads the same workbook through its `ESG` space:

```python
cv = mx.read_model("CashValue_ME_G2PP")
proj = cv.Projection

proj.result_tvog()               # CE value, mean, TVOG and SE by model point
proj.formula_gmab_g2pp(120)      # closed-form GMAB cost, for an all-cash or single-maturity fund

cv.ESG.fund_id[()] = "CASH"      # try another fund without editing the workbook
proj.result_tvog()
cv.ESG.fund_id.clear_all()       # back to the workbook's fund
```

Row 0 of every `*_paths` array is the certainty-equivalent scenario, which follows the
initial forward curve. Row k is stochastic scenario k, and column i is month i. So when
you average over the stochastic scenarios yourself, use rows 1 to N.

The model reads `g2pp_input.xlsx` from the folder that contains `BasicG2PP/`. To use
another workbook, assign its file name or absolute path to `g2pp.input_file`. After
editing a workbook in place, call `model.clear_all()`, because the model caches what it
has read.

## Input workbook

- `Params`: the G2++ parameters `a`, `b`, `sigma`, `eta` and `rho`, and the run settings
  `scen_size`, `step_size` (months), `seed`, `antithetic`, `curve_id`, `compounding` and
  `fund_id`. The example G2++ parameters are illustrative only.
- `Curve`: spot rates by maturity in years, one column per curve. The example holds EUR,
  GBP, JPY and USD curves (BASE, UP and DOWN) out to 150 years, from lifelib's
  `appliedlife/economic_data/risk_free_202312.xlsx` (source: EIOPA). Curves are not
  extrapolated, so the selected curve must reach `step_size`/12 years, plus the tenor of
  any yield you ask for.
- `Fund`: each fund's shares by years to maturity of zero-coupon bonds, or `cash` for the
  bank account. Each month a fund sells its bonds and buys new ones at the same
  maturities.

## Tests

```
python -m pytest              # 89 tests, about 20 s
python -m pytest --runslow    # also the 18 statistical tests, peaking near 1 GB of memory
```

The tests check the numpy reference against numerical integration and martingale
properties, and then the model against the reference to a relative 1e-12. They also cover
input validation, a cross-check with lifelib's BasicHullWhite when η = 0, read-write-read
round trips and the Validation space. For `CashValue_ME_G2PP`, they check the GMAB cost
in every scenario against the payoff recomputed from the ESG paths, and the Monte Carlo
mean against the closed form.

The statistical tests run the Validation checks with 10,000 scenarios over 50 years and
2,000 over 150 years. A check with m z-scores passes if its largest |z| is below
Φ⁻¹(1 − 0.00135/m), the same chance of a false alarm as one 3-sigma check.

## License

MIT, like lifelib; see [LICENSE](LICENSE). `CashValue_ME_G2PP` is derived from lifelib's
`CashValue_ME_EX4`, and the example curves in `g2pp_input.xlsx` come from lifelib's
appliedlife data, whose stated source is EIOPA.
