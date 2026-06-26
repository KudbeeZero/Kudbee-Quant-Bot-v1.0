"""Tests for research/ema_800_study.py — CI-safe synthetic guards.

  (a) the enumerator reproduces bracket_backtest's BASELINE net-R EXACTLY
      (fidelity lock — no reimplementation drift);
  (b) bucketing classifies ABOVE/BELOW the ema_800 column at the signal bar and
      excludes warm-up NaNs;
  (c) the pre-registered verdict gate ACCEPTs only when all conditions hold and
      REJECTs on small n / weak p / within-noise improvement.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "research"))

from kudbee_quant.backtest.bracket import bracket_backtest  # noqa: E402

import ema_800_study as ema  # noqa: E402
import trailing_sweep as ts  # noqa: E402


def _frame(seed: int = 11, n: int = 600, ema_const: float | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0, 0.004, n)
    close = 100.0 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.002, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.002, n)))
    op = np.r_[close[0], close[:-1]]
    atr = pd.Series(high - low).rolling(14, min_periods=1).mean().to_numpy()
    ema_800 = np.full(n, ema_const if ema_const is not None else float("nan")) \
        if ema_const is not None else pd.Series(close).ewm(span=800, min_periods=1).mean().to_numpy()
    return pd.DataFrame({"open": op, "high": high, "low": low, "close": close,
                         "atr": atr, "ema_800": ema_800})


def _alt_signal(df: pd.DataFrame) -> pd.Series:
    sig = pd.Series(0.0, index=df.index)
    sig.iloc[::9] = 1.0
    sig.iloc[5::17] = -1.0
    return sig


# --- (a) fidelity -----------------------------------------------------------

def test_enumerator_reproduces_bracket_baseline_exactly():
    df = _frame()
    sig = _alt_signal(df)
    engine = bracket_backtest(df, sig, **ts.BASELINE_KW)
    rows = ema.ema800_trades(df, sig)
    net = [r["net_r"] for r in rows]
    assert len(net) == engine.n_trades
    np.testing.assert_allclose(net, engine.trades, rtol=0, atol=1e-12)
    assert {r["bucket"] for r in rows} <= {"above", "below", "excluded"}


# --- (b) bucketing ----------------------------------------------------------

def test_bucketing_above_below_and_excludes_nan():
    df = _frame()
    sig = _alt_signal(df)
    # Pin ema_800 far BELOW price -> every classified trade is ABOVE.
    df_above = df.copy()
    df_above["ema_800"] = 1.0
    rows = ema.ema800_trades(df_above, sig)
    buckets = {r["bucket"] for r in rows}
    assert "above" in buckets and "below" not in buckets

    # NaN ema_800 -> all excluded.
    df_nan = df.copy()
    df_nan["ema_800"] = np.nan
    rows_nan = ema.ema800_trades(df_nan, sig)
    assert all(r["bucket"] == "excluded" for r in rows_nan)


# --- (c) verdict gate -------------------------------------------------------

def _res(above, below, base, bp_above):
    bp = lambda x: 0.5  # noqa: E731
    return {"n_total": 0, "n_excluded": 0, "cells": {
        "baseline (all classified)": ema._block(base, bp),
        "ABOVE 800-EMA": ema._block(above, lambda x: bp_above),
        "BELOW 800-EMA": ema._block(below, bp),
    }}


def test_verdict_accepts_when_all_gates_pass():
    res = _res(above=[0.20] * 40, below=[-0.05] * 40, base=[0.05] * 200, bp_above=0.001)
    assert "ACCEPT" in ema.verdict(res)


def test_verdict_rejects_small_n():
    res = _res(above=[0.20] * 12, below=[-0.05] * 40, base=[0.05] * 200, bp_above=0.001)
    v = ema.verdict(res)
    assert "REJECT" in v and "n_above=12" in v


def test_verdict_rejects_within_noise_improvement():
    # significant + big n but only +0.01R over baseline -> REJECT
    res = _res(above=[0.06] * 50, below=[0.05] * 50, base=[0.05] * 200, bp_above=0.001)
    assert "REJECT" in ema.verdict(res)
