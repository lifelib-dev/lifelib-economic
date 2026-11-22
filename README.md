# lifelib-economic

A draft of lifelib's `economic` library, kept here until it is merged into lifelib. So far
it holds a G2++ interest rate scenario generator built as a modelx model, for calculating
the time value of options and guarantees (TVOG) of lifelib insurance liabilities. The
design is in the library's
[design note](lifelib/libraries/economic/_research/g2pp_design.md), made from
[PLAN.md](PLAN.md), and the plan for the merge in
[INTEGRATION_PLAN.md](INTEGRATION_PLAN.md).

**Status:** Phases 0–4 of the plan are done: the input workbook, a pure-numpy reference
implementation, the `BasicG2PP` model with its `G2PP` and `Validation` spaces, the
statistical tests, and the TVOG example `CashValue_ME_G2PP`, lifelib's
`savings/CashValue_ME_EX4` driven by the G2++ scenarios. Two notebooks show the
scenarios and the TVOG. Phase 5 brings all of this into lifelib, and its steps A to C
are done: the files now sit at `lifelib/libraries/economic/`, the library's path in
lifelib, next to a copy of lifelib's own library, and are adapted to it, with docstring
links to lifelib's docs, lifelib's Colab cell in the notebooks and two gallery scripts.
The docs pages of both models are drafted in MyST, and the design is kept in a note in
the library. All of this was merged into lifelib's `main` on 2026-11-22, in
[lifelib-dev/lifelib#188](https://github.com/lifelib-dev/lifelib/pull/188); the release
of lifelib v0.17.4 follows. Phase 6 lists optional extensions.

## Layout

The library lives where it will in lifelib: the models, the workbook, the notebooks and the
tests in `lifelib/libraries/economic/`, and the docs pages in
`doc/source/libraries/economic/`. Both folders started as a copy of lifelib's own
`economic` library at v0.17.3, in commit e292f34, so `git diff e292f34 -- lifelib doc`
shows what merging the draft will change in lifelib
([INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) §3).

In `lifelib/libraries/economic/`:

| Path | Contents |
|---|---|
| `g2pp_input.xlsx` | Excel input, read by both G2++ models at run time |
| `BasicG2PP/` | the modelx model: space `G2PP` (the scenarios) and space `Validation` (checks) |
| `CashValue_ME_G2PP/` | TVOG example: lifelib's `CashValue_ME_EX4` with a copy of `G2PP` as space `ESG` |
| `g2pp-simulation.ipynb` | fan charts, martingale check, yield distributions, bond fund, validation summary |
| `g2pp-tvog.ipynb` | model points, TVOG on the delivered input, GMAB TVOG by fund against the closed form |
| `plot_ex4_g2pp_rate_fan.py`, `plot_ex5_g2pp_martingale.py` | scripts for the gallery in lifelib's docs: fan charts of the short rate and the 10-year yield, and the martingale tests |
| `tests/` | the library's pytest suite, with `g2pp_registry.py` (paths and helpers) and `reference_g2pp.py`, a pure-numpy reference implementation |
| `_research/g2pp_design.md` | the design note: PLAN.md without the parts that concern only the drafting. Like delib's research notes, it stays out of lifelib's distributions |
| `BasicHullWhite/`, `hull-white-simulation.ipynb`, `plot_ex1_*.py` to `plot_ex3_*.py`, `README.txt` | lifelib's own library, unchanged |

In `doc/source/libraries/economic/`, the pages are MyST Markdown: `index.md`, the library's
page, and one page per model, `BasicHullWhite.md`, `BasicG2PP.md` and
`CashValue_ME_G2PP.md`. The `.nblink` files link the notebooks into the docs.

At the root, staying here:

| Path | Contents |
|---|---|
| `scripts/make_input.py` | creates `g2pp_input.xlsx` from lifelib's appliedlife curves (bootstrap only) |
| `scripts/build_model.py` | creates `BasicG2PP/` with the `G2PP` space through the modelx API (bootstrap only) |
| `scripts/add_validation_space.py` | adds the `Validation` space to the written model (bootstrap only) |
| `scripts/build_cashvalue_g2pp.py` | builds `CashValue_ME_G2PP/` from lifelib's EX4 and `G2PP` (bootstrap only) |
| `pytest.ini`, `.gitattributes` | lifelib's pytest options and line-ending rules, so the suite and the files behave as in lifelib |
| `PLAN.md`, `INTEGRATION_PLAN.md` | the plan the models were drafted from, whose design parts became the design note, and the plan for the merge |

After the first build, edit the model folders (directly or in Spyder-modelx) and
`g2pp_input.xlsx` themselves. The scripts are not kept in sync, and they refuse to
overwrite what they created unless given `--force`. To bootstrap from nothing, run
`make_input.py`, `build_model.py`, `add_validation_space.py` and
`build_cashvalue_g2pp.py` in that order. They write into the library folder. Run them as
files, as in `python scripts/make_input.py`: then `import lifelib` finds the installed
lifelib, whose files they only read, and not this repository's `lifelib/` folder.

Requirements: modelx, numpy, pandas, scipy, openpyxl and pytest. An installed lifelib is
needed only by `make_input.py` and `build_cashvalue_g2pp.py`, for their default sources.

## Use

From the library folder, `lifelib/libraries/economic/`:

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

From the repository root, where `pytest.ini` holds lifelib's pytest options:

```
python -m pytest                 # all 108 tests, about 24 s, peaking near 1 GB of memory
python -m pytest -m "not slow"   # without the 18 statistical tests, about 20 s
```

One test skips here: it compares the workbook's curves with appliedlife's source file,
which sits next to this library in lifelib but is not in this repository.

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

MIT, like lifelib; see [LICENSE](LICENSE). `BasicHullWhite` and the rest of the copy of
lifelib's library are lifelib's own files. `CashValue_ME_G2PP` is derived from lifelib's
`CashValue_ME_EX4`, and the example curves in `g2pp_input.xlsx` come from lifelib's
appliedlife data, whose stated source is EIOPA.
