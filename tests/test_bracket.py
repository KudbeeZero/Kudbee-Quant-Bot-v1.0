"""Tests for the bracket (stop/target) backtester — measures R, not win-rate."""
import numpy as np
import pandas as pd

from kudbee_quant.backtest.bracket import bracket_backtest


def _df_with_atr(prices, atr=1.0):
    n = len(prices)
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": prices, "high": [p + 0.1 for p in prices], "low": [p - 0.1 for p in prices],
        "close": prices, "atr": atr,
    })


def test_target_hit_gives_positive_r():
    # Long entry at 100, ATR=1, target 2R=102. Price rises to 103 -> +2R.
    prices = [100, 100, 101, 102, 103, 103]
    df = _df_with_atr(prices)
    df.loc[4, "high"] = 103  # ensure target 102 is reached by bar 4
    sig = pd.Series([1, 0, 0, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=2.0, max_bars=5, fee_r=0.0)
    assert r.n_trades == 1
    assert r.trades[0] == 2.0


def test_stop_hit_gives_minus_one_r():
    # Long at 100, stop at 99. Price drops to 98 -> -1R.
    prices = [100, 99.5, 98, 98, 98]
    df = _df_with_atr(prices)
    df.loc[2, "low"] = 98
    sig = pd.Series([1, 0, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=2.0, max_bars=4, fee_r=0.0)
    assert r.trades[0] == -1.0


def test_expectancy_and_profit_factor():
    # Two trades: one +2R, one -1R -> expectancy +0.5R, PF = 2.0.
    prices = [100, 102.5, 100, 100, 100, 99, 98, 98]
    df = _df_with_atr(prices)
    df.loc[1, "high"] = 102.5      # first long hits +2R target (102)
    df.loc[6, "low"] = 98          # second long hits stop (-1R)
    sig = pd.Series([1, 0, 0, 0, 1, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=2.0, max_bars=3, fee_r=0.0)
    assert r.n_trades == 2
    assert np.isclose(r.expectancy_r, 0.5)
    assert np.isclose(r.profit_factor, 2.0)
    assert np.isclose(r.win_rate, 0.5)


def test_no_overlap_skips_entries_during_trade():
    prices = [100, 100, 100, 102, 100, 100]
    df = _df_with_atr(prices)
    df.loc[3, "high"] = 102
    sig = pd.Series([1, 1, 1, 0, 0, 0], dtype=float)  # 3 triggers, but 1 trade at a time
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=2.0, max_bars=5, fee_r=0.0)
    assert r.n_trades == 1


def test_fee_pct_is_timeframe_aware():
    # Entry 100, ATR=1 -> stop distance 1 (1% of price). A 0.5% round-trip cost
    # = 0.5R. Target +2R hit -> net 2 - 0.5 = 1.5R.
    prices = [100, 102.5, 103, 103]
    df = _df_with_atr(prices, atr=1.0)
    df.loc[1, "high"] = 102.5
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=2.0, max_bars=3, fee_pct=0.005)
    assert abs(r.trades[0] - 1.5) < 1e-9
    # Tighter stop (smaller ATR) -> same % cost is MORE R: ATR=0.5 -> stop 0.5%
    # -> cost 1.0R -> net 2 - 1 = 1.0R.
    df2 = _df_with_atr(prices, atr=0.5)
    df2.loc[1, "high"] = 101.0  # target = 100 + 2*0.5 = 101
    r2 = bracket_backtest(df2, sig, stop_atr=1.0, target_r=2.0, max_bars=3, fee_pct=0.005)
    assert abs(r2.trades[0] - 1.0) < 1e-9


def test_short_side_target():
    # Short at 100, target 2R down = 98. Price falls to 97 -> +2R.
    prices = [100, 99, 98, 97, 97]
    df = _df_with_atr(prices)
    df.loc[2, "low"] = 98
    sig = pd.Series([-1, 0, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=2.0, max_bars=4, fee_r=0.0)
    assert r.trades[0] == 2.0
