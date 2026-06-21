"""Unit tests for the shared resolver's path-dependent exits (resolver.py).

Hand-built bar paths make each exit's behaviour unambiguous. We also assert the
exits are OFF by default — with no exit params the resolver must reproduce the
original all-or-nothing stop/target/mark-to-close result exactly.
"""
from __future__ import annotations

import numpy as np

from kudbee_quant.backtest.resolver import resolve_bracket

# A long trade: entry 100, sd=1.0 (so 1R = 1.0 in price), stop 99.


def _long(high, low, close, **kw):
    return resolve_bracket(1.0, 100.0, 99.0, 100.0 + 3.0, 1.0, 3.0,
                           high, low, close, **kw)


def test_exits_off_matches_plain_stop_target():
    # target (103) hit on bar 1 -> +3R, exactly as the original logic.
    out = _long([101, 103.5, 104], [100, 101, 102], [100.5, 103.2, 103.5])
    assert out.exited and out.outcome_r == 3.0 and out.exit_offset == 1


def test_exits_off_marks_to_close_when_neither_hit():
    out = _long([100.5, 100.6, 100.7], [99.5, 99.6, 99.7], [100.2, 100.3, 100.4])
    assert out.exited and out.exit_offset == 2
    assert abs(out.outcome_r - (100.4 - 100.0) / 1.0) < 1e-9


def test_trailing_stop_locks_profit():
    # Far target (win_r huge) so only the trail can exit. Price runs to 105 then
    # falls; chandelier (2 ATR, atr=1) trails to 103 and stops the pullback at +3R.
    out = resolve_bracket(1.0, 100.0, 99.0, 1000.0, 1.0, 100.0,
                          [102, 105, 104], [100, 102, 101], [101, 104, 102],
                          trailing_atr=2.0, atr_at_entry=1.0)
    assert out.exited and out.exit_offset == 2
    assert abs(out.outcome_r - 3.0) < 1e-9   # stopped at the trailed 103


def test_mae_giveup_exits_early():
    # Goes adverse fast (mae <= -0.5) and never shows >= 0.5R favorable -> give up
    # at bar 1's close (-0.3R), instead of waiting for the -1R stop.
    out = _long([100.2, 99.8, 99.9], [99.4, 99.5, 99.6], [99.7, 99.7, 99.8],
                mae_giveup=(2, 0.5, 0.5))
    assert out.exited and out.exit_offset == 1
    assert abs(out.outcome_r - (-0.3)) < 1e-9


def test_time_decay_target_harvests_smaller_win():
    # Target decays 3R->1R over 4 bars. By bar 2 the decayed target is 1.5R (101.5);
    # price tags 101.6 there -> banks +1.5R rather than waiting for the full 3R.
    out = _long([100.5, 101.0, 101.6], [100.0, 100.0, 101.0], [100.3, 100.8, 101.4],
                time_decay=(4, 1.0))
    assert out.exited and out.exit_offset == 2
    assert abs(out.outcome_r - 1.5) < 1e-9


def test_tp2_three_leg_blends_all_tranches():
    # Long entry 100, sd=1. Three-leg: 75% @ TP1=1.5R (101.5), 10% @ TP2=2.5R (102.5),
    # 15% @ target=3R (103). A path that tags 101.5, then 102.5, then 103 on three
    # separate bars banks 0.75*1.5 + 0.10*2.5 + 0.15*3.0 = 1.125+0.25+0.45 = 1.825R.
    out = resolve_bracket(1.0, 100.0, 99.0, 103.0, 1.0, 3.0,
                          [101.6, 102.6, 103.1], [100.5, 101.5, 102.5],
                          [101.5, 102.5, 103.0],
                          tp1=101.5, tp1_r=1.5, tp1_frac=0.75,
                          tp2=102.5, tp2_r=2.5, tp2_frac=0.10, be_after_tp1=True)
    assert out.exited and out.exit_offset == 2
    assert abs(out.outcome_r - 1.825) < 1e-9


def test_tp2_stop_after_tp1_banks_partial_then_breakeven():
    # Bank 75% @ TP1 (1.5R) on bar 0, then price collapses to the breakeven stop
    # (100) on bar 1. Remaining 25% exits at ~0R -> total = 0.75*1.5 + 0.25*0 = 1.125R.
    out = resolve_bracket(1.0, 100.0, 99.0, 103.0, 1.0, 3.0,
                          [101.6, 100.2, 100.3], [100.5, 99.8, 99.9],
                          [101.5, 100.0, 100.1],
                          tp1=101.5, tp1_r=1.5, tp1_frac=0.75,
                          tp2=102.5, tp2_r=2.5, tp2_frac=0.10, be_after_tp1=True)
    assert out.exited and out.exit_offset == 1
    assert abs(out.outcome_r - 1.125) < 1e-9


def test_tp2_off_matches_single_leg_tp1():
    # With tp2 None the three-leg path must equal the original single-TP1 result:
    # 50% @ 1.5R then 50% @ 3R target -> 0.5*1.5 + 0.5*3.0 = 2.25R.
    path = ([101.6, 103.1], [100.5, 102.5], [101.5, 103.0])
    base = resolve_bracket(1.0, 100.0, 99.0, 103.0, 1.0, 3.0, *path,
                           tp1=101.5, tp1_r=1.5, tp1_frac=0.5, be_after_tp1=True)
    assert abs(base.outcome_r - 2.25) < 1e-9


# --- Breakeven-only exit: tp1_r=1.0, tp1_frac=0.0, be_after_tp1=True ----------
# This is exactly what the hourly paper bot arms via `--tp1-r 1.0 --tp1-frac 0.0`:
# bank NOTHING at +1R, keep full size, move the stop to breakeven, ride to +3R.
# tp1 = 1R above entry = 101.0 (sd=1.0). These three cases pin the behaviour the
# bot relies on — most importantly (b), the -1R -> ~0R leak being plugged.


def test_be_only_runner_rides_full_size_to_target():
    # (a) Runner — tags +1R (101) on bar 0, banks nothing, then runs to the +3R
    # target (103) on bar 1 with full size -> 0 + 1.0*3.0 = +3.0R.
    out = _long([101.5, 103.5], [100.5, 101.0], [101.2, 103.2],
                tp1=101.0, tp1_r=1.0, tp1_frac=0.0, be_after_tp1=True)
    assert out.exited and out.exit_offset == 1
    assert abs(out.outcome_r - 3.0) < 1e-9
    assert out.tp1_offset == 0


def test_be_only_breakeven_save_exits_at_zero_not_minus_one():
    # (b) THE LEAK BEING PLUGGED. Tags +1R (101) on bar 0 -> stop moves to
    # breakeven (100). Bar 1 reverses into that breakeven stop. Old behaviour
    # (no tp1) would have ridden to the original -1R stop; here the full size
    # exits at ~0R -> 0 + 1.0*0.0 = 0.0R, NOT -1.0R.
    out = _long([101.5, 100.2], [100.5, 99.9], [101.2, 100.0],
                tp1=101.0, tp1_r=1.0, tp1_frac=0.0, be_after_tp1=True)
    assert out.exited and out.exit_offset == 1
    assert abs(out.outcome_r - 0.0) < 1e-9
    assert out.outcome_r > -1.0 + 1e-9   # explicitly: NOT a full -1R stop


def test_be_only_clean_stop_takes_full_minus_one_r():
    # (c) Clean stop — never reaches +1R (high stays < 101), hits the -1R stop
    # (99) on bar 0. Full size, nothing banked, BE never armed -> -1.0R.
    out = _long([100.5, 100.6], [98.9, 99.5], [99.5, 100.0],
                tp1=101.0, tp1_r=1.0, tp1_frac=0.0, be_after_tp1=True)
    assert out.exited and out.exit_offset == 0
    assert abs(out.outcome_r - (-1.0)) < 1e-9
    assert out.tp1_offset is None   # TP1 never banked


def test_random_equivalence_no_exits():
    # Fuzz: resolver with no exits == a plain stop-then-target reference walk.
    rng = np.random.default_rng(0)
    for _ in range(200):
        n = rng.integers(3, 20)
        base = 100 + rng.normal(0, 1, n).cumsum()
        high = base + np.abs(rng.normal(0, 0.5, n))
        low = base - np.abs(rng.normal(0, 0.5, n))
        close = base
        out = _long(list(high), list(low), list(close))
        # reference
        ref_r, ref_j = None, None
        for j in range(n):
            if low[j] <= 99.0:
                ref_r, ref_j = -1.0, j; break
            if high[j] >= 103.0:
                ref_r, ref_j = 3.0, j; break
        if ref_r is None:
            ref_r, ref_j = (close[n - 1] - 100.0) / 1.0, n - 1
        assert out.exit_offset == ref_j
        assert abs(out.outcome_r - ref_r) < 1e-9
