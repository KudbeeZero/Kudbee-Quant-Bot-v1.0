"""Tests for the prediction journal (no network — fake client)."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from kudbee_quant.journal import Prediction, TradeJournal


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


def _resolved_bracket(symbol, setup, outcome_r, entry=100.0, stop=99.0):
    """A pre-resolved bracket prediction (skip the price-check path)."""
    return Prediction(symbol=symbol, kind="bracket", level=entry, entry=entry,
                      stop=stop, target=entry + 3.0, direction=1.0, target_r=3.0,
                      status="hit" if outcome_r > 0 else "miss", outcome_r=outcome_r,
                      setup=setup, deadline_days=1.0)


def test_fee_in_r_charges_crypto_but_not_tradfi():
    from kudbee_quant.config.validated_defaults import CRYPTO_FEE_ROUNDTRIP
    from kudbee_quant.journal.fees import fee_in_r, round_trip_fee_pct
    # Venue read from the spec: bare/binance pays, yahoo: (TradFi promo) is free.
    assert round_trip_fee_pct("BTCUSDT") == CRYPTO_FEE_ROUNDTRIP
    assert round_trip_fee_pct("YAHOO:GC=F") == 0.0
    # 1R = |100 - 99| = 1.0, so fee_R = fee_pct * entry / risk.
    assert fee_in_r("BTCUSDT", 100.0, 99.0) == pytest.approx(CRYPTO_FEE_ROUNDTRIP * 100.0)
    assert fee_in_r("YAHOO:GC=F", 100.0, 99.0) == 0.0
    # No risk width (non-bracket) -> can't charge -> 0.
    assert fee_in_r("BTCUSDT", None, None) == 0.0


def test_scorecard_net_of_fee_per_venue(tmp_path):
    from kudbee_quant.config.validated_defaults import CRYPTO_FEE_ROUNDTRIP
    j = _journal(tmp_path)
    # Same +1.0R gross outcome on each venue; entry 100 / stop 99 => 1R = 1.0.
    j.add(_resolved_bracket("BTCUSDT", "confluence_r", outcome_r=1.0))
    j.add(_resolved_bracket("YAHOO:GC=F", "confluence_r_tradfi", outcome_r=1.0))
    sc = j.scorecard().set_index("setup")
    fee_r = CRYPTO_FEE_ROUNDTRIP * 100.0  # entry/risk = 100
    # Crypto: net = gross - fee. TradFi (0-fee promo): net == gross.
    assert sc.loc["confluence_r", "expectancy_r"] == pytest.approx(1.0)
    assert sc.loc["confluence_r", "net_expectancy_r"] == pytest.approx(1.0 - fee_r)
    assert sc.loc["confluence_r_tradfi", "net_expectancy_r"] == pytest.approx(1.0)
    # The zero-fee edge is exactly the crypto fee drag.
    edge = (sc.loc["confluence_r_tradfi", "net_expectancy_r"]
            - sc.loc["confluence_r", "net_expectancy_r"])
    assert edge == pytest.approx(fee_r)
