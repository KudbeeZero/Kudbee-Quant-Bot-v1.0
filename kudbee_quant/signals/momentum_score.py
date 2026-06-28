"""Momentum score (0.0 .. 1.0) for an open position — drives the dynamic TP2 of
the tiered exit (``execution/tiered_exit.py``).

Score interpretation (mapping lives in ``tiered_exit.dynamic_tp2_r``):
    > 0.65  -> strong momentum, extend TP2 to 3R
    0.35-0.65 -> keep TP2 at 2R
    < 0.35  -> weak, tighten TP2 to 1.5R (take profit faster)

The composite is the equal-weight (0.25 each) mean of four sub-scores. Each
reuses an EXISTING engine primitive — nothing here rebuilds signal detection:
  1. VOLUME      — current bar volume vs its 20-bar average.
  2. TREND       — price vs EMA20 & EMA50 in the trade direction.
  3. PVSRA       — >=1 PVSRA climax bar in the trade direction since entry
                   (reuses ``signals.pvsra.pvsra_vector_candles``).
  4. SR_CLEARANCE— distance to the next reference level beyond price (from the
                   ``levels`` columns already on the frame), measured in R.

All sub-scores are causal: a bar's score uses only that bar and earlier ones.
"""
from __future__ import annotations

import pandas as pd

from .pvsra import pvsra_vector_candles

_SR_COLUMNS = (
    "pdh", "pdl", "pwh", "pwl", "round_above", "round_below",
    "pivot_r1", "pivot_s1", "pivot_r2", "pivot_s2", "vwap",
    "mlevel_m0", "mlevel_m1", "mlevel_m2", "mlevel_m3", "mlevel_m4", "mlevel_m5",
)


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def volume_momentum(bars: pd.DataFrame, idx: int) -> float:
    """Current bar volume vs the trailing 20-bar average."""
    vol = bars["volume"]
    avg = vol.rolling(20, min_periods=1).mean().iloc[idx]
    if avg <= 0:
        return 0.5
    ratio = float(vol.iloc[idx]) / float(avg)
    return 1.0 if ratio >= 2.0 else (0.5 if ratio >= 1.0 else 0.0)


def trend_alignment(bars: pd.DataFrame, idx: int, direction: float) -> float:
    """Price above (long) / below (short) both EMA20 and EMA50."""
    close = bars["close"]
    px = float(close.iloc[idx])
    e20 = float(_ema(close, 20).iloc[idx])
    e50 = float(_ema(close, 50).iloc[idx])
    a20 = (px > e20) if direction > 0 else (px < e20)
    a50 = (px > e50) if direction > 0 else (px < e50)
    return 1.0 if (a20 and a50) else (0.5 if (a20 or a50) else 0.0)


def pvsra_continuation(bars: pd.DataFrame, since_idx: int, idx: int, direction: float) -> float:
    """1.0 iff at least one PVSRA climax bar in the trade direction occurred
    between ``since_idx`` and ``idx`` (inclusive). Uses precomputed
    ``is_climax``/``vector`` columns when present, else computes them causally."""
    if "is_climax" in bars.columns and "vector" in bars.columns:
        sub = bars
    else:
        sub = pvsra_vector_candles(bars.iloc[: idx + 1])
    lo = max(0, since_idx)
    window = sub.iloc[lo: idx + 1]
    want = "bull" if direction > 0 else "bear"
    hit = window["is_climax"] & window["vector"].astype(str).str.startswith(want)
    return 1.0 if bool(hit.any()) else 0.0


def sr_clearance(bars: pd.DataFrame, idx: int, direction: float, sd: float) -> float:
    """Distance to the nearest reference level ahead of price (trade direction),
    expressed in R (``sd`` = 1R). Far = clear runway = high score."""
    if sd <= 0:
        return 1.0
    px = float(bars["close"].iloc[idx])
    ahead = []
    for col in _SR_COLUMNS:
        if col in bars.columns:
            v = bars[col].iloc[idx]
            if pd.notna(v):
                v = float(v)
                if (v > px) if direction > 0 else (v < px):
                    ahead.append(v)
    if not ahead:
        return 1.0
    nearest = min(ahead) if direction > 0 else max(ahead)
    dist_r = abs(nearest - px) / sd
    return 1.0 if dist_r > 1.5 else (0.5 if dist_r >= 0.5 else 0.0)


def momentum_score(bars: pd.DataFrame, idx: int, direction: float,
                   since_idx: int | None = None, sd: float | None = None) -> float:
    """Composite momentum score in [0, 1] at bar ``idx`` for a trade in
    ``direction`` (+1/-1) opened at ``since_idx`` (defaults to ``idx``).

    ``sd`` is the 1R price distance; defaults to the bar's ATR if the frame has
    an ``atr`` column, else 1.0.
    """
    if since_idx is None:
        since_idx = idx
    if sd is None:
        sd = float(bars["atr"].iloc[idx]) if "atr" in bars.columns else 1.0
    parts = (
        volume_momentum(bars, idx),
        trend_alignment(bars, idx, direction),
        pvsra_continuation(bars, since_idx, idx, direction),
        sr_clearance(bars, idx, direction, sd),
    )
    return float(sum(parts) / 4.0)
