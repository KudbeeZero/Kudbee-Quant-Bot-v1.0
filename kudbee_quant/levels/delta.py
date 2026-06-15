"""Bar-level taker delta, cumulative volume delta (CVD), and delta-divergence.

Derived purely from the ``taker_buy_base`` column Binance already ships on every
kline (see ingest/binance.py) — no second data source, no order-book feed. The
intuition: ``taker_buy_base`` is the share of the bar's volume that lifted the
offer (aggressive buying); the rest hit the bid (aggressive selling). Their
difference is the bar's net aggressive **delta**, and its running sum is **CVD**.

Everything here is causal — each column at bar ``t`` uses only data up to and
including the closed bar ``t`` (rolling/cumulative/shift), exactly like the
existing PVSRA / divergence features. Scale-free columns (``*_pct``, ``*_z``) are
normalised by volume or price so they pool across coins.

This module is OPT-IN: ``build_levels`` only calls it when
``FeatureFlags.enable_taker_delta`` is set (default OFF), so the default feature
frame — and live trading — is unchanged until the flag earns its place with
out-of-sample evidence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# The scale-free delta columns safe to feed a meta-model / pool across symbols.
DELTA_FEATURE_COLUMNS = [
    "delta_pct", "delta_z", "cvd_session_pct", "cvd_roll_pct", "delta_div",
]


def add_taker_delta(
    df: pd.DataFrame,
    roll: int = 24,
    z_window: int = 48,
    div_lookback: int = 12,
) -> pd.DataFrame:
    """Annotate bars with taker delta / CVD / delta-divergence (causal).

    Args:
        roll: window (bars) for the rolling-CVD and its volume normaliser.
        z_window: window for the per-bar delta z-score.
        div_lookback: window over which price extremes are compared to flow for
            the absorption-divergence flag.

    No-op (returns ``df`` unchanged) when ``taker_buy_base``/``volume`` are
    absent, so it is safe on synthetic or non-Binance frames.
    """
    if not {"taker_buy_base", "volume"} <= set(df.columns):
        return df
    out = df.copy()

    vol = out["volume"].astype(float)
    taker_buy = out["taker_buy_base"].astype(float).clip(lower=0.0)
    # Aggressive sell volume is whatever wasn't a taker-buy; clip guards rounding.
    taker_sell = (vol - taker_buy).clip(lower=0.0)
    out["taker_sell_base"] = taker_sell

    # Net aggressive delta and its volume-normalised form (-1 all-sell .. +1 all-buy).
    delta = taker_buy - taker_sell
    out["bar_delta"] = delta
    safe_vol = vol.replace(0, np.nan)
    out["delta_pct"] = (delta / safe_vol).clip(-1.0, 1.0)

    # Per-bar delta z-score: is this bar's aggression unusual vs recent history?
    dmean = delta.rolling(z_window, min_periods=z_window // 2).mean()
    dstd = delta.rolling(z_window, min_periods=z_window // 2).std().replace(0, np.nan)
    out["delta_z"] = ((delta - dmean) / dstd).replace([np.inf, -np.inf], np.nan)

    # Session-anchored CVD: running sum of delta within the UTC day (like VWAP),
    # plus a volume-normalised version that stays comparable across coins/days.
    if "utc_date" not in out.columns:
        out["utc_date"] = pd.to_datetime(out["timestamp"], utc=True).dt.date
    grp = delta.groupby(out["utc_date"])
    out["cvd_session"] = grp.cumsum()
    day_vol = vol.groupby(out["utc_date"]).cumsum().replace(0, np.nan)
    out["cvd_session_pct"] = (out["cvd_session"] / day_vol).clip(-1.0, 1.0)

    # Rolling CVD over a fixed window (boundary-free, stationary) + its pct form.
    cvd_roll = delta.rolling(roll, min_periods=max(2, roll // 2)).sum()
    roll_vol = vol.rolling(roll, min_periods=max(2, roll // 2)).sum().replace(0, np.nan)
    out["cvd_roll"] = cvd_roll
    out["cvd_roll_pct"] = (cvd_roll / roll_vol).clip(-1.0, 1.0)

    # Absorption divergence: price prints a fresh ``div_lookback``-bar extreme but
    # the rolling order-flow does NOT confirm it. New high on net-sell flow = -1
    # (bearish: buyers exhausted into supply); new low on net-buy flow = +1.
    close = out["close"]
    roll_hi = close.rolling(div_lookback, min_periods=2).max()
    roll_lo = close.rolling(div_lookback, min_periods=2).min()
    new_high = close >= roll_hi - 1e-12
    new_low = close <= roll_lo + 1e-12
    out["delta_div"] = np.where(new_high & (cvd_roll < 0), -1.0,
                                np.where(new_low & (cvd_roll > 0), 1.0, 0.0))
    return out
