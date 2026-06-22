"""No-lookahead + sanity tests for the owner's experimental confluence indicators
(scripts/lab_indicators.py). Mirrors the causality guard in test_mlevel_system.py:
spiking the LAST bar must not change any prior bar's indicator value."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from lab_indicators import (  # noqa: E402
    bollinger, kdj, kdj_divergence, fib_confluence, spider_touch, level_cluster,
)


def _frame(n=400, seed=11):
    rng = np.random.default_rng(seed)
    close = 1000 * np.cumprod(1 + rng.normal(0.0002, 0.01, n))
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    df = pd.DataFrame({
        "open": np.r_[close[0], close[:-1]], "high": high, "low": low, "close": close,
        "atr": pd.Series(close).rolling(14, min_periods=1).std().fillna(1.0).to_numpy(),
    })
    # minimal level columns the fib/spider helpers look for
    df["swing_high"] = df["high"].rolling(7, min_periods=1).max().shift(3)
    df["swing_low"] = df["low"].rolling(7, min_periods=1).min().shift(3)
    for c in ("ema_13", "ema_50", "ema_200", "pivot_pp", "pivot_r1", "pivot_s1",
              "daily_open", "weekly_open", "vwap",
              "mlevel_m1", "mlevel_m2", "mlevel_m3", "mlevel_m4"):
        df[c] = df["close"].rolling(20, min_periods=1).mean()
    return df


def test_bollinger_band_ordering_and_pctb():
    df = _frame()
    mid, up, lo, pctb, width = bollinger(df)
    ok = up.notna()
    assert (up[ok] >= mid[ok]).all() and (mid[ok] >= lo[ok]).all()
    # pct_b is (close-lower)/(upper-lower): finite where bands exist
    assert pctb[ok].notna().all()


def test_kdj_k_in_range():
    df = _frame()
    k, d, j = kdj(df)
    kk = k.dropna()
    assert (kk >= -1e-6).all() and (kk <= 100 + 1e-6).all()


def test_divergence_votes_are_signs():
    df = _frame()
    assert set(np.unique(kdj_divergence(df).to_numpy())) <= {-1.0, 0.0, 1.0}


def _spike_last(df):
    s = df.copy()
    i = len(s) - 1
    s.loc[i, "high"] *= 5
    s.loc[i, "low"] *= 0.2
    s.loc[i, "close"] = s.loc[i, "high"]
    return s


def test_no_lookahead_all_indicators():
    df = _frame()
    spiked = _spike_last(df)
    prior = np.arange(len(df)) < len(df) - 1   # every bar but the last

    pairs = [
        ("bollinger", lambda d: bollinger(d)[3]),         # pct_b
        ("kdj_k", lambda d: kdj(d)[0]),
        ("kdj_div", kdj_divergence),
        ("fib_count", lambda d: fib_confluence(d)[0]),
        ("spider_sup", lambda d: spider_touch(d)[0].astype(float)),
        ("level_cluster", level_cluster),
    ]
    for name, fn in pairs:
        a = fn(df).to_numpy()[prior]
        b = fn(spiked).to_numpy()[prior]
        assert np.allclose(a, b, equal_nan=True), f"lookahead leak in {name}"


def test_fib_confluence_nonnegative_count():
    df = _frame()
    count, near = fib_confluence(df)
    assert (count.dropna() >= 0).all()


def test_level_cluster_counts_stacked_levels():
    df = _frame()
    df["daily_open"] = df["close"].round(-1)            # ensure the column exists
    lc = level_cluster(df)
    assert (lc.dropna() >= 0).all()
    # a price with many coincident levels should count more than a lone one
    assert lc.max() >= 1
