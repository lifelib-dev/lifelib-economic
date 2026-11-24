"""Bootstrap: add the Validation space to the written BasicLMM model.

Reads BasicLMM/, adds a space Validation whose cells check the space LMM against closed
forms and martingale properties, and writes the model back. The LMM space is left as it
is on disk. The previous model folder is kept as BasicLMM_BAK1 until the new one has been
read back and run; it is then removed. An existing Validation space is replaced only if
--force is given::

    python scripts/add_validation_space_lmm.py [--force]

Each function below becomes a Cells of the space Validation. The module source in
MCSTATS_SOURCE is saved in the model folder as mcstats.py, and the cells use it through
the Reference ``mcstats``. Its functions are those of BasicG2PP's mcstats.py.
"""
import argparse
import os
import shutil
import stat
import tempfile
import time
from pathlib import Path

import modelx as mx
import numpy as np
import pandas as pd
import scipy.stats

LIBRARY = Path(__file__).resolve().parents[1] / "lifelib" / "libraries" / "economic"
TARGET = LIBRARY / "BasicLMM"
BACKUP = LIBRARY / "BasicLMM_BAK1"

MCSTATS_SOURCE = '''"""Monte Carlo summary statistics for the Validation space of BasicLMM.

:func:`check` turns simulated samples into a DataFrame of Monte Carlo estimates,
theoretical values, standard errors and z-scores. With antithetic variates, scenarios
k and k + N/2 form a pair, and the standard error comes from the N/2 pair means, which
are independent. Treating the N paths as independent would overstate it.
"""
import numpy as np
import pandas as pd


def mean_se(samples, antithetic):
    """Mean and standard error of samples over their first axis (scenarios)."""
    samples = np.asarray(samples, dtype=float)
    if antithetic:
        half = len(samples) // 2
        samples = 0.5 * (samples[:half] + samples[half:])
    return samples.mean(axis=0), samples.std(axis=0, ddof=1) / np.sqrt(len(samples))


def check(samples, theory, antithetic, index=None):
    """DataFrame with columns mc, theory, se and z of samples against theory.

    ``samples`` has one row per stochastic scenario, with shape (N,) or (N, k), and
    ``theory`` is a scalar or has shape (k,). z = (mc - theory) / se. Where se is below
    1e-12 of the value, the estimate is exact by construction (for example the deflators
    of the first tenor period, or the deflated value of an all-cash fund): z is then 0
    if mc matches theory to 1e-9, and infinite otherwise.
    """
    mc, se = mean_se(samples, antithetic)
    mc, se = np.atleast_1d(mc), np.atleast_1d(se)
    theory = np.array(np.broadcast_to(np.asarray(theory, dtype=float), mc.shape))
    tol = 1e-12 * np.maximum(1.0, np.abs(theory))
    diff = mc - theory
    z = np.where(np.abs(diff) <= 1e3 * tol, 0.0, np.copysign(np.inf, diff))
    np.divide(diff, se, out=z, where=se > tol)
    return pd.DataFrame({"mc": mc, "theory": theory, "se": se, "z": z}, index=index)
'''

SPACE_DOC = r"""Checks of the LMM space against closed forms and martingale properties.

Every test returns a DataFrame with the columns

* ``mc``: the Monte Carlo estimate over the stochastic scenarios 1 to N,
* ``theory``: the value it should converge to,
* ``se``: its standard error, from antithetic pair means when antithetic variates are on,
* ``z``: :math:`(\mathrm{mc} - \mathrm{theory}) / \mathrm{se}`.

With correct formulas, each z is roughly standard normal, so :math:`|z| > 3` is rare for a
single check. Tests that cover many months or rates contain many z-scores, so a larger
maximum is expected by chance: :func:`summary` compares the largest :math:`|z|` of each
test with a limit that allows for the number of z-scores. Where the estimate is exact by
construction, z is 0 (see ``mcstats.check``).

The martingale tests check the deflated bonds, and so the interpolation between tenor
dates. The caplet tests check the distribution of the forward rates, and with it the
monthly step. :func:`swaption_test` is a diagnostic: its formula is an approximation.

The tests read the scenarios through the Reference :attr:`lmm`, so they run on whatever
input the LMM space uses. Statistical power grows with ``scen_size``; 10,000 antithetic
scenarios is a good setting for validation.

Attributes:

    lmm: The LMM space.

    mcstats: User module with ``check()``, which turns samples into the DataFrame
        above. Saved in the model folder as ``mcstats.py``.

    np: The numpy module.

    pd: The pandas module.

    stats: The scipy.stats module, for the normal distribution.
"""


def martingale_test():
    r"""Mean deflator against the initial curve, for every month

    :math:`E[D(t_i)] = P^M(0, t_i)` for i = 0 to n. In the first tenor period the
    deflators are known at time 0, so z is 0 there.

    Returns:
        pandas.DataFrame indexed by month ``t``, columns ``mc``, ``theory``, ``se``, ``z``
    """
    paths = lmm.disc_factor_paths()
    return mcstats.check(paths[1:], paths[0], lmm.antithetic(),
                         pd.RangeIndex(paths.shape[1], name="t"))


def fund_martingale_test():
    r"""Deflated value of the selected fund against 1, for every month

    :math:`E[D(t_i) AV(t_i)/AV_0] = 1` with :math:`AV(t_i)/AV_0 = \prod_{k<i}(1 + R^F_k)`,
    because the fund trades only bonds and the bank account. For an all-cash fund this
    holds in every scenario, so z is 0.

    Returns:
        pandas.DataFrame indexed by month ``t``, columns ``mc``, ``theory``, ``se``, ``z``
    """
    returns = lmm.fund_return_paths()
    growth = np.cumprod(np.hstack([np.ones((len(returns), 1)), 1 + returns]), axis=1)
    values = lmm.disc_factor_paths() * growth
    return mcstats.check(values[1:], 1.0, lmm.antithetic(),
                         pd.RangeIndex(values.shape[1], name="t"))


def curve_fit_test():
    r"""Spot rates implied by the mean deflators against the input curve

    At each maturity of the selected curve that is a whole number of months no later
    than :math:`t_n`, the spot rate implied by the mean of :math:`D(t)` (compounded as
    the input) against the input spot rate. The standard error comes from that of
    :func:`martingale_test` by the delta method. Where the deflator is known at time 0,
    in the first tenor period, z is 0, as in ``mcstats.check``.

    Returns:
        pandas.DataFrame indexed by ``maturity`` in years, columns ``mc``, ``theory``,
        ``se``, ``z``
    """
    col = lmm.curve_table()[lmm.curve_id()].dropna()
    years = col.index.to_numpy(dtype=float)
    months = np.round(years * 12).astype(int)
    keep = (np.abs(years * 12 - months) < 1e-9) & (months <= lmm.step_size())
    years, months, spot = years[keep], months[keep], col.to_numpy(dtype=float)[keep]
    mart = martingale_test()
    mean, se_mean = mart["mc"].to_numpy()[months], mart["se"].to_numpy()[months]
    if lmm.compounding() == "annual":
        implied = mean ** (-1 / years) - 1
        slope = mean ** (-1 / years - 1) / years
    else:
        implied = -np.log(mean) / years
        slope = 1 / (mean * years)
    se = slope * se_mean
    tol = 1e-12 * np.maximum(1.0, np.abs(spot))
    diff = implied - spot
    z = np.where(np.abs(diff) <= 1e3 * tol, 0.0, np.copysign(np.inf, diff))
    np.divide(diff, se, out=z, where=se > tol)
    return pd.DataFrame({"mc": implied, "theory": spot, "se": se, "z": z},
                        index=pd.Index(years, name="maturity"))


def zcb_martingale_test(i, j):
    r"""Deflated bond prices: :math:`E[D(t_i) P(t_i, t_j)] = P^M(0, t_j)`

    Returns:
        pandas.DataFrame with one row indexed by (``i``, ``j``)
    """
    values = lmm.disc_factor(i) * lmm.P_t_T(i, j)
    return mcstats.check(values, lmm.mkt_zcb(j), lmm.antithetic(),
                         pd.MultiIndex.from_tuples([(i, j)], names=["i", "j"]))


def caplet_cf(k, x):
    r"""Closed-form price of the caplet on :math:`F_k` with strike x

    The caplet pays :math:`\tau(F_k(T_{k-1}) - x)^+` at :math:`T_k`. Under the forward
    measure of :math:`T_k`, :math:`F_k + \alpha` is lognormal with the Black volatility
    :math:`\sigma_k` of ``lmm.caplet_vol``, so Black's formula with the shifted rate and
    strike gives, with :math:`v = \sigma_k\sqrt{T_{k-1}}`:

    .. math::

        \mathrm{Cpl} = {} & \tau P^M(0, T_k)\left[(F_k(0) + \alpha)\Phi(d_1)
        - (x + \alpha)\Phi(d_1 - v)\right] \\
        d_1 = {} & \frac{1}{v}\ln\frac{F_k(0) + \alpha}{x + \alpha} + \frac{v}{2}

    A strike at or below :math:`-\alpha` is always exceeded, so the caplet is then worth
    :math:`\tau P^M(0, T_k)(F_k(0) - x)`.
    """
    p, alpha = lmm.tenor_mth(), lmm.shift()
    fwd, strike = lmm.mkt_fwd_rates()[k - 1] + alpha, x + alpha
    annuity = p / 12 * lmm.mkt_zcb(k * p)
    if strike <= 0:
        return float(annuity * (fwd - strike))
    v = lmm.caplet_vol(k) * np.sqrt(lmm.t_((k - 1) * p))
    d1 = np.log(fwd / strike) / v + v / 2
    return float(annuity * (fwd * stats.norm.cdf(d1) - strike * stats.norm.cdf(d1 - v)))


def caplet_mc(k, x):
    r"""Monte Carlo price of the caplet of :func:`caplet_cf`, against the closed form

    The mean of the deflated payoffs :math:`D(T_k)\,\tau(F_k(T_{k-1}) - x)^+`. Needs the
    expiry :math:`T_{k-1}` within the projection.

    Returns:
        pandas.DataFrame with one row indexed by (``k``, ``x``)
    """
    p = lmm.tenor_mth()
    fixing = lmm.fwd_rates((k - 1) * p)[:, 0]
    values = lmm.tenor_disc_factor(k) * (p / 12) * np.maximum(fixing - x, 0)
    return mcstats.check(values, caplet_cf(k, x), lmm.antithetic(),
                         pd.MultiIndex.from_tuples([(k, x)], names=["k", "x"]))


def caplet_test():
    r"""At-the-money caplets on the rates that expire at every whole year up to :math:`t_n`

    For each year y, the caplet on the rate :math:`F_k` set at :math:`T_{k-1} = y`, with the
    strike :math:`F_k(0)`, against :func:`caplet_cf`. If the run is shorter than a year,
    the rates set at every tenor date up to :math:`t_n`. Together the caplets check the
    distribution of the rates, and with it the monthly step.

    Returns:
        pandas.DataFrame indexed by (``k``, ``expiry`` in years), columns ``mc``,
        ``theory``, ``se``, ``z``
    """
    p, n = lmm.tenor_mth(), lmm.step_size()
    expiries = list(range(12, n + 1, 12)) or list(range(p, n + 1, p))
    if not expiries:
        raise ValueError("caplet_test needs at least one tenor: step_size >= tenor_mth")
    ks = [i // p + 1 for i in expiries]
    strikes = lmm.mkt_fwd_rates()[np.array(ks) - 1]
    samples = np.column_stack([
        lmm.tenor_disc_factor(k) * (p / 12) * np.maximum(lmm.fwd_rates(i)[:, 0] - x, 0)
        for k, i, x in zip(ks, expiries, strikes)])
    theory = [caplet_cf(k, x) for k, x in zip(ks, strikes)]
    index = pd.MultiIndex.from_arrays([ks, [i / 12 for i in expiries]], names=["k", "expiry"])
    return mcstats.check(samples, theory, lmm.antithetic(), index)


def fwd_swap(a, b):
    r"""Forward swap rate :math:`S(0)` and annuity :math:`A(0)` of the b-year swap starting in a years

    The swap has a yearly fixed leg, paid at the anniversaries :math:`T_l` from a + 1 to
    a + b years: :math:`A(0) = \sum_l P^M(0, T_l)` and
    :math:`S(0) = (P^M(0, a) - P^M(0, a + b)) / A(0)`.

    Returns:
        tuple of the forward swap rate and the annuity
    """
    zcb = [lmm.mkt_zcb(12 * y) for y in range(a, a + b + 1)]
    annuity = sum(zcb[1:])
    return (zcb[0] - zcb[-1]) / annuity, annuity


def swaption_vol(a, b):
    r"""Black volatility of the forward swap rate plus :math:`\alpha`, by Rebonato's formula

    For the swaption that expires in a years on the b-year swap of :func:`fwd_swap`, with
    the forward rates :math:`F_j` of the swap, j from :math:`a/\tau + 1` to
    :math:`(a + b)/\tau`, frozen at time 0 in the weights:

    .. math::

        \sigma_S^2 a = {} & \sum_{i=0}^{12a - 1} \frac{1}{12}
        \left|\sum_j z_j\lambda((j-1)p - i)\right|^2 \\
        z_j = {} & \frac{\partial S}{\partial F_j}\frac{F_j(0) + \alpha}{S(0) + \alpha}

    Brigo and Mercurio, section 6.15, with the shift and a fixed leg that pays less often
    than the tenor. It is an approximation; :func:`swaption_test` compares it with the
    Monte Carlo price.
    """
    p, alpha = lmm.tenor_mth(), lmm.shift()
    tau, per = p / 12, 12 // p
    zcb = np.array([lmm.mkt_zcb(k * p) for k in range((a + b) * per + 1)])
    fwd = lmm.mkt_fwd_rates()
    swap, annuity = fwd_swap(a, b)
    fixed = np.arange(a + 1, a + b + 1) * per          # tenor indexes of the fixed dates
    js = np.arange(a * per + 1, (a + b) * per + 1)     # the forward rates of the swap
    later = np.array([zcb[fixed[fixed >= j]].sum() for j in js])
    slope = tau / (1 + tau * fwd[js - 1]) * (zcb[-1] + swap * later) / annuity
    weight = slope * (fwd[js - 1] + alpha) / (swap + alpha)
    lam = lmm.vol_loadings()
    var = sum(np.sum((weight @ lam[(js - 1) * p - i]) ** 2) for i in range(12 * a)) / 12
    return float(np.sqrt(var / a))


def swaption_test(a, b):
    r"""At-the-money payer swaption, Monte Carlo against the price from :func:`swaption_vol`

    The deflated payoff at :math:`T_\alpha` = a years is

    .. math::

        \left(D(T_\alpha) - D(T_\alpha; T_\beta) - S(0)\sum_l D(T_\alpha; T_l)\right)^+

    and the approximate price :math:`A(0)(S(0) + \alpha)(2\Phi(v/2) - 1)`, Black's formula
    at the money with :math:`v = \sigma_S\sqrt{a}`. A diagnostic, not a test: the formula is
    an approximation, so its z-score need not be small.

    Returns:
        pandas.DataFrame with one row indexed by (``a``, ``b``)
    """
    swap, annuity = fwd_swap(a, b)
    i = 12 * a
    fixed_leg = sum(lmm.defl_zcb(i, 12 * (a + y)) for y in range(1, b + 1))
    values = np.maximum(lmm.disc_factor(i) - lmm.defl_zcb(i, 12 * (a + b)) - swap * fixed_leg, 0)
    v = swaption_vol(a, b) * np.sqrt(a)
    theory = annuity * (swap + lmm.shift()) * (2 * stats.norm.cdf(v / 2) - 1)
    return mcstats.check(values, theory, lmm.antithetic(),
                         pd.MultiIndex.from_tuples([(a, b)], names=["a", "b"]))


def summary():
    r"""Largest :math:`|z|` of each test on the current input, against its limit

    Runs every test, with the deflated bond at :math:`t_i`, i = n // 2, maturing
    ``maturity_size`` months later. :func:`swaption_test` is left out, because its formula
    is an approximation.

    A test with m z-scores passes if its largest :math:`|z|` is below
    :math:`\Phi^{-1}(1 - 0.00135/m)`. That keeps the chance of a false alarm at that of a
    single 3-sigma check, 0.27%, if the z-scores were independent; positively correlated
    ones, such as those of neighbouring months, make it smaller still. The limit is 3
    for a single check and about 4.5 for 600 months.

    Returns:
        pandas.DataFrame indexed by test, columns ``checks`` (number of z-scores),
        ``max_abs_z``, ``limit``, ``ok`` and ``at`` (the row of the largest :math:`|z|`)
    """
    i = max(1, lmm.step_size() // 2)
    j = i + lmm.maturity_size()
    tests = {
        "martingale_test()": martingale_test(),
        "fund_martingale_test()": fund_martingale_test(),
        "curve_fit_test()": curve_fit_test(),
        "caplet_test()": caplet_test(),
        f"zcb_martingale_test({i}, {j})": zcb_martingale_test(i, j),
    }
    rows = {}
    for name, df in tests.items():
        z = df["z"].abs()
        m = int(z.notna().sum())
        limit = float(stats.norm.isf(0.00135 / m))
        rows[name] = {"checks": m, "max_abs_z": z.max(), "limit": limit,
                      "ok": bool(z.max() < limit), "at": z.idxmax()}
    return pd.DataFrame.from_dict(rows, orient="index")


FORMULAS = [martingale_test, fund_martingale_test, curve_fit_test, zcb_martingale_test,
            caplet_cf, caplet_mc, caplet_test, fwd_swap, swaption_vol, swaption_test, summary]


def add_space(model, module_path):
    space = model.new_space("Validation")
    space.doc = SPACE_DOC
    for func in FORMULAS:
        space.new_cells(formula=func)
    space.lmm = model.LMM
    space.np = np
    space.pd = pd
    space.stats = scipy.stats
    space.new_module("mcstats", "mcstats.py", module_path)
    return space


def check(path):
    """Read the written model back and run the Validation summary on the default input."""
    model = mx.read_model(path)
    start = time.perf_counter()
    summary = model.Validation.summary()
    elapsed = time.perf_counter() - start
    print(summary.to_string())
    print(f"summary in {elapsed:.2f} s")
    model.close()


def remove_tree(path, attempts=5):
    """Remove a folder, clearing read-only flags and retrying while a sync client such as
    OneDrive still holds it. Warns instead of failing if it cannot."""
    def make_writable(func, name, exc):
        os.chmod(name, stat.S_IWRITE)
        func(name)
    for attempt in range(attempts):
        try:
            shutil.rmtree(path, onexc=make_writable)
            print(f"removed {path}")
            return
        except PermissionError:
            time.sleep(1)
    print(f"could not remove {path}; delete it by hand")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="replace an existing Validation space")
    args = parser.parse_args()
    if BACKUP.exists():
        raise SystemExit(f"{BACKUP} exists; move or delete it first")
    model = mx.read_model(TARGET)
    if "Validation" in model.spaces:
        if not args.force:
            model.close()
            raise SystemExit("BasicLMM already has a Validation space; pass --force to replace it")
        # deleting the space leaves the module's IOSpec registered under mcstats.py
        model.del_spec(model.Validation.mcstats)
        del model.Validation
    with tempfile.TemporaryDirectory() as tmp:
        module_path = Path(tmp) / "mcstats.py"
        module_path.write_text(MCSTATS_SOURCE, encoding="utf-8")
        add_space(model, module_path)
        mx.write_model(model, TARGET, backup=True)     # the old folder becomes BasicLMM_BAK1
    model.close()
    print(f"wrote {TARGET}")
    check(TARGET)
    remove_tree(BACKUP)


if __name__ == "__main__":
    main()
