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
