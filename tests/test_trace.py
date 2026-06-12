"""Tests for the factor trace / sandbox / replay layer (no network).

The critical guarantee: the trace NEVER forks the vote logic — its votes must
equal factor_votes() output bar-for-bar, factor-for-factor.
"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from kudbee_quant.confluence import confluence_score, factor_votes
from kudbee_quant.confluence.trace import (FACTOR_KEYS, FACTOR_SPECS,
                                           apply_ema_overrides, factor_trace,
                                           sandbox_score)
from kudbee_quant.journal import Prediction, TradeJournal
from kudbee_quant.levels import build_levels


def _ohlcv(n=900, seed=11):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0002, 0.011, n)
    close = 1000 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
        "open": close, "high": high, "low": low, "close": close,
        "volume": rng.lognormal(5, 0.6, n),
    })


@pytest.fixture(scope="module")
def levels():
    return build_levels(_ohlcv())


def test_trace_votes_match_factor_votes_exactly(levels):
    """Parity: the trace decorates factor_votes, it never recomputes votes."""
    votes = factor_votes(levels)
    scored = confluence_score(levels)
    rows = factor_trace(levels, bars=len(levels))
    assert len(rows) == len(levels)
    for i, row in zip(levels.index, rows):
        for f in row["factors"]:
            if f["vote"] is not None:
                assert f["vote"] == int(votes.at[i, f["key"]]), (i, f["key"])
        assert row["n_factors"] == int(scored.at[i, "n_factors"])
        assert row["net_score"] == int(scored.at[i, "net_score"])
        assert abs(row["confluence_pct"] - float(scored.at[i, "confluence_pct"])) < 1e-12


def test_trace_has_all_factors_ordered_with_details(levels):
    row = factor_trace(levels, bars=1)[0]
    assert [f["key"] for f in row["factors"]] == list(FACTOR_KEYS)
    assert len(FACTOR_SPECS) == 10
    for f in row["factors"]:
        assert f["detail"], f["key"]
        assert f["label"]
        assert f["group"] in ("trend", "level", "smart_money")
    # Detail strings are JSON-safe plain data; values carry no numpy types.
    for f in row["factors"]:
        for v in f["values"].values():
            assert v is None or isinstance(v, (int, float, str))


def test_trace_missing_factor_reported_unavailable(levels):
    df = levels.drop(columns=["vwap"])
    row = factor_trace(df, bars=1)[0]
    vwap = next(f for f in row["factors"] if f["key"] == "v_vwap")
    assert vwap["vote"] is None
    # n_factors shrinks exactly like confluence_score's present-column count.
    assert row["n_factors"] == factor_votes(df).shape[1] == 9


def test_apply_ema_overrides_bounds_and_cloud(levels):
    with pytest.raises(ValueError):
        apply_ema_overrides(levels, {"ema_50": 1})
    with pytest.raises(ValueError):
        apply_ema_overrides(levels, {"ema_50": 2001})
    with pytest.raises(ValueError):
        apply_ema_overrides(levels, {"ema_999": 50})
    # Identity spans reproduce the builder's EMAs (same formula).
    same = apply_ema_overrides(levels, {"ema_13": 13, "ema_50": 50, "ema_800": 800})
    for col in ("ema_13", "ema_50", "ema_800"):
        assert np.allclose(same[col], levels[col], equal_nan=True)
    assert (same["ema_cloud_pos"] == levels["ema_cloud_pos"]).all()
    # Changed spans actually move the EMAs AND rebuild the cloud position.
    moved = apply_ema_overrides(levels, {"ema_13": 5, "ema_50": 200})
    assert not np.allclose(moved["ema_13"], levels["ema_13"])
    assert (moved["ema_cloud_pos"] != levels["ema_cloud_pos"]).any()


def test_sandbox_subset_changes_denominator(levels):
    out = sandbox_score(levels, enabled=["v_emastack", "v_vwap"], bars=3)
    assert out["unvalidated"] is True
    last = out["bars"][-1]
    assert last["n_factors"] == 2
    assert [f["key"] for f in last["factors"]] == ["v_emastack", "v_vwap"]
    assert 0.0 <= last["confluence_pct"] <= 1.0
    assert out["gate"]["min_pct"] == 0.5
    assert isinstance(out["gate"]["passed"], bool)


def test_sandbox_rejects_bad_input(levels):
    with pytest.raises(ValueError):
        sandbox_score(levels, enabled=[])
    with pytest.raises(ValueError):
        sandbox_score(levels, enabled=["v_nope"])
    with pytest.raises(ValueError):
        sandbox_score(levels, ema_spans={"ema_50": 0})


def test_sandbox_does_not_mutate_input(levels):
    before = levels.copy()
    sandbox_score(levels, ema_spans={"ema_50": 100}, enabled=["v_emastack"], bars=2)
    pd.testing.assert_frame_equal(levels, before)


# --- replay (fake client + tmp journal; journal must stay untouched) ----------


class _FakeClient:
    def __init__(self, prices):
        self.prices = prices

    def klines(self, symbol, interval="1h", limit=1000):
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        n = len(self.prices)
        ts = pd.date_range(now - timedelta(hours=n - 1), periods=n, freq="h", tz="UTC")
        c = pd.Series(self.prices, dtype=float)
        return pd.DataFrame({"timestamp": ts, "open": c, "high": c + 0.5,
                             "low": c - 0.5, "close": c, "volume": 1.0})


def _replay_fixture(tmp_path):
    from kudbee_quant.replay import replay_trade

    rng = np.random.default_rng(3)
    prices = list(100 + np.cumsum(rng.normal(0, 0.3, 700)))
    j = TradeJournal(path=tmp_path / "j.json", client=_FakeClient(prices))
    now = datetime.now(timezone.utc)
    p = Prediction(symbol="X", kind="bracket", level=100, entry=100, stop=99,
                   target=103, direction=1.0, target_r=3.0, deadline_days=3.0,
                   setup="confluence_r")
    p.created_at = (now - timedelta(hours=10)).isoformat()
    p.filled_at = (now - timedelta(hours=8)).isoformat()
    p.status, p.outcome_r = "hit", 3.0
    p.resolved_at = (now - timedelta(hours=2)).isoformat()
    j.add(p)
    journal_text = (tmp_path / "j.json").read_text()
    rep = replay_trade(p.id, journal=j, client=_FakeClient(prices))
    return rep, journal_text, (tmp_path / "j.json").read_text()


def test_replay_trade_events_and_caveat(tmp_path):
    rep, before, after = _replay_fixture(tmp_path)
    assert after == before                      # read-only guarantee
    assert "NOT_REPRODUCED" in rep["caveat"]
    assert rep["trade"]["status"] == "hit"
    bars = rep["bars"]
    assert bars, "window bars expected"
    n_pre = sum(1 for b in bars if b.get("pre"))
    assert 0 < n_pre <= 12
    labels = [l for ls in rep["events"].values() for l in ls]
    assert any(l == "SIGNAL" for l in labels)
    assert any(l.startswith("FILLED") for l in labels)
    assert any(l.startswith("RESOLVED HIT") for l in labels)
    # SIGNAL lands on the first non-pre bar.
    sig_k = next(int(k) for k, ls in rep["events"].items() if "SIGNAL" in ls)
    assert sig_k == n_pre
    # Every bar row carries the full factor breakdown.
    assert len(bars[0]["factors"]) == 10


def test_replay_validates_id_and_kind(tmp_path):
    from kudbee_quant.replay import ReplayUnsupported, find_trade, replay_trade

    j = TradeJournal(path=tmp_path / "j2.json", client=_FakeClient([100] * 10))
    with pytest.raises(ValueError):
        find_trade("zzzz", journal=j)
    with pytest.raises(KeyError):
        find_trade("aaaaaaaa", journal=j)
    p = Prediction(symbol="X", kind="touch", level=100, deadline_days=1.0)
    j.add(p)
    with pytest.raises(ReplayUnsupported):
        replay_trade(p.id, journal=j, client=_FakeClient([100] * 10))


def test_replay_too_old(tmp_path):
    from kudbee_quant.replay import ReplayTooOld, replay_trade

    j = TradeJournal(path=tmp_path / "j3.json", client=_FakeClient([100] * 10))
    p = Prediction(symbol="X", kind="bracket", level=100, entry=100, stop=99,
                   target=103, direction=1.0, target_r=3.0, deadline_days=3.0)
    p.created_at = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    j.add(p)
    with pytest.raises(ReplayTooOld):
        replay_trade(p.id, journal=j, client=_FakeClient([100] * 10))
