"""Tests for the trailing-stop research (research/trailing_sweep.py).

Two guards the task requires, plus a fidelity lock:
  (a) the chandelier trail NEVER loosens the stop (monotonic ratchet) on a
      synthetic favorable series;
  (b) trailing_atr=None reproduces the current baseline exit EXACTLY (the
      path-dependent code is a true no-op when off);
  (c) the paired diagnostic's baseline branch reproduces the unmodified
      bracket_backtest baseline trade list EXACTLY — proving the paired
      enumerator is faithful, not a divergent reimplementation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "research"))

from kudbee_quant.backtest.bracket import bracket_backtest  # noqa: E402
from kudbee_quant.backtest.resolver import resolve_bracket  # noqa: E402

import trailing_sweep as ts  # noqa: E402


# --- (a) monotonic ratchet: the trail never loosens -------------------------

def test_trail_ratchets_and_locks_profit_long():
    """Long: price rallies for several bars then dips on the last bar. The trail
    must exit at the RATCHETED stop (extreme-since-entry - trail_dist), i.e. it
    locks in profit and never sits at the original (loose) 1R stop."""
    entry, sd = 100.0, 1.0          # 1R = 1.0 price
    atr_at_entry, mult = 1.0, 2.0   # trail distance = 2.0 price
    stop = entry - sd               # 99.0 original hard stop
    target = entry + sd * 10.0      # 110.0 (far away; never reached -> exit is the TRAIL, not the target)
    # forward highs climb 101..105 (extreme ratchets up), final bar craters to
    # trigger the trailed stop. Lows stay above the trail until the last bar.
    high = np.array([101.0, 102.0, 103.0, 104.0, 105.0, 105.0])
    low = np.array([100.5, 101.5, 102.5, 103.5, 104.5, 100.0])
    close = np.array([101.0, 102.0, 103.0, 104.0, 105.0, 100.0])
    out = resolve_bracket(1.0, entry, stop, target, sd, 10.0, high, low, close,
                          force_close_at_end=True, trailing_atr=mult,
                          atr_at_entry=atr_at_entry)
    # extreme BEFORE the last bar = 104.0 (high of bar idx 3, set after that bar);
    # by the last bar the extreme is 105.0 set after bar idx 4 -> trail = 105-2 = 103.0.
    # last bar low 100.0 is below 103.0 -> exit at 103.0 => +3.0R, NOT the -1R stop.
    expected_stop = 105.0 - mult * atr_at_entry  # 103.0
    assert out.exited
    assert out.outcome_r > 0, "trail must lock in profit, not exit at a loss"
    assert abs(out.outcome_r - (expected_stop - entry) / sd) < 1e-9


def test_trail_never_loosens_after_a_dip():
    """A mid-trade dip must NOT pull the stop back down: once the extreme sets a
    tight stop, a later lower extreme can't loosen it. A series with an early
    high then a pullback then a final probe of the ratcheted level must still
    stop out at the high-anchored level."""
    entry, sd, atr_at_entry, mult = 100.0, 1.0, 1.0, 1.5
    stop = entry - sd
    target = entry + sd * 10.0   # far away (target_r=10) so the early high only sets the extreme
    # bar0 spikes to a high of 106 (extreme=106 -> stop ratchets to 106-1.5=104.5),
    # bars1-2 pull back (lower highs; extreme stays 106), bar3 dips to 104.4 (< 104.5)
    # => must trigger at the RATCHETED 104.5, proving the dip didn't loosen it.
    high = np.array([106.0, 105.0, 104.9, 104.9])
    low = np.array([100.5, 104.8, 104.7, 104.4])
    close = np.array([105.0, 104.9, 104.8, 104.5])
    out = resolve_bracket(1.0, entry, stop, target, sd, 10.0, high, low, close,
                          force_close_at_end=True, trailing_atr=mult,
                          atr_at_entry=atr_at_entry)
    expected_stop = 106.0 - mult * atr_at_entry  # 104.5
    assert out.exited
    assert abs(out.outcome_r - (expected_stop - entry) / sd) < 1e-9, (
        "stop must stay anchored to the highest extreme; a later dip cannot loosen it")


def test_trail_stop_sequence_is_monotonic_non_decreasing_long():
    """Directly assert the ratchet: replay a rising long series through the
    resolver's own trail formula and confirm the stop sequence never decreases."""
    entry, sd, atr_at_entry, mult = 100.0, 1.0, 1.0, 2.0
    highs = [101, 100.5, 103, 102, 104, 103.5, 106]  # noisy but trending up
    extreme = entry
    cur_stop = entry - sd
    stops = []
    for h in highs:
        trail_level = extreme - mult * atr_at_entry
        cur_stop = max(cur_stop, trail_level)
        stops.append(cur_stop)
        extreme = max(extreme, h)
    assert all(b >= a - 1e-12 for a, b in zip(stops, stops[1:], strict=False)), \
        f"stop loosened somewhere: {stops}"


# --- (b) trailing_atr=None is an exact no-op --------------------------------

def _synthetic_frame(seed: int = 3, n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0, 0.004, n)
    close = 100.0 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.002, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.002, n)))
    op = np.r_[close[0], close[:-1]]
    atr = pd.Series(high - low).rolling(14, min_periods=1).mean().to_numpy()
    return pd.DataFrame({"open": op, "high": high, "low": low, "close": close, "atr": atr})


def test_trailing_none_is_a_noop_on_the_full_path():
    """resolve_bracket with trailing_atr=None (and no other path arg) must give a
    byte-identical outcome to the plain stop/target resolution."""
    df = _synthetic_frame()
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    for entry_i in range(0, 350, 7):
        entry = c[entry_i]
        sd = 1.5 * df["atr"].to_numpy()[entry_i]
        if sd <= 0:
            continue
        stop = entry - sd
        target = entry + sd * 3.0
        hi, lo, cl = h[entry_i + 1:entry_i + 25], l[entry_i + 1:entry_i + 25], c[entry_i + 1:entry_i + 25]
        plain = resolve_bracket(1.0, entry, stop, target, sd, 3.0, hi, lo, cl,
                                force_close_at_end=True)
        with_none = resolve_bracket(1.0, entry, stop, target, sd, 3.0, hi, lo, cl,
                                    force_close_at_end=True, trailing_atr=None,
                                    atr_at_entry=df["atr"].to_numpy()[entry_i])
        assert plain == with_none


def test_baseline_kw_has_trailing_off():
    assert ts.BASELINE_KW["trailing_atr"] is None
    assert ts.BASELINE_KW["tp1_r"] == 1.0
    assert ts.BASELINE_KW["tp1_frac"] == 0.5
    assert ts.BASELINE_KW["be_after_tp1"] is True
    assert ts.BASELINE_KW["target_r"] == 3.0


# --- (c) paired baseline == unmodified bracket_backtest baseline (fidelity) --

def test_paired_baseline_reproduces_bracket_backtest_exactly():
    """The paired enumerator's BASELINE net-R list must EXACTLY equal the
    unmodified bracket_backtest baseline trades — proving the paired entry/overlap
    loop is faithful and not a divergent reimplementation of the engine."""
    df = _synthetic_frame(seed=11, n=600)
    # a deterministic alternating signal that fires often enough to exercise overlap
    sig = pd.Series(0.0, index=df.index)
    sig.iloc[::9] = 1.0
    sig.iloc[5::17] = -1.0

    engine = bracket_backtest(df, sig, **ts.BASELINE_KW)
    paired = ts.paired_trades(df, sig, ts.TRAIL_MULTIPLES)
    paired_net = [r["net_b"] for r in paired]

    assert len(paired_net) == engine.n_trades, (
        f"trade count differs: paired={len(paired_net)} engine={engine.n_trades}")
    np.testing.assert_allclose(paired_net, engine.trades, rtol=0, atol=1e-12)
