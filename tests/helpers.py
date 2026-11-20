"""Paths and helpers shared by the tests."""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "g2pp_input.xlsx"
MODEL_DIR = ROOT / "BasicG2PP"


def lifelib_path(*parts):
    """Path of a file or folder in lifelib's ``libraries`` folder; skip if unavailable."""
    try:
        import lifelib
    except ImportError:
        pytest.skip("lifelib is not installed")
    path = Path(lifelib.__file__).parent / "libraries" / Path(*parts)
    if not path.exists():
        pytest.skip(f"{path} not found")
    return path


def write_workbook(path, params=None, curve=None, fund=None, drop_params=(), base=INPUT):
    """Write a copy of ``base`` to ``path``.

    ``params`` overrides values in the Params sheet (adding rows if needed) and
    ``drop_params`` removes rows. ``curve`` and ``fund`` replace the Curve and Fund sheets
    with the given DataFrames, which must include their ``maturity`` column.
    """
    sheets = pd.read_excel(base, sheet_name=None)
    if params or drop_params:
        table = sheets["Params"].set_index("parameter").drop(index=list(drop_params))
        for key, value in (params or {}).items():
            table.loc[key, "value"] = value
        sheets["Params"] = table.reset_index()
    if curve is not None:
        sheets["Curve"] = curve
    if fund is not None:
        sheets["Fund"] = fund
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return Path(path)
