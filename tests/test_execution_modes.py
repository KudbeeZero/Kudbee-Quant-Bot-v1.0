"""Unit tests for the offline execution head-to-head (backtest/execution_modes.py).

Synthetic, deterministic frames so every entry price, exit type, and fee is
predictable. Guards the no-lookahead contract (market fills at T+1 OPEN, never the
signal close) and the per-leg fee model (taker in/out, maker on resting fills).
"""
from __future__ import annotations

import pandas as pd

from kudbee_quant.backtest.execution_modes import (
    MAKER_SIDE, TAKER_SIDE, adverse_selection, run_variant, summarize,
)


def _frame(rows):
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df["atr"] = 1.0
    return df


def test_market_fills_at_next_bar_open_not_signal_close():
    # Signal at t=0 close=100 (long). Next bar opens at 101 -> entry MUST be 101.
    # sd = 1.5*1 = 1.5 -> target = 101 + 4.5 = 105.5, stop = 99.5.
    # Bar 2 prints the target high.
    df = _frame([
        [100, 100, 100, 100],   # t0 signal bar
        [101, 101, 101, 101],   # t1 entry bar (open=101)
        [101, 106, 101, 105],   # t2 -> high 106 >= 105.5 target
        [105, 105, 105, 105],
    ])
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    out = run_variant(df, sig, mode="market", stop_atr=1.5, target_r=3.0, max_bars=24)
    assert len(out["trades"]) == 1
    tr = out["trades"][0]
    assert tr["entry_bar"] == 1                      # filled on T+1
    assert tr["exit_type"] == "target"
    assert tr["gross_r"] == 3.0
    # entry leg taker + exit leg maker (target rests as a limit), priced off entry=101, sd=1.5
    expected_cost = (TAKER_SIDE + MAKER_SIDE) * 101.0 / 1.5
    assert abs(tr["cost_r"] - expected_cost) < 1e-12
    assert abs(tr["net_r"] - (3.0 - expected_cost)) < 1e-12


def test_stop_exit_pays_taker_both_legs_on_market():
    # Market long, entry 100; sd=1.5 -> stop = 98.5. Price falls through it.
    df = _frame([
        [100, 100, 100, 100],
        [100, 100, 100, 100],   # entry bar, open=100
        [100, 100, 98, 98.4],   # low 98 <= 98.5 -> stop
        [98, 98, 98, 98],
    ])
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    tr = run_variant(df, sig, mode="market", stop_atr=1.5, target_r=3.0)["trades"][0]
    assert tr["exit_type"] == "stop"
    assert tr["gross_r"] == -1.0
    expected_cost = (TAKER_SIDE + TAKER_SIDE) * 100.0 / 1.5   # taker in, taker out
    assert abs(tr["cost_r"] - expected_cost) < 1e-12


def test_maker_retrace_cancels_when_no_pullback():
    # Long signal at t0=100, retrace limit = 100 - 0.25 = 99.75. Price never dips
    # to 99.75 within the window -> CANCELLED, no trade, recorded as an attempt.
    df = _frame([
        [100, 100, 100, 100],
        [101, 102, 100.5, 101.5],
        [101.5, 103, 101, 102.5],
        [102.5, 104, 102, 103.5],
    ])
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    out = run_variant(df, sig, mode="maker_retrace", retrace_atr=0.25, entry_window=6)
    assert out["trades"] == []
    assert len(out["attempts"]) == 1 and out["attempts"][0]["filled"] is False


def test_maker_retrace_fills_at_limit_with_maker_fee():
    # Retrace limit = 99.75; bar 1 dips to 99.7 -> fill at the LIMIT (99.75), maker in.
    df = _frame([
        [100, 100, 100, 100],
        [100, 100, 99.7, 99.9],   # low 99.7 <= 99.75 -> filled at 99.75
        [99.9, 105, 99.9, 104],   # target = 99.75 + 4.5 = 104.25? high 105 >= -> target
        [104, 104, 104, 104],
    ])
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    tr = run_variant(df, sig, mode="maker_retrace", retrace_atr=0.25, entry_window=6)["trades"][0]
    assert tr["entry_bar"] == 1
    assert tr["exit_type"] == "target"
    expected_cost = (MAKER_SIDE + MAKER_SIDE) * 99.75 / 1.5   # maker in, maker out (target)
    assert abs(tr["cost_r"] - expected_cost) < 1e-12


def test_adverse_selection_resolves_only_cancelled_signals():
    # One signal that the retrace cancels (no pullback) -> adverse_selection should
    # resolve exactly that one as a market entry at T+1 open.
    df = _frame([
        [100, 100, 100, 100],
        [101, 102, 101, 101.5],   # never dips to 99.75 -> maker cancels
        [101.5, 106, 101.5, 105],  # market entry @ open 101.5; target=101.5+4.5=106
        [105, 105, 105, 105],
    ])
    sig = pd.Series([1, 0, 0, 0], dtype=float)
    recs = adverse_selection(df, sig, retrace_atr=0.25, entry_window=6)
    assert len(recs) == 1
    assert recs[0]["exit_type"] == "target"


def test_summarize_basic():
    s = summarize([1.0, -1.0, 3.0, -1.0])
    assert s["n_trades"] == 4
    assert abs(s["win_rate"] - 0.5) < 1e-12
    assert abs(s["expectancy_r"] - 0.5) < 1e-12
    assert abs(s["total_r"] - 2.0) < 1e-12
    assert 0.0 <= s["bootstrap_p"] <= 1.0
