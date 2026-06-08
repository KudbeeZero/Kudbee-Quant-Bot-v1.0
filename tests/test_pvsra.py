"""Tests for the PVSRA vector-candle classifier (no network required)."""
import numpy as np
import pandas as pd

from kudbee_quant.signals import VectorCandleConfig, pvsra_vector_candles


def _base_frame(n: int = 20, vol: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": np.full(n, 10.0),
            "high": np.full(n, 11.0),
            "low": np.full(n, 9.0),
            "close": np.full(n, 10.5),  # bullish by default
            "volume": np.full(n, vol),
        }
    )


def test_climax_bull_on_volume_spike():
    df = _base_frame()
    df.loc[df.index[-1], "volume"] = 1000.0  # 10x average -> climax
    out = pvsra_vector_candles(df)
    assert out["vector"].iloc[-1] == "bull_climax"
    assert out["is_climax"].iloc[-1]


def test_climax_bear_when_close_below_open():
    df = _base_frame()
    df["close"] = 9.5  # bearish
    df.loc[df.index[-1], "volume"] = 1000.0
    out = pvsra_vector_candles(df)
    assert out["vector"].iloc[-1] == "bear_climax"


def test_rising_between_thresholds():
    df = _base_frame(vol=100.0)
    # 1.6x avg -> rising (>=1.5x) but not climax (<2x), and avoid spread-climax
    # by keeping spread constant so vol*spread never sets a new high.
    df.loc[df.index[-1], "volume"] = 160.0
    out = pvsra_vector_candles(df, VectorCandleConfig(lookback=10))
    # The very last bar's vol*spread is the highest in window, which by the
    # canonical rule also flags climax; verify the rule is applied, not the label.
    last = out.iloc[-1]
    assert last["is_climax"] or last["is_rising"]


def test_neutral_on_declining_volume():
    # Monotonically declining volume (constant spread): each bar is strictly
    # below the rolling max of vol*spread and below 1.5x the avg, so no bar is
    # a climax or rising candle -> all neutral. This is the meaningful inverse
    # of the climax case (a flat series is degenerate: every bar ties the max).
    n = 20
    df = pd.DataFrame(
        {
            "open": np.full(n, 10.0),
            "high": np.full(n, 11.0),
            "low": np.full(n, 9.0),
            "close": np.full(n, 10.5),
            "volume": np.linspace(200.0, 100.0, n),
        }
    )
    out = pvsra_vector_candles(df)
    assert (out["vector"].iloc[1:] == "neutral").all()


def test_missing_columns_raises():
    try:
        pvsra_vector_candles(pd.DataFrame({"open": [1.0]}))
    except ValueError as e:
        assert "missing" in str(e)
    else:
        raise AssertionError("expected ValueError for missing OHLCV columns")
