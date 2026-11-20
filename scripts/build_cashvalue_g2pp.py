"""Bootstrap: build CashValue_ME_G2PP, lifelib's CashValue_ME_EX4 driven by G2++ scenarios.

Reads savings/CashValue_ME_EX4 from the installed lifelib (which is only read), copies the
G2PP space of BasicG2PP into it as the space ESG, and changes the space Projection so that
fund returns and discount factors come from ESG:

* scen_index() is ESG's: scenario 0 is the certainty-equivalent (CE) scenario,
* inv_return_table() tiles ESG's fund returns over the model points,
* disc_factors(t) tiles ESG's deflators over the model points,
* new result_tvog() and formula_gmab_g2pp(t),
* EX4's own economic inputs are dropped: scen_size, scen_id, std_norm_rand,
  disc_rate_ann, disc_rate_mth and formula_option_put.

The model is written to CashValue_ME_G2PP/ next to BasicG2PP/, so ESG reads the same
g2pp_input.xlsx. After the first build the written model is the source of truth; this
script refuses to replace it unless --force is given::

    python scripts/build_cashvalue_g2pp.py [--source PATH] [--force]
"""
import argparse
import os
import re
import shutil
import stat
import time
from pathlib import Path

import modelx as mx

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "CashValue_ME_G2PP"
DROP_CELLS = ["std_norm_rand", "disc_rate_mth", "formula_option_put"]
DROP_REFS = ["scen_size", "scen_id", "disc_rate_ann"]

MODEL_DOC = """lifelib's savings model CashValue_ME_EX4, driven by G2++ interest rate scenarios.

The space ESG is a copy of the G2PP space of BasicG2PP. It reads ``g2pp_input.xlsx``
next to the model folder and supplies the deflators and the fund returns of every
scenario. Scenario 0 is the certainty-equivalent (CE) scenario, so one run gives both
terms of TVOG = mean of the stochastic present values - the CE present value. See
:func:`~CashValue_ME_G2PP.Projection.result_tvog`.
"""

PROJECTION_INTRO = """The main Space of CashValue_ME_G2PP: CashValue_ME_EX4 driven by G2++ scenarios.

This space is lifelib's CashValue_ME_EX4 Projection space with its economic inputs taken
from the space ESG, a copy of BasicG2PP's G2PP space:

* :func:`scen_index` is ESG's: scen_id 0 is the certainty-equivalent (CE) scenario and
  1 to N are stochastic, so :func:`model_point` repeats every model point N+1 times.
* :func:`inv_return_table` is the market-value return of the bond fund chosen by
  ``fund_id`` in the ESG input, instead of EX4's lognormal returns.
* :func:`disc_factors` are ESG's deflators, instead of EX4's flat discount rate.
* :func:`result_tvog` gives the TVOG of the GMAB, the GMDB and the net cash flow, and
  :func:`formula_gmab_g2pp` the closed-form GMAB cost it can be checked against.
* :func:`check_pv_net_cf` discounts month by month; EX4's version calls
  ``disc_factors()`` without ``t`` and fails. :func:`check_margin` is unchanged and
  returns ``False`` here as in EX4, because the margins leave out the GMAB claims.

EX4's ``scen_size``, ``scen_id``, ``std_norm_rand``, ``disc_rate_ann``, ``disc_rate_mth``
and ``formula_option_put`` are removed. The rest of the original description follows.

"""

ESG_ATTRIBUTE = """    esg: The ESG space, a copy of BasicG2PP's G2PP space. It reads ``g2pp_input.xlsx``
        next to the model folder and supplies :func:`scen_index`, the fund returns of
        :func:`inv_return_table` and the deflators of :func:`disc_factors`.

"""


# ---------------------------------------------------------------------------
# New and changed formulas of Projection

def scen_index():
    """Scenario IDs from the ESG space: 0 is the CE scenario, 1 to N are stochastic

    :func:`model_point` repeats every model point for each of these scenarios.

    Returns:
        pandas.RangeIndex named ``scen_id``
    """
    return esg.scen_index()


def inv_return_table():
    """Monthly investment returns by model point and scenario, from the ESG space

    The fund earns the market-value return of the bond fund chosen by ``fund_id`` in the
    ESG input (``esg.fund_return_paths()``), with row 0 the CE scenario, which earns the
    one-month forwards of the initial curve. The array is tiled over model points in the
    row order of :func:`model_point`. Raises ``ValueError`` if the projection is longer
    than the ESG scenarios.

    Returns:
        numpy array of shape (point_size() * (N+1), n)
    """
    if max_proj_len() > esg.step_size():
        raise ValueError(
            f"the projection needs {max_proj_len()} months but the ESG scenarios have "
            f"{esg.step_size()}; raise step_size in the ESG input")
    return np.tile(esg.fund_return_paths(), (point_size(), 1))


def disc_factors(t):
    """Discount factors for cash flows at t, by model point and scenario: the ESG deflators

    Column ``t`` of ``esg.disc_factor_paths()``, tiled over model points in the row order
    of :func:`model_point`. The CE scenario discounts with the initial curve.

    Returns:
        numpy array of shape (point_size() * (N+1),)
    """
    return np.tile(esg.disc_factor_paths()[:, t], point_size())


def check_pv_net_cf():
    """Check present value summation

    Check if the present value of :func:`net_cf` matches the sum of the present values
    of each cash flow, :func:`pv_net_cf`. Returns the check result as :obj:`True` or
    :obj:`False`.

    Changed from CashValue_ME_EX4, whose version calls ``disc_factors()`` without ``t``
    and fails; this one discounts each month with ``disc_factors(t)``.
    """
    pvs = sum(net_cf(t) * disc_factors(t) for t in range(max_proj_len()))
    return np.all(np.isclose(pvs, pv_net_cf()))


def result_tvog():
    """Time value of options and guarantees (TVOG) by model point

    For the GMAB cost (``pv_claims_over_av("MATURITY")``), the GMDB cost
    (``pv_claims_over_av("DEATH")``) and the present value of net cash flows
    (:func:`pv_net_cf`):

    * ``CE``: the present value in the CE scenario (scen_id 0),
    * ``mean``: the mean over the stochastic scenarios 1 to N,
    * ``TVOG``: ``mean`` - ``CE``,
    * ``SE``: the standard error of ``mean``, from antithetic pair means when the ESG
      uses antithetic variates.

    Returns:
        pandas.DataFrame indexed by ``point_id``, with columns (measure, statistic)
    """
    n_scen = len(esg.scen_index())
    half = (n_scen - 1) // 2
    measures = {"GMAB": pv_claims_over_av("MATURITY"), "GMDB": pv_claims_over_av("DEATH"),
                "net cash flow": pv_net_cf()}
    frames = {}
    for name, pv in measures.items():
        table = np.asarray(pv, dtype=float).reshape(point_size(), n_scen)
        ce, stochastic = table[:, 0], table[:, 1:]
        if esg.antithetic():
            independent = 0.5 * (stochastic[:, :half] + stochastic[:, half:])
        else:
            independent = stochastic
        se = independent.std(axis=1, ddof=1) / np.sqrt(independent.shape[1])
        mean = stochastic.mean(axis=1)
        frames[name] = pd.DataFrame({"CE": ce, "mean": mean, "TVOG": mean - ce, "SE": se},
                                    index=model_point_table_ext().index)
    return pd.concat(frames, axis=1)


def formula_gmab_g2pp(t):
    r"""Closed-form GMAB cost of the single-premium model points maturing at month t

    For a single-premium policy with no fees or decrements, whose fund is all cash or
    holds zero-coupon bonds of a single maturity, :math:`\ln D(T)` and the log of the
    deflated account value are jointly Gaussian, and the exchange-option formula gives

    .. math::

        PV = SA\,P^M(0, T)\,\Phi(d_1) - AV_0\,\Phi(d_1 - s), \quad
        d_1 = \frac{\ln(SA\,P^M(0, T)/AV_0) + s^2/2}{s}

    where SA is the sum assured of the policies maturing at :math:`T = t/12`,
    :math:`AV_0` their account value after the premium at time 0 (``av_at(0,
    "BEF_FEE")``) and :math:`s^2` the variance of :math:`\ln(AV(T)/AV_0)`,
    ``esg.fund_logvar(t)``. For an all-cash fund this is EX1's Black-Scholes put
    (``formula_option_put``) with :math:`e^{-rT}` replaced by :math:`P^M(0, T)` and
    :math:`\sigma^2 T` by :math:`V(0, T)`. ``esg.fund_logvar`` raises ``ValueError`` for
    a fund with several maturities, which has no exact closed form.

    Returns:
        pandas.Series indexed by ``point_id`` of the single-premium points maturing at t
    """
    mps = model_point_table_ext()
    n_scen = len(esg.scen_index())
    keep = ((mps["policy_term"] * 12 - mps["duration_mth"] == t)
            & (mps["premium_type"] == "SINGLE")).to_numpy()
    sa = (sum_assured() * pols_maturity(t))[::n_scen][keep]
    av0 = av_at(0, "BEF_FEE")[::n_scen][keep]
    p = esg.mkt_zcb(t)
    s = np.sqrt(esg.fund_logvar(t))
    d1 = (np.log(sa * p / av0) + s**2 / 2) / s
    pv = sa * p * stats.norm.cdf(d1) - av0 * stats.norm.cdf(d1 - s)
    return pd.Series(pv, index=mps.index[keep], name="GMAB")


CHANGED = [scen_index, inv_return_table, disc_factors, check_pv_net_cf]
NEW = [result_tvog, formula_gmab_g2pp]


def projection_doc(doc):
    """EX4's Projection docstring with the dropped attributes removed and esg added."""
    for name in DROP_REFS + DROP_CELLS:
        doc = re.sub(rf"\n    {name}:.*?(?=\n    [A-Za-z_]+: |\n\S)", "", doc, flags=re.S)
    doc = doc.replace("Attributes:\n\n", "Attributes:\n\n" + ESG_ATTRIBUTE, 1)
    return PROJECTION_INTRO + doc


def build(source):
    model = mx.read_model(source, name="CashValue_ME_G2PP")
    g2pp_model = mx.read_model(ROOT / "BasicG2PP", name="BasicG2PP_source")
    esg = g2pp_model.G2PP.copy(model, "ESG")
    esg.t_.doc = g2pp_model.G2PP.t_.doc or "Time t_i = i/12 in years of month i"
    g2pp_model.close()

    proj = model.Projection
    proj.esg = esg
    for func in CHANGED:
        proj.cells[func.__name__].formula = func
    for func in NEW:
        proj.new_cells(formula=func)
    model.del_spec(proj.disc_rate_ann)        # the data file goes with the reference
    for name in DROP_CELLS + DROP_REFS:
        delattr(proj, name)
    proj.doc = projection_doc(proj.doc)
    model.doc = MODEL_DOC
    return model


def remove_tree(path, attempts=5):
    """Remove a folder, clearing read-only flags and retrying while OneDrive holds it."""
    def make_writable(func, name, exc):
        os.chmod(name, stat.S_IWRITE)
        func(name)
    for _ in range(attempts):
        try:
            shutil.rmtree(path, onexc=make_writable)
            return
        except PermissionError:
            time.sleep(1)
    raise SystemExit(f"could not remove {path}; delete it by hand")


def check(path):
    """Read the written model back and run the TVOG results on the default input."""
    model = mx.read_model(path)
    proj = model.Projection
    start = time.perf_counter()
    tvog = proj.result_tvog()
    elapsed = time.perf_counter() - start
    print(tvog["GMAB"].round(0).to_string())
    print(f"result_tvog() in {elapsed:.1f} s; checks: av roll-forward "
          f"{proj.check_av_roll_fwd()}, pv_net_cf {proj.check_pv_net_cf()}")
    model.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=None,
                        help="CashValue_ME_EX4 folder (default: from the installed lifelib)")
    parser.add_argument("--force", action="store_true", help="replace an existing model")
    args = parser.parse_args()
    if TARGET.exists():
        if not args.force:
            raise SystemExit(f"{TARGET} exists: edit it directly, or pass --force to rebuild it")
        remove_tree(TARGET)
    if args.source is None:
        import lifelib
        args.source = Path(lifelib.__file__).parent / "libraries" / "savings" / "CashValue_ME_EX4"
    model = build(args.source)
    mx.write_model(model, TARGET, backup=False)
    model.close()
    print(f"wrote {TARGET}")
    check(TARGET)


if __name__ == "__main__":
    main()
