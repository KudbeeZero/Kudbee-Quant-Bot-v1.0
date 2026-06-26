"""Tests for research/management_geometry_study.py — CI-safe synthetic guards.

  (a) the paired B branch reproduces bracket_backtest's BASELINE net-R EXACTLY
      (fidelity lock — B drives the entry timeline, same as trailing_sweep);
  (b) A (ride-3R) and C (partial no-BE) are produced per the same entries and
      differ from B on a synthetic series (the geometries are really distinct);
  (c) the pre-registered verdict gate: rejects small n, lets B stand when A
      doesn't beat it, and attributes the drag to the BE slide vs the partial.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "research"))

from kudbee_quant.backtest.bracket import bracket_backtest  # noqa: E402

import management_geometry_study as mg  # noqa: E402
import trailing_sweep as ts  # noqa: E402


def _frame(seed: int = 11, n: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0, 0.004, n)
    close = 100.0 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.002, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.002, n)))
    op = np.r_[close[0], close[:-1]]
    atr = pd.Series(high - low).rolling(14, min_periods=1).mean().to_numpy()
    return pd.DataFrame({"open": op, "high": high, "low": low, "close": close, "atr": atr})


def _alt_signal(df: pd.DataFrame) -> pd.Series:
    sig = pd.Series(0.0, index=df.index)
    sig.iloc[::9] = 1.0
    sig.iloc[5::17] = -1.0
    return sig


# --- (a) fidelity: paired B == bracket_backtest baseline --------------------

def test_paired_B_reproduces_bracket_baseline_exactly():
    df = _frame()
    sig = _alt_signal(df)
    engine = bracket_backtest(df, sig, **ts.BASELINE_KW)
    rows = mg.paired_geometries(df, sig)
    net_b = [r["net_b"] for r in rows]
    assert len(net_b) == engine.n_trades, f"count: paired={len(net_b)} engine={engine.n_trades}"
    np.testing.assert_allclose(net_b, engine.trades, rtol=0, atol=1e-12)


# --- (b) the three geometries are distinct ----------------------------------

def test_geometries_are_distinct_and_paired():
    df = _frame()
    sig = _alt_signal(df)
    rows = mg.paired_geometries(df, sig)
    a = np.array([r["net_a"] for r in rows])
    b = np.array([r["net_b"] for r in rows])
    c = np.array([r["net_c"] for r in rows])
    assert len(a) == len(b) == len(c) and len(a) > 0          # paired, non-empty
    assert not np.allclose(a, b)                               # A != B
    assert not np.allclose(b, c)                               # B != C (BE slide matters)


# --- (c) verdict gate -------------------------------------------------------

def _res(a, b, c, boot_p_ab):
    def stat(arr):
        arr = np.asarray(arr, float)
        return {"n": arr.size, "mean_r": float(arr.mean()), "win_rate": 0.5,
                "total_r": float(arr.sum()), "boot_p": 0.2}
    return {
        "n": len(a),
        "geom": {"A ride-3R": stat(a), "B bank-half/BE (live)": stat(b),
                 "C partial no-BE": stat(c)},
        "deltas": {
            "A-B": {"mean_delta": float(np.mean(a) - np.mean(b)), "boot_p_x_le_y": boot_p_ab},
            "A-C": {"mean_delta": float(np.mean(a) - np.mean(c)), "boot_p_x_le_y": 0.5},
            "C-B": {"mean_delta": float(np.mean(c) - np.mean(b)), "boot_p_x_le_y": 0.5},
        },
    }


def test_verdict_rejects_small_n():
    res = _res([0.2] * 10, [0.0] * 10, [0.1] * 10, boot_p_ab=0.01)
    assert "REJECT" in mg.verdict(res) and "n<50" in mg.verdict(res)


def test_verdict_B_stands_when_A_not_better():
    # A ~ B (tiny delta) -> current management stands
    res = _res([0.05] * 80, [0.045] * 80, [0.05] * 80, boot_p_ab=0.4)
    v = mg.verdict(res)
    assert "NOT shown inferior" in v and "no change" in v.lower()


def test_verdict_isolates_be_slide_when_C_matches_A():
    # A beats B; and C ~ A (removing the BE slide recovers ride-3R) -> slide is the drag.
    res = _res([0.20] * 80, [0.05] * 80, [0.195] * 80, boot_p_ab=0.001)
    v = mg.verdict(res)
    assert "BE SLIDE is the drag" in v and "governance" in v.lower()


def test_verdict_blames_partial_when_C_below_A():
    # A beats B; C sits well below A (dropping the slide alone doesn't recover) ->
    # the partial close itself is the larger drag.
    res = _res([0.20] * 80, [0.05] * 80, [0.08] * 80, boot_p_ab=0.001)
    v = mg.verdict(res)
    assert "PARTIAL CLOSE itself" in v and "ride-3R" in v
