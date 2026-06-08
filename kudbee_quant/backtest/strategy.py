"""PVSRA vector-candle strategy — the worked example of the hybrid system.

Hypothesis (Traders Reality logic): a bullish climax candle marks large-
player accumulation -> go long; a bearish climax marks distribution -> go
short (or flat). This is exactly the discretionary read we want to *measure*
rather than believe. Feed the output to run_backtest + monte_carlo to find
out whether the edge is real on a given asset/timeframe.
"""
from __future__ import annotations

import pandas as pd

from ..context import SessionWindows, add_mm_context
from ..signals import VectorCandleConfig, pvsra_vector_candles


def pvsra_positions(
    df: pd.DataFrame,
    config: VectorCandleConfig | None = None,
    allow_short: bool = True,
    hold: bool = True,
) -> pd.Series:
    """Map PVSRA vector candles to a target-position series in {-1, 0, 1}.

    Args:
        df: OHLCV frame.
        config: vector-candle thresholds.
        allow_short: if False, bearish climax -> flat (0) instead of -1.
        hold: if True, carry the last non-zero position forward until the
            opposite climax appears (a stateful "regime" read). If False,
            only take a position on the climax bar itself.
    """
    annotated = pvsra_vector_candles(df, config)
    vec = annotated["vector"]

    raw = pd.Series(0.0, index=annotated.index)
    raw[vec == "bull_climax"] = 1.0
    raw[vec == "bear_climax"] = -1.0 if allow_short else 0.0

    if not hold:
        return raw

    # Carry the regime forward: stay long until a bear climax, vice versa.
    position = raw.replace(0.0, pd.NA).ffill().fillna(0.0).astype(float)
    if not allow_short:
        position = position.clip(lower=0.0)
    return position


def pvsra_mm_positions(
    df: pd.DataFrame,
    config: VectorCandleConfig | None = None,
    windows: SessionWindows | None = None,
    allow_short: bool = True,
    require_session: bool = True,
) -> pd.Series:
    """Hybrid strategy: PVSRA climax confirmed by MM-cycle context.

    The naive PVSRA strategy loses because it trades every climax regardless
    of structure. This version only acts when the climax aligns with a
    market-maker read:

      LONG  : bull climax AND (a liquidity sweep of a low just occurred
              OR price is above the previous-day high — a bullish regime)
      SHORT : bear climax AND (sweep of a high OR price below prev-day low)

    and, when ``require_session`` is set, only during the London/NY windows
    where MM activity concentrates. This is a *hypothesis* — backtest it.
    """
    ctx = add_mm_context(df, windows)
    ctx = pvsra_vector_candles(ctx, config)
    vec = ctx["vector"]

    bullish_regime = (ctx["sweep_bias"] > 0) | (ctx["close"] > ctx["pdh"])
    bearish_regime = (ctx["sweep_bias"] < 0) | (ctx["close"] < ctx["pdl"])
    active = (ctx["in_london"] | ctx["in_ny"]) if require_session else True

    raw = pd.Series(0.0, index=ctx.index)
    raw[(vec == "bull_climax") & bullish_regime & active] = 1.0
    if allow_short:
        raw[(vec == "bear_climax") & bearish_regime & active] = -1.0

    position = raw.replace(0.0, pd.NA).ffill().fillna(0.0).astype(float)
    if not allow_short:
        position = position.clip(lower=0.0)
    return position
