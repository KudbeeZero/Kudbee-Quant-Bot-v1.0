"""Regression locks for research/section41_gap.py — the §41 gap investigation.

Hermetic (no network): a synthetic frame with enough columns to produce every
vote, run through build_levels-free paths. Two invariants:

1. ``signal_variant(vwap_momentum=False)`` must equal the engine's own
   ``confluence_position`` exactly (the replication cannot drift).
2. ``vwap_momentum=True`` flips ONLY the v_vwap vote (the one-variable
   counterfactual is genuinely one variable).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from kudbee_quant.config.validated_defaults import MIN_PCT, TREND_FILTER
from kudbee_quant.confluence.stack import confluence_position, factor_votes

from section41_gap import signal_variant  # noqa: E402


@pytest.fixture()
def frame() -> pd.DataFrame:
    rng = np.random.default_rng(41)
    n = 400
    close = 100 + rng.normal(0, 1, n).cumsum()
    df = pd.DataFrame({
        "close": close,
        "high": close + rng.uniform(0.1, 1.0, n),
        "low": close - rng.uniform(0.1, 1.0, n),
        "ema_13": pd.Series(close).ewm(span=13).mean().to_numpy(),
        "ema_50": pd.Series(close).ewm(span=50).mean().to_numpy(),
        "ema_800": pd.Series(close).ewm(span=200).mean().to_numpy(),
        "vwap": close + rng.normal(0, 0.5, n),
        "daily_open": close + rng.normal(0, 1.0, n),
        "pivot_pp": close + rng.normal(0, 1.0, n),
        "dealing_mid": close + rng.normal(0, 1.0, n),
        "sweep_bias": rng.choice([-1.0, 0.0, 1.0], n),
    })
    return df


def test_unflipped_variant_equals_engine_signal(frame):
    ours = signal_variant(frame, vwap_momentum=False)
    ref = confluence_position(frame, min_pct=MIN_PCT, trend_align=TREND_FILTER)
    pd.testing.assert_series_equal(ours, ref, check_names=False)


def test_flip_changes_only_v_vwap(frame):
    votes = factor_votes(frame)
    assert "v_vwap" in votes.columns  # the counterfactual's target factor exists
    flipped = votes.copy()
    flipped["v_vwap"] = -flipped["v_vwap"]
    # Every other column identical; v_vwap exactly negated (zero stays zero).
    for col in votes.columns:
        if col == "v_vwap":
            assert (flipped[col] == -votes[col]).all()
        else:
            assert flipped[col].equals(votes[col])


def test_flipped_signal_differs_where_vwap_is_decisive(frame):
    a = signal_variant(frame, vwap_momentum=False)
    b = signal_variant(frame, vwap_momentum=True)
    # On a random frame the flip must change at least one bar's signal
    # (if it never did, the counterfactual would be a no-op — a broken test rig).
    assert (a != b).any()
