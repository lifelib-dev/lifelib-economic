"""Bootstrap: build CashValue_ME_LMM, the TVOG example of BasicLMM.

Reads CashValue_ME_G2PP from the library folder, which is only read, replaces its space
ESG with a copy of the LMM space of BasicLMM, and changes the space Projection:

* formula_gmab_g2pp goes: under the LMM a maturity guarantee on a fund has no closed form.
* formula_gmab_floorlet(t) is new: the closed form for single-premium policies that
  mature at the second tenor date with an all-cash fund, whose guarantee is a floorlet.
* the docstrings of the model and of Projection name the LMM.

scen_index, inv_return_table, disc_factors, check_pv_net_cf and result_tvog use only the
outputs that BasicG2PP and BasicLMM share, and are left as they are.

The model is written to CashValue_ME_LMM/ next to BasicLMM/, so ESG reads lmm_input.xlsx.
After the first build the written model is the source of truth; this script refuses to
replace it unless --force is given::

    python scripts/build_cashvalue_lmm.py [--force]
"""
import argparse
import os
import shutil
import stat
import time
from pathlib import Path

import modelx as mx

LIBRARY = Path(__file__).resolve().parents[1] / "lifelib" / "libraries" / "economic"
SOURCE = LIBRARY / "CashValue_ME_G2PP"
TARGET = LIBRARY / "CashValue_ME_LMM"

MODEL_DOC = """lifelib's savings model CashValue_ME_EX4, driven by LMM interest rate scenarios.

The space ESG is a copy of the :mod:`~economic.BasicLMM.LMM` space of BasicLMM. It reads
``lmm_input.xlsx`` next to the model folder and supplies the deflators and the fund
returns of every scenario. Scenario 0 is the certainty-equivalent (CE) scenario, so one
run gives both terms of TVOG = mean of the stochastic present values - the CE present
value. See ``Projection.result_tvog``, and the notebook ``lmm-tvog.ipynb``, which
describes this example model. Apart from its ESG and its closed form, the model is
CashValue_ME_G2PP.
"""

G2PP_INTRO = """The main Space of CashValue_ME_G2PP: CashValue_ME_EX4 driven by G2++ scenarios.

This space is lifelib's CashValue_ME_EX4 Projection space with its economic inputs taken
from the space ESG, a copy of the :mod:`~economic.BasicG2PP.G2PP` space of BasicG2PP:
"""

LMM_INTRO = """The main Space of CashValue_ME_LMM: CashValue_ME_EX4 driven by LMM scenarios.

This space is lifelib's CashValue_ME_EX4 Projection space with its economic inputs taken
from the space ESG, a copy of the :mod:`~economic.BasicLMM.LMM` space of BasicLMM. It is
the Projection space of CashValue_ME_G2PP, apart from the closed form:
"""

G2PP_FORMULA_ITEM = """  :func:`formula_gmab_g2pp` the closed-form GMAB cost it can be checked against.
"""

LMM_FORMULA_ITEM = """  :func:`formula_gmab_floorlet` the closed-form GMAB cost of policies that mature at the
  second tenor date, which it can be checked against.
"""

G2PP_ESG_ATTRIBUTE = """    esg: The ESG space, a copy of the :mod:`~economic.BasicG2PP.G2PP` space of
        BasicG2PP. It reads ``g2pp_input.xlsx`` next to the model folder and supplies
"""

LMM_ESG_ATTRIBUTE = """    esg: The ESG space, a copy of the :mod:`~economic.BasicLMM.LMM` space of
        BasicLMM. It reads ``lmm_input.xlsx`` next to the model folder and supplies
"""


def formula_gmab_floorlet(t):
    r"""Closed-form GMAB cost of the single-premium model points maturing at month t

    For a single-premium policy with no fees or decrements whose fund is all cash, the
    account value grows with the bank account. If the policy matures at the second tenor
    date :math:`T_2`, month 2p, its account value at maturity is
    :math:`AV_0(1 + \tau F_1(0))(1 + \tau F_2(T_1))`. The guarantee is then
    :math:`AV_0/P^M(0, T_1)` floorlets on :math:`F_2` with the strike
    :math:`x = (SA\,P^M(0, T_1)/AV_0 - 1)/\tau`, and Black's formula with the shifted rate
    and strike gives

    .. math::

        PV = {} & \frac{AV_0}{P^M(0, T_1)}\tau P^M(0, T_2)
        \left[(x + \alpha)\Phi(v - d_1) - (F_2(0) + \alpha)\Phi(-d_1)\right] \\
        d_1 = {} & \frac{1}{v}\ln\frac{F_2(0) + \alpha}{x + \alpha} + \frac{v}{2}

    where SA is the sum assured of the policies maturing at :math:`T_2`, :math:`AV_0`
    their account value after the premium at time 0 (``av_at(0, "BEF_FEE")``),
    :math:`\alpha` the shift and :math:`v = \sigma_2\sqrt{T_1}`, with :math:`\sigma_2` from
    ``esg.caplet_vol(2)``. The value is 0 if :math:`x + \alpha \le 0`, as the account
    value then always exceeds the sum assured. Raises ``ValueError`` unless t is the
    second tenor date and the fund is all cash; for other policies the LMM gives no closed
    form.

    Returns:
        pandas.Series indexed by ``point_id`` of the single-premium points maturing at t
    """
    p = esg.tenor_mth()
    if t != 2 * p:
        raise ValueError(f"formula_gmab_floorlet needs the maturity at the second tenor "
                         f"date, month {2 * p}; got month {t}")
    if esg.fund_cash_share() != 1:
        raise ValueError(f"formula_gmab_floorlet needs an all-cash fund; fund "
                         f"{esg.fund_id()} holds bonds")
    mps = model_point_table_ext()
    n_scen = len(esg.scen_index())
    keep = ((mps["policy_term"] * 12 - mps["duration_mth"] == t)
            & (mps["premium_type"] == "SINGLE")).to_numpy()
    sa = (sum_assured() * pols_maturity(t))[::n_scen][keep]
    av0 = av_at(0, "BEF_FEE")[::n_scen][keep]
    tau, alpha = p / 12, esg.shift()
    p1, p2 = esg.mkt_zcb(p), esg.mkt_zcb(2 * p)
    fwd = esg.mkt_fwd_rates()[1] + alpha
    strike = (sa * p1 / av0 - 1) / tau + alpha
    v = esg.caplet_vol(2) * np.sqrt(tau)
    d1 = np.log(fwd / np.where(strike > 0, strike, 1.0)) / v + v / 2
    put = strike * stats.norm.cdf(v - d1) - fwd * stats.norm.cdf(-d1)
    pv = np.where(strike > 0, av0 / p1 * tau * p2 * put, 0.0)
    return pd.Series(pv, index=mps.index[keep], name="GMAB")


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit(f"expected one occurrence of {old[:60]!r}; edit the script")
    return text.replace(old, new)


def build():
    model = mx.read_model(SOURCE, name="CashValue_ME_LMM")
    proj = model.Projection
    del model.ESG
    lmm_model = mx.read_model(LIBRARY / "BasicLMM", name="BasicLMM_source")
    esg = lmm_model.LMM.copy(model, "ESG")
    esg.t_.doc = lmm_model.LMM.t_.doc
    lmm_model.close()
    proj.esg = esg
    del proj.formula_gmab_g2pp
    proj.new_cells(formula=formula_gmab_floorlet)
    doc = replace_once(proj.doc, G2PP_INTRO, LMM_INTRO)
    doc = replace_once(doc, G2PP_FORMULA_ITEM, LMM_FORMULA_ITEM)
    proj.doc = replace_once(doc, G2PP_ESG_ATTRIBUTE, LMM_ESG_ATTRIBUTE)
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
    parser.add_argument("--force", action="store_true", help="replace an existing model")
    args = parser.parse_args()
    if TARGET.exists():
        if not args.force:
            raise SystemExit(f"{TARGET} exists: edit it directly, or pass --force to rebuild it")
        remove_tree(TARGET)
    model = build()
    mx.write_model(model, TARGET, backup=False)
    model.close()
    print(f"wrote {TARGET}")
    check(TARGET)


if __name__ == "__main__":
    main()
