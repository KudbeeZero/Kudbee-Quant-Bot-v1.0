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


def test_limit_retrace_entry_fills_at_pullback():
    # Long signal at bar 0 (close 100, ATR 1). Limit retrace 0.5 ATR -> 99.5.
    # Price dips to 99.5 (bar 1 low), fills at 99.5, then runs to target
    # 99.5 + 2*1 = 101.5 (bar 2). Outcome +2R from the limit fill.
    prices = [100, 100, 102, 102]
    df = _df_with_atr(prices, atr=1.0)
    df.loc[1, "low"] = 99.4      # reaches the 99.5 limit
    df.loc[2, "high"] = 101.6    # reaches target 101.5
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=2.0, max_bars=5,
                         fee_r=0.0, limit_retrace_atr=0.5, entry_window=4)
    assert r.n_trades == 1
    assert abs(r.trades[0] - 2.0) < 1e-9


def test_confirmation_filter_requires_reversal_candle():
    from kudbee_quant.backtest.bracket import _is_confirmation
    # Bullish hammer (long lower wick, bullish close) confirms a long.
    assert _is_confirmation(o=100, h=100.3, l=98, c=100.1, direction=1)
    # A bearish candle does not confirm a long.
    assert not _is_confirmation(o=100, h=100.2, l=99.5, c=99.6, direction=1)
    # Shooting star confirms a short; a bull candle does not.
    assert _is_confirmation(o=100, h=102, l=99.9, c=99.95, direction=-1)
    assert not _is_confirmation(o=100, h=100.5, l=99.9, c=100.4, direction=-1)


def test_limit_retrace_missed_when_no_pullback():
    # Price runs up without retracing to the limit -> signal missed, no trade.
    prices = [100, 101, 102, 103]
    df = _df_with_atr(prices, atr=1.0)
    df["low"] = df["close"] - 0.05  # never dips to the 99.5 limit
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=2.0, max_bars=5,
                         fee_r=0.0, limit_retrace_atr=0.5, entry_window=3)
    assert r.n_trades == 0


def test_short_side_target():
    # Short at 100, target 2R down = 98. Price falls to 97 -> +2R.
    prices = [100, 99, 98, 97, 97]
    df = _df_with_atr(prices)
    df.loc[2, "low"] = 98
    sig = pd.Series([-1, 0, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=2.0, max_bars=4, fee_r=0.0)
    assert r.trades[0] == 2.0


def test_tp1_tp2_full_run_blends_both_targets():
    # Long at 100, ATR 1. TP1 at +2R (102, half), TP2/target at +4R (104, half).
    # Price runs to 104 -> blended R = 0.5*2 + 0.5*4 = 3.0R.
    prices = [100, 100, 102, 104, 104]
    df = _df_with_atr(prices, atr=1.0)
    df.loc[2, "high"] = 102.0
    df.loc[3, "high"] = 104.0
    sig = pd.Series([1, 0, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=4.0, max_bars=4, fee_r=0.0,
                         tp1_r=2.0, tp1_frac=0.5, be_after_tp1=True)
    assert r.n_trades == 1
    assert abs(r.trades[0] - 3.0) < 1e-9


def test_tp1_then_breakeven_stop_banks_half():
    # Long at 100. TP1 +2R (102) fills banking 0.5*2=1R, stop -> breakeven (100).
    # Price then falls back through 100 before reaching TP2 -> remainder exits ~0R.
    # Blended R = 1.0 + 0.5*0 = 1.0R (the "free trade" outcome).
    prices = [100, 100, 102, 100, 99]
    df = _df_with_atr(prices, atr=1.0)
    df.loc[2, "high"] = 102.0
    df.loc[3, "low"] = 99.9       # dips back to breakeven (100) after TP1
    sig = pd.Series([1, 0, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=4.0, max_bars=4, fee_r=0.0,
                         tp1_r=2.0, tp1_frac=0.5, be_after_tp1=True)
    assert abs(r.trades[0] - 1.0) < 1e-9


def test_bracket_excursions_records_mfe_and_stop():
    from kudbee_quant.backtest.bracket import bracket_excursions
    # Long market entry at 100 (no retrace), ATR 1. Price runs to 102.5 (MFE 2.5R)
    # then drops through the 99 stop (MAE -1, stopped). Path highs/lows crafted.
    prices = [100, 101, 102.5, 98.5, 98]
    df = _df_with_atr(prices, atr=1.0)
    df.loc[2, "high"] = 102.5
    df.loc[3, "low"] = 98.5      # breaches the 99 stop
    sig = pd.Series([1, 0, 0, 0, 0], dtype=float)
    ex = bracket_excursions(df, sig, stop_atr=1.0, max_bars=4, limit_retrace_atr=None)
    assert len(ex) == 1
    assert abs(ex["mfe_r"].iloc[0] - 2.5) < 1e-9
    assert ex["stopped"].iloc[0] and ex["mae_r"].iloc[0] <= -1.0


def test_tp1_full_stop_before_tp1_is_minus_one():
    # Long at 100, stop at 99. Price drops to 98 before TP1 -> full -1R (no partial).
    prices = [100, 99.5, 98, 98]
    df = _df_with_atr(prices, atr=1.0)
    df.loc[2, "low"] = 98.0
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    r = bracket_backtest(df, sig, stop_atr=1.0, target_r=4.0, max_bars=3, fee_r=0.0,
                         tp1_r=2.0, tp1_frac=0.5, be_after_tp1=True)
    assert abs(r.trades[0] - (-1.0)) < 1e-9
