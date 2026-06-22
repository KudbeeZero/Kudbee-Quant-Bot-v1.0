"""Unit tests for the volume-universe backtest's RECONCILED verdict logic.

No network — pure decision function. The whole point of the study is that a
marginally-positive pooled R must NOT be enough on its own; the significance
harness has to agree before we'd even paper-trade the wider universe."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from validate_volume_universe import reconcile_verdict  # noqa: E402


def test_paper_only_when_both_agree():
    # tail beats core OOS AND harness robust -> PAPER (tagged experiment)
    assert reconcile_verdict(-0.01, 0.04, tail_n=1000, core_n=300,
                             harness_robust=True) == "PAPER"


def test_positive_pooled_but_harness_rejects_is_hold():
    # the real result of this study: +0.037R tail vs -0.007R core, harness NOT robust
    assert reconcile_verdict(-0.0072, 0.0373, tail_n=1087, core_n=368,
                             harness_robust=False) == "HOLD"


def test_negative_tail_is_reject_regardless_of_harness():
    assert reconcile_verdict(-0.01, -0.05, tail_n=900, core_n=300,
                             harness_robust=True) == "REJECT"


def test_tail_below_core_is_reject():
    # tail positive but worse than core -> not additive -> REJECT
    assert reconcile_verdict(0.05, 0.02, tail_n=900, core_n=300,
                             harness_robust=True) == "REJECT"


def test_empty_samples_reject():
    assert reconcile_verdict(0.0, 0.0, tail_n=0, core_n=0, harness_robust=True) == "REJECT"


def test_expanded_candidate_pool_supports_top_40():
    # the pool must be wide enough to actually answer "top 30-40"
    from kudbee_quant.universe import CRYPTO_CANDIDATES, TOP_10_CRYPTO
    assert len(CRYPTO_CANDIDATES) >= 40
    # the validated top-10 must still be inside the candidate pool
    assert set(TOP_10_CRYPTO) <= set(CRYPTO_CANDIDATES)
    # no duplicates
    assert len(CRYPTO_CANDIDATES) == len(set(CRYPTO_CANDIDATES))
