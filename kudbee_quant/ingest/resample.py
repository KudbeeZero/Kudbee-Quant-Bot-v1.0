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
    cols = {
        "open": s["open"].resample(rule, label="left", closed="left").first(),
        "high": s["high"].resample(rule, label="left", closed="left").max(),
        "low": s["low"].resample(rule, label="left", closed="left").min(),
        "close": s["close"].resample(rule, label="left", closed="left").last(),
        "volume": s["volume"].resample(rule, label="left", closed="left").sum(),
    }
    # Preserve taker-buy volumes (summed) when present, so bar-delta / CVD survive
    # resampling to non-native timeframes. No-op on frames without them.
    for c in ("taker_buy_base", "taker_buy_quote", "quote_volume"):
        if c in s.columns:
            cols[c] = s[c].resample(rule, label="left", closed="left").sum()
    agg = pd.DataFrame(cols).dropna(subset=["open", "high", "low", "close"])
    if not agg.empty:
        # The trailing bucket may be PARTIAL: the source frame's last base bar can
        # land mid-bucket (e.g. resampling 1h bars to 3h with only 2 of the 3 hours
        # fetched so far), so its high/low/close don't reflect the bucket's true,
        # final values — the same failure class as scanning a still-forming
        # native-interval candle (§77), just one level up. A bucket only counts as
        # closed once the source data reaches (or passes) its END boundary; if not,
        # drop it rather than hand a misleadingly-final-looking partial bar
        # downstream. (Conservative: a historical slice that happens to end EXACTLY
        # on a bucket boundary loses one trailing row too — an inconsequential cost
        # next to trading a partial bar as if it were closed.)
        last_bucket_end = agg.index[-1] + pd.tseries.frequencies.to_offset(rule)
        if s.index.max() < last_bucket_end:
            agg = agg.iloc[:-1]
    return agg.reset_index()
