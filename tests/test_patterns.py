"""Double-top/bottom neckline-break + support/resistance tests (no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.scenarios.patterns import double_top_bottom_break, support_resistance


def _df(highs, lows, closes, atr=1.0):
    n = len(closes)
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": closes, "high": highs, "low": lows, "close": closes, "atr": atr})


def test_double_top_triggers_short_on_neckline_break():
    # Two equal tops (peaks at bars 3 and 9, confirmed +2 bars later) with a
    # neckline trough at bar 6, then a close below it -> short at the break bar.
    closes = [100, 103, 106, 110, 107, 103, 100, 103, 107, 110, 107, 103, 99, 97, 96]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    highs[3] = 112; highs[9] = 112            # two equal tops
    lows[6] = 99                              # neckline trough between them
    df = _df(highs, lows, closes, atr=1.0)
    sig = double_top_bottom_break(df, left=2, right=2, tol_atr=1.5, max_gap=30)
    assert (sig < 0).any()                    # a short was generated on the break


def test_support_resistance_exposes_levels():
    closes = [100, 102, 101, 99, 100, 103, 101, 98, 100, 104]
    highs = [c + 1 for c in closes]; lows = [c - 1 for c in closes]
    df = _df(highs, lows, closes, atr=1.0)
    sr = support_resistance(df, left=2, right=2)
    assert "resistance" in sr.columns and "support" in sr.columns
    assert "res_shelf" in sr.columns and "sup_shelf" in sr.columns
    # Once swings are confirmed, support should sit at or below resistance.
    tail = sr.dropna(subset=["resistance", "support"])
    assert (tail["support"] <= tail["resistance"]).all()


def test_no_signal_without_equal_swings():
    # Strictly trending up: no double top/bottom -> no pattern signal.
    closes = list(np.linspace(100, 130, 40))
    highs = [c + 0.5 for c in closes]; lows = [c - 0.5 for c in closes]
    df = _df(highs, lows, closes, atr=1.0)
    sig = double_top_bottom_break(df, left=3, right=3, tol_atr=0.2)
    assert (sig == 0).all()
