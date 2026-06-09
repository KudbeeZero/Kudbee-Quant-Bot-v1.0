"""RSI / momentum divergence (Vol 9 sec 4) — a non-redundant reversal signal.

Unlike the trend/level confluence factors, divergence is a MOMENTUM-REVERSAL
signal at swings, so it carries different information. Causal: a divergence is
only confirmed once the swing is confirmed (``right`` bars later), and exposed
from that bar.

Bullish divergence: price makes a LOWER low while RSI makes a HIGHER low.
Bearish divergence: price makes a HIGHER high while RSI makes a LOWER high.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def add_divergence(df: pd.DataFrame, left: int = 3, right: int = 3,
                   period: int = 14, persist: int = 4) -> pd.DataFrame:
    """Add div_vote in {-1,0,+1}: +1 bullish divergence, -1 bearish (causal)."""
    out = df.copy()
    high = out["high"].to_numpy()
    low = out["low"].to_numpy()
    r = rsi(out["close"], period).to_numpy()
    n = len(out)
    vote = np.zeros(n)

    prev_low_price = prev_low_rsi = None
    prev_high_price = prev_high_rsi = None
    for i in range(left, n - right):
        win_hi = high[i - left:i + right + 1]
        win_lo = low[i - left:i + right + 1]
        conf = i + right  # divergence known only when the swing confirms
        if low[i] == win_lo.min() and win_lo.argmin() == left:   # swing low
            if prev_low_price is not None and low[i] < prev_low_price and r[i] > prev_low_rsi:
                vote[conf] = 1.0   # bullish divergence
            prev_low_price, prev_low_rsi = low[i], r[i]
        if high[i] == win_hi.max() and win_hi.argmax() == left:   # swing high
            if prev_high_price is not None and high[i] > prev_high_price and r[i] < prev_high_rsi:
                vote[conf] = -1.0  # bearish divergence
            prev_high_price, prev_high_rsi = high[i], r[i]

    out["rsi"] = r
    # Persist the divergence signal a few bars (it is actionable for a window).
    out["div_vote"] = pd.Series(vote).replace(0.0, np.nan).ffill(limit=persist).fillna(0.0).to_numpy()
    return out
