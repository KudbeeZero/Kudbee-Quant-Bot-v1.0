"""Tests for the prediction journal (no network — fake client)."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from kudbee_quant.config.validated_defaults import TAKER_FEE_PCT
from kudbee_quant.journal import Prediction, TradeJournal
from kudbee_quant.journal.journal import fee_r_of, net_outcome_r, venue_of


class _FakeClient:
    """Returns a fixed OHLCV frame; price ranges 90..110 over recent bars."""
    def __init__(self, base=100.0):
        self.base = base

    def klines(self, symbol, interval="1h", limit=1000):
        now = datetime.now(timezone.utc)
        # Span 24h past..23h "future" so the post-creation window is non-empty
        # (simulates time passing after a prediction is logged).
        ts = pd.date_range(now - timedelta(hours=24), periods=48, freq="h", tz="UTC")
        close = pd.Series(range(48)).apply(lambda i: self.base + (i % 20) - 10)  # ~90..110
        return pd.DataFrame({
            "timestamp": ts, "open": close, "high": close + 1,
            "low": close - 1, "close": close, "volume": 1.0,
        })


def _journal(tmp_path):
    return TradeJournal(path=tmp_path / "j.json", client=_FakeClient())


def test_add_and_persist(tmp_path):
    j = _journal(tmp_path)
    j.add(Prediction(symbol="ZECUSDT", kind="touch", level=100.0, deadline_days=7, setup="x"))
    j2 = TradeJournal(path=tmp_path / "j.json", client=_FakeClient())
    assert len(j2.predictions) == 1 and j2.predictions[0].symbol == "ZECUSDT"


def test_invalid_kind_rejected():
    with pytest.raises(ValueError):
        Prediction(symbol="X", kind="moon", level=1.0, deadline_days=1)


def test_touch_resolves_hit(tmp_path):
    j = _journal(tmp_path)
    # 100 is within the 90..110 range the fake client produces -> hit.
    j.add(Prediction(symbol="ZECUSDT", kind="touch", level=100.0, deadline_days=0.0001, setup="t"))
    changed = j.check_open()
    assert changed and changed[0].status == "hit"


def test_reach_above_miss_when_unreached_and_deadline_passed(tmp_path):
    j = _journal(tmp_path)
    p = Prediction(symbol="ZECUSDT", kind="reach_above", level=999.0, deadline_days=0.0001)
    # Backdate creation so the deadline has already passed.
    p.created_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    j.add(p)
    changed = j.check_open()
    assert changed and changed[0].status == "miss"


def test_stay_below_violation_is_miss(tmp_path):
    j = _journal(tmp_path)
    # Level 95 is inside the range, so a high will exceed it -> violated -> miss.
    j.add(Prediction(symbol="ZECUSDT", kind="stay_below", level=95.0, deadline_days=7))
    changed = j.check_open()
    assert changed and changed[0].status == "miss"


def test_open_prediction_stays_open(tmp_path):
    j = _journal(tmp_path)
    # Unreached level, deadline far in the future -> still open.
    j.add(Prediction(symbol="ZECUSDT", kind="reach_above", level=999.0, deadline_days=30))
    assert j.check_open() == []
    assert j.predictions[0].status == "open"


def test_scorecard_counts_resolved(tmp_path):
    j = _journal(tmp_path)
    j.add(Prediction(symbol="A", kind="touch", level=100.0, deadline_days=0.0001, setup="s1"))
    j.add(Prediction(symbol="A", kind="reach_above", level=100.0, deadline_days=0.0001, setup="s1"))
    j.check_open()
    sc = j.scorecard()
    assert sc.loc[sc["setup"] == "s1", "n"].iloc[0] == 2


# --- net-of-fee / per-venue scoring (MEMORY §26) ---------------------------

def _bracket(symbol, outcome_r, status="hit", entry=100.0, stop=99.0):
    """A resolved bracket trade; entry/stop give risk=1 so fee_r == fee_pct*entry."""
    return Prediction(symbol=symbol, kind="bracket", level=entry, deadline_days=7,
                      entry=entry, stop=stop, target=103.0, direction=1.0,
                      target_r=3.0, status=status, outcome_r=outcome_r)


def test_venue_classification():
    crypto = Prediction(symbol="ZECUSDT", kind="touch", level=1.0, deadline_days=1)
    tradfi = Prediction(symbol="yahoo:GC=F", kind="touch", level=1.0, deadline_days=1)
    explicit = Prediction(symbol="binance:BTCUSDT", kind="touch", level=1.0, deadline_days=1)
    assert venue_of(crypto) == "crypto"
    assert venue_of(tradfi) == "tradfi"
    assert venue_of(explicit) == "crypto"


def test_fee_r_and_net_by_venue():
    expected_fee = TAKER_FEE_PCT * 100.0 / 1.0   # fee_pct * entry / risk(=1)
    crypto = _bracket("BTCUSDT", outcome_r=3.0)
    tradfi = _bracket("yahoo:GC=F", outcome_r=3.0)
    assert fee_r_of(crypto) == pytest.approx(expected_fee)
    assert fee_r_of(tradfi) == 0.0                       # zero-fee promo venue
    assert net_outcome_r(crypto) == pytest.approx(3.0 - expected_fee)
    assert net_outcome_r(tradfi) == pytest.approx(3.0)   # net == gross on TradFi


def test_fee_r_zero_for_non_bracket():
    p = Prediction(symbol="BTCUSDT", kind="touch", level=100.0, deadline_days=1)
    assert fee_r_of(p) == 0.0          # no entry/stop -> no R-denominated fee
    assert net_outcome_r(p) is None    # unresolved / carries no R


def test_tp1_fill_adds_a_half_round_trip(tmp_path):
    base = _bracket("BTCUSDT", outcome_r=2.0)
    base.tp1, base.tp1_frac = 102.0, 0.5
    no_tp1 = fee_r_of(base)
    base.tp1_filled_at = "2026-06-09T00:00:00+00:00"     # TP1 banked -> extra exit leg
    assert fee_r_of(base) == pytest.approx(no_tp1 * (1 + 0.5 * 0.5))


def test_scorecard_has_net_columns(tmp_path):
    j = _journal(tmp_path)
    j.predictions = [_bracket("BTCUSDT", outcome_r=3.0)]
    sc = j.scorecard()
    assert {"net_expectancy_r", "net_total_r"} <= set(sc.columns)
    assert sc.iloc[0]["net_expectancy_r"] == pytest.approx(3.0 - TAKER_FEE_PCT * 100.0)


def test_conviction_record_splits_by_confluence_tier(tmp_path):
    j = _journal(tmp_path)
    hi = _bracket("BTCUSDT", outcome_r=3.0)
    hi.setup = "confluence_r_70pct_tf"
    hi2 = _bracket("ETHUSDT", outcome_r=3.0)
    hi2.setup = "confluence_r_80pct_tf"
    lo = _bracket("SOLUSDT", outcome_r=-1.0, status="miss")
    lo.setup = "confluence_r_50pct_tf"
    untagged = _bracket("XRPUSDT", outcome_r=-1.0, status="miss")
    untagged.setup = "my_read"                  # no pct tag -> in neither tier
    j.predictions = [hi, hi2, lo, untagged]
    rec = j.conviction_record()
    assert rec["high_conviction_70plus"]["n"] == 2
    assert rec["high_conviction_70plus"]["hits"] == 2
    assert rec["high_conviction_70plus"]["expectancy_r"] == pytest.approx(3.0)
    assert rec["base_50_60"]["n"] == 1
    assert rec["base_50_60"]["total_r"] == pytest.approx(-1.0)


def test_venue_record_splits_gross_and_net(tmp_path):
    j = _journal(tmp_path)
    j.predictions = [_bracket("BTCUSDT", outcome_r=3.0),
                     _bracket("yahoo:GC=F", outcome_r=3.0)]
    rec = j.venue_record()
    fee = TAKER_FEE_PCT * 100.0
    assert rec["crypto"]["n"] == 1 and rec["tradfi"]["n"] == 1
    # TradFi 0-fee venue: net expectancy == gross. Crypto bleeds exactly the taker.
    assert rec["tradfi"]["net_expectancy_r"] == pytest.approx(rec["tradfi"]["expectancy_r"])
    assert rec["crypto"]["net_expectancy_r"] == pytest.approx(rec["crypto"]["expectancy_r"] - fee)
    assert rec["crypto"]["avg_fee_r"] == pytest.approx(fee)
    assert rec["tradfi"]["avg_fee_r"] == 0.0
