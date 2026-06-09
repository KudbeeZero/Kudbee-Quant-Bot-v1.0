"""Tests for the risk/leverage toolkit (kudbee_quant/risk.py)."""
from __future__ import annotations

import numpy as np

from kudbee_quant import risk


def _edge_R(n=2000, win=0.37, target=3.0, seed=0):
    rng = np.random.default_rng(seed)
    return np.where(rng.random(n) < win, target, -1.0)


def test_kelly_positive_for_edge_zero_for_none():
    R = _edge_R()
    assert risk.kelly_empirical(R) > 0
    assert risk.kelly_gaussian(R) > 0
    # a negative-edge series -> no Kelly bet
    assert risk.kelly_empirical(np.where(np.arange(100) % 2, 1.0, -2.0)) == 0.0


def test_kelly_gaussian_matches_mean_over_var():
    R = _edge_R()
    assert abs(risk.kelly_gaussian(R) - R.mean() / R.var()) < 1e-9


def test_lower_variance_raises_kelly():
    # same mean, lower variance -> larger safe fraction (the fast-fail payoff)
    hi = _edge_R(win=0.37, target=3.0)
    lo = hi * 0.85           # shrink every outcome 15% -> mean & std both down 15%,
    # so mean/var rises (var falls faster) -> kelly up. Construct a cleaner case:
    base = _edge_R(win=0.40, target=2.0)
    tighter = np.clip(base, -0.7, None)   # truncate the loss tail (smaller losses)
    assert risk.kelly_gaussian(tighter) >= risk.kelly_gaussian(base)


def test_risk_of_ruin_decreases_with_units():
    R = _edge_R()
    assert risk.risk_of_ruin_closed(R, 10) > risk.risk_of_ruin_closed(R, 30)


def test_montecarlo_ruin_in_range():
    R = _edge_R()
    p = risk.ror_montecarlo(R, 0.02, n_trades=300, n_sims=2000, ruin_dd=0.5)
    assert 0.0 <= p <= 1.0


def test_max_safe_leverage_drops_with_bigger_losses():
    rng = np.random.default_rng(1)
    small = np.abs(rng.normal(0.02, 0.005, 1000))   # ~2% adverse moves
    big = np.abs(rng.normal(0.05, 0.01, 1000))      # ~5% adverse moves
    lev_small = risk.max_safe_leverage(small, n_trades=100)
    lev_big = risk.max_safe_leverage(big, n_trades=100)
    assert lev_small > lev_big          # smaller losses -> higher safe leverage
    assert 0 < lev_big <= 50


def test_liq_distance_matches_known_points():
    assert abs(risk.liq_distance(20, mmr=0.0) - 0.05) < 1e-9    # 20x -> 5%
    assert abs(risk.liq_distance(40, mmr=0.0) - 0.025) < 1e-9   # 40x -> 2.5%


def test_summary_shape():
    R = _edge_R()
    adverse = np.abs(np.random.default_rng(2).normal(0.03, 0.01, R.size))
    s = risk.summary(R, adverse_moves=adverse, n_trades=300)
    assert {"kelly_full", "risk_per_trade_frac", "optimal_f", "max_safe_leverage"} <= set(s)
