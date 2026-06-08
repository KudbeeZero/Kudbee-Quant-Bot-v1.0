"""PVSRA Vector Candles — the Traders Reality (Tino) signature signal.

PVSRA = Price / Volume / Spread / Read Analysis. It is a Volume-Spread-
Analysis descendant of Wyckoff that flags "climax" bars where unusually
high volume (and volume x spread) suggests large-player activity.

Classification (the canonical Traders Reality rules):
    spread          = high - low
    av              = sma(volume, lookback)            # avg volume
    climax_product  = highest(volume * spread, lookback)

    A bar is a CLIMAX / "vector" candle when:
        volume >= climax_mult * av
        OR  volume * spread >= climax_product
    A bar is RISING / above-average when (and not already climax):
        volume >= rising_mult * av

    Colouring:
        bullish (close > open)  climax -> green     rising -> blue
        bearish (close < open)  climax -> red       rising -> violet
        otherwise                                   -> neutral

HONESTY NOTE: a vector candle marks *where volume showed up*. It is a
hypothesis about intent, not proof of direction. Treat the output as a
feature to be validated by the backtest engine, never as a trade signal
on its own.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Default palette mirrors the Traders Reality TradingView script.
BULL_CLIMAX = "#00ff00"   # lime
BEAR_CLIMAX = "#ff0000"   # red
BULL_RISING = "#0000ff"   # blue
BEAR_RISING = "#ee82ee"   # violet
NEUTRAL = "#7f7f7f"       # gray


@dataclass(frozen=True)
class VectorCandleConfig:
    lookback: int = 10
    climax_mult: float = 2.0
    rising_mult: float = 1.5


def pvsra_vector_candles(df: pd.DataFrame, config: VectorCandleConfig | None = None) -> pd.DataFrame:
    """Annotate an OHLCV frame with PVSRA vector-candle classification.

    Args:
        df: must contain columns open, high, low, close, volume.
        config: thresholds; defaults match the standard TR script.

    Returns:
        A copy of ``df`` with added columns:
          spread, avg_volume, climax_product, is_climax, is_rising,
          vector (category str), vector_color (hex str).
    """
    config = config or VectorCandleConfig()
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing OHLCV columns: {sorted(missing)}")

    out = df.copy()
    spread = out["high"] - out["low"]
    av = out["volume"].rolling(config.lookback, min_periods=1).mean()
    vol_spread = out["volume"] * spread
    climax_product = vol_spread.rolling(config.lookback, min_periods=1).max()

    is_climax = (out["volume"] >= config.climax_mult * av) | (vol_spread >= climax_product)
    is_rising = (~is_climax) & (out["volume"] >= config.rising_mult * av)
    is_bull = out["close"] > out["open"]

    vector = np.select(
        [
            is_climax & is_bull,
            is_climax & ~is_bull,
            is_rising & is_bull,
            is_rising & ~is_bull,
        ],
        ["bull_climax", "bear_climax", "bull_rising", "bear_rising"],
        default="neutral",
    )
    color = np.select(
        [
            vector == "bull_climax",
            vector == "bear_climax",
            vector == "bull_rising",
            vector == "bear_rising",
        ],
        [BULL_CLIMAX, BEAR_CLIMAX, BULL_RISING, BEAR_RISING],
        default=NEUTRAL,
    )

    out["spread"] = spread
    out["avg_volume"] = av
    out["climax_product"] = climax_product
    out["is_climax"] = is_climax
    out["is_rising"] = is_rising
    out["vector"] = vector
    out["vector_color"] = color
    return out
