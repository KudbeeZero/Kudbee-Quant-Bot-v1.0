"""Pin the v_vwap vote to the §41-validated MOMENTUM sign (MEMORY §74/§75).

The 2026-06-16 rotation flip (§44) was OOS-refuted by the pre-registered §41
gap investigation (PR #129) and reverted with owner sign-off on 2026-07-01.
This test makes any future re-flip a deliberate, test-breaking act rather than
a silent drift — re-flipping requires fresh OOS evidence per §74.
"""
from __future__ import annotations

import pandas as pd

from kudbee_quant.confluence.stack import factor_votes


def test_v_vwap_votes_momentum_sign():
    df = pd.DataFrame({
        "close": [101.0, 99.0, 100.0],
        "vwap":  [100.0, 100.0, 100.0],
    })
    votes = factor_votes(df)
    # Momentum sign: above VWAP -> long (+1), below -> short (-1), at -> 0.
    assert votes["v_vwap"].tolist() == [1.0, -1.0, 0.0]


def test_v_vwap_matches_pine_indicator_sign():
    # pinescript/kudbee_confluence.pine line ~88: vVwap = sign(close - vwap).
    # The Python engine and the TradingView indicator must agree.
    df = pd.DataFrame({"close": [105.0], "vwap": [100.0]})
    assert factor_votes(df)["v_vwap"].iloc[0] == 1.0
