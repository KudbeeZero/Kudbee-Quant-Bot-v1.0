"""Resample OHLCV to arbitrary timeframes (e.g. 7m, 3h) that exchanges don't serve.

Lets us survey 'strange' timeframes (7-minute, 3-hour) by aggregating a base
interval. Strictly causal: a resampled bar only uses the base bars within it.
"""
from __future__ import annotations

import pandas as pd


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate an OHLCV frame to a pandas offset ``rule`` (e.g. '7min', '3h')."""
    s = df.copy()
    s["timestamp"] = pd.to_datetime(s["timestamp"], utc=True)
    s = s.set_index("timestamp")
    agg = pd.DataFrame({
        "open": s["open"].resample(rule, label="left", closed="left").first(),
        "high": s["high"].resample(rule, label="left", closed="left").max(),
        "low": s["low"].resample(rule, label="left", closed="left").min(),
        "close": s["close"].resample(rule, label="left", closed="left").last(),
        "volume": s["volume"].resample(rule, label="left", closed="left").sum(),
    }).dropna(subset=["open", "high", "low", "close"])
    return agg.reset_index()
