"""Regression tests for the leverage forward-test scripts (Tier-2 fills + shadow).

Covers three bugs found in code review:
  #1  tier2 `_is_filled` must not double-count a 'cancelled' row that carries a
      stale `filled_at` (status is authoritative).
  #2  `hold_days_of` must treat a +1R touch on bar 0 (bars_to==0) as a real fast
      touch, not fall through to the full path length (falsy-zero bug).
  #3  the shadow KILL gate must not fire on a couple of liquidations at the n-gate
      (point estimate); it requires the liq rate to be 95%-CI-significantly > 1%.
"""
import os
import sys
import types

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import leverage_be_study as study      # noqa: E402
import leverage_be_shadow as shadow     # noqa: E402
import leverage_be_tier2_fills as t2    # noqa: E402


def _pred(status, filled_at=None):
    return types.SimpleNamespace(status=status, filled_at=filled_at)


# ---- #1: cancelled-with-stale-filled_at counts ONCE, as unfilled ----------
def test_cancelled_with_stale_filled_at_not_double_counted():
    preds = [
        _pred("cancelled", "2026-01-01T00:00:00"),  # stale filled_at — still UNFILLED
        _pred("hit", "2026-01-01T01:00:00"),
        _pred("miss", None),                         # resolved w/o filled_at — filled
        _pred("open", "2026-01-01T02:00:00"),
        _pred("pending", None),
    ]
    f, c, pend = t2._segment(preds)
    assert f == 3, "hit+miss+open are the filled entries"
    assert c == 1, "the cancelled row counts once, as unfilled"
    assert pend == 1
    assert f + c + pend == len(preds), "no row double-counted"
    # fill rate = 3 / (3+1) = 0.75, not 4/5
    assert t2._rate(f, c) == 0.75


def test_is_filled_status_authoritative():
    assert t2._is_filled(_pred("cancelled", "2026-01-01T00:00:00")) is False
    assert t2._is_filled(_pred("hit", None)) is True
    assert t2._is_filled(_pred("pending", "2026-01-01T00:00:00")) is False


# ---- #2: hold_days_of treats bar-0 +1R touch as fast, not full-length -------
def _tp(timeframe, bars_to_1R, n_bars):
    tp = study.TradePath(p=types.SimpleNamespace(timeframe=timeframe),
                         rhi=np.zeros(n_bars), rlo=np.zeros(n_bars), rclose=np.zeros(n_bars),
                         stop_pct=1.0, target_r=3.0)
    tp.bars_to = {} if bars_to_1R is None else {"1.00": bars_to_1R}
    return tp


def test_hold_days_zero_touch_is_fast_not_full_length():
    # +1R on bar 0 → ~0 days, NOT len(rhi) bars
    assert study.hold_days_of(_tp("1h", 0, 48)) == 0.0
    # +1R after 12 hourly bars → 12/24 = 0.5 days
    assert study.hold_days_of(_tp("1h", 12, 48)) == 0.5
    # never reached +1R → falls back to full path length (48 bars * 1h)
    assert study.hold_days_of(_tp("1h", None, 48)) == 48 / 24.0


# ---- #3: liquidation KILL needs CI-significance over the 1% baseline --------
def _ev(n, n_liq, rule_lo=0.05, delta_lo=0.1, worst_roll=-0.01):
    return {"n": n, "n_liquidated_at_cap": n_liq, "pct_liquidated": n_liq / n,
            "rule_net_ci": [rule_lo, 0.2], "delta_ci": [delta_lo, 0.5],
            "worst_rolling100_net": worst_roll}


def test_liq_kill_does_not_fire_on_baseline_noise():
    # 3 liquidations in 150 (2%) — within noise of the ~1% baseline → NOT a kill
    v, _ = shadow.verdict(_ev(150, 3))
    assert v == "PASS"


def test_liq_kill_fires_when_significantly_above_baseline():
    # 10 liquidations in 150 (6.7%) — 95% CI low clears 1% → KILL
    v, reasons = shadow.verdict(_ev(150, 10))
    assert v == "KILL"
    assert any("liq" in r for r in reasons)


def test_below_gate_is_inconclusive():
    v, _ = shadow.verdict(_ev(50, 0))
    assert v == "INCONCLUSIVE"
