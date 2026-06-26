"""Tests for research/vah_trap_reversal.py — CI-safe synthetic guards.

  (a) the trade enumerator reproduces bracket_backtest's BASELINE net-R EXACTLY
      (fidelity lock — no reimplementation drift);
  (b) session_vah computes the value-area-high of a hand-built profile correctly;
  (c) prior_session_vah_array maps each bar to the PRIOR day's VAH (NaN day 1);
  (d) the qualifying flag = proximity AND rejection; the pre-registered verdict
      gate ACCEPTs/REJECTs on the locked thresholds.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "research"))

from kudbee_quant.backtest.bracket import bracket_backtest  # noqa: E402

import trailing_sweep as ts  # noqa: E402
import vah_trap_reversal as vah  # noqa: E402


def _synthetic_frame(seed: int = 11, n: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0, 0.004, n)
    close = 100.0 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.002, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.002, n)))
    op = np.r_[close[0], close[:-1]]
    atr = pd.Series(high - low).rolling(14, min_periods=1).mean().to_numpy()
    vol = rng.uniform(100, 1000, n)
    ts_idx = pd.date_range("2024-06-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({
        "timestamp": ts_idx, "open": op, "high": high, "low": low, "close": close,
        "volume": vol, "atr": atr, "utc_date": ts_idx.tz_convert("UTC").date,
    })


def _alt_signal(df: pd.DataFrame) -> pd.Series:
    sig = pd.Series(0.0, index=df.index)
    sig.iloc[::9] = 1.0
    sig.iloc[5::17] = -1.0
    return sig


# --- (a) fidelity: enumerator net-R == bracket_backtest baseline ------------

def test_vah_enumerator_reproduces_bracket_baseline_exactly():
    df = _synthetic_frame()
    sig = _alt_signal(df)
    engine = bracket_backtest(df, sig, **ts.BASELINE_KW)
    pv = vah.prior_session_vah_array(df)
    rows = vah.vah_trades(df, sig, pv)
    net = [r["net_r"] for r in rows]
    assert len(net) == engine.n_trades, f"count: mirror={len(net)} engine={engine.n_trades}"
    np.testing.assert_allclose(net, engine.trades, rtol=0, atol=1e-12)


# --- (b) value-area-high of a known profile ---------------------------------

def test_session_vah_on_hand_built_profile():
    # Heavy volume concentrated mid-range; thin tails. VAH must sit at the top of
    # the contiguous 70% band around the POC, below the session high.
    high = np.array([10.0, 11.0, 12.0, 13.0, 20.0])
    low = np.array([9.0, 10.0, 11.0, 12.0, 10.0])
    close = np.array([9.5, 10.5, 11.5, 12.5, 11.0])
    vol = np.array([100.0, 1000.0, 1000.0, 100.0, 5.0])  # POC in the 10.5-11.5 zone
    v = vah.session_vah(high, low, close, vol, bins=20)
    assert np.isfinite(v)
    assert v < 20.0, "VAH must exclude the thin high tail"
    assert v > 11.0, "VAH must sit above the POC typical price"


def test_session_vah_degenerate_is_nan():
    assert np.isnan(vah.session_vah(np.array([5.0]), np.array([5.0]),
                                    np.array([5.0]), np.array([0.0])))


# --- (c) prior-session mapping ----------------------------------------------

def test_prior_session_vah_first_day_is_nan_then_prior():
    df = _synthetic_frame(n=72)               # 3 UTC days of hourly bars
    pv = vah.prior_session_vah_array(df)
    days = df["utc_date"].astype(str).to_numpy()
    first_day = days == days[0]
    assert np.all(np.isnan(pv[first_day])), "day 1 has no prior session -> NaN"
    assert np.isfinite(pv[~first_day]).any(), "later days must carry a prior VAH"


# --- (d) qualifying flag + pre-registered verdict gate ----------------------

def test_verdict_accepts_only_when_all_gates_pass():
    base = vah._block([0.05] * 200, boot_p=lambda x: 0.5)
    # qualifying: clearly positive, big n, tiny boot_p, improvement > 0.02R
    res = {"n_total": 200, "cells": {
        "baseline_all": base,
        "qualifying (near VAH + rejection)": vah._block([0.30] * 40, boot_p=lambda x: 0.001),
        "near VAH, NO rejection (specificity)": vah._block([0.0] * 10, boot_p=lambda x: 0.6),
        "qualifying — long": vah._block([0.3] * 20, boot_p=lambda x: 0.01),
        "qualifying — short": vah._block([0.3] * 20, boot_p=lambda x: 0.01),
    }}
    assert "ACCEPT" in vah.verdict(res)


def test_verdict_rejects_small_n_even_if_positive():
    base = vah._block([0.05] * 200, boot_p=lambda x: 0.5)
    res = {"n_total": 200, "cells": {
        "baseline_all": base,
        "qualifying (near VAH + rejection)": vah._block([0.30] * 12, boot_p=lambda x: 0.001),
        "near VAH, NO rejection (specificity)": vah._block([], boot_p=lambda x: 0.5),
        "qualifying — long": vah._block([], boot_p=lambda x: 0.5),
        "qualifying — short": vah._block([], boot_p=lambda x: 0.5),
    }}
    v = vah.verdict(res)
    assert "REJECT" in v and "n_qualifying=12" in v


def test_verdict_rejects_improvement_within_noise():
    base = vah._block([0.05] * 200, boot_p=lambda x: 0.5)
    # significant and big n, but only +0.01R over baseline (< 0.02R) -> REJECT
    res = {"n_total": 200, "cells": {
        "baseline_all": base,
        "qualifying (near VAH + rejection)": vah._block([0.06] * 50, boot_p=lambda x: 0.001),
        "near VAH, NO rejection (specificity)": vah._block([], boot_p=lambda x: 0.5),
        "qualifying — long": vah._block([], boot_p=lambda x: 0.5),
        "qualifying — short": vah._block([], boot_p=lambda x: 0.5),
    }}
    assert "REJECT" in vah.verdict(res)
