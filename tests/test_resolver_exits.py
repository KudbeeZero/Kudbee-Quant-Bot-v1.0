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
