"""Tests for bracket journal predictions and the paper-trading scan (no network)."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from kudbee_quant.journal import Prediction, TradeJournal


class _FakeClient:
    def __init__(self, path_prices):
        self.prices = path_prices

    def klines(self, symbol, interval="1h", limit=1000):
        now = datetime.now(timezone.utc)
        n = len(self.prices)
        ts = pd.date_range(now - timedelta(hours=n - 1), periods=n, freq="h", tz="UTC")
        c = pd.Series(self.prices, dtype=float)
        return pd.DataFrame({"timestamp": ts, "open": c, "high": c + 0.5,
                             "low": c - 0.5, "close": c, "volume": 1.0})


def _journal(tmp_path, prices):
    return TradeJournal(path=tmp_path / "j.json", client=_FakeClient(prices))


def _bracket(direction, entry, stop, target, days=1.0):
    p = Prediction(symbol="X", kind="bracket", level=entry, entry=entry, stop=stop,
                   target=target, direction=direction, target_r=2.0, deadline_days=days,
                   setup="confluence_r")
    # Backdate so the fake bars fall after creation.
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    return p


def test_bracket_target_first_is_win(tmp_path):
    # Long entry 100, stop 99, target 102. Price path reaches 102 (high 102.5).
    j = _journal(tmp_path, [100, 101, 102, 103])
    j.add(_bracket(1, 100, 99, 102))
    changed = j.check_open()
    assert changed and changed[0].status == "hit" and changed[0].outcome_r == 2.0


def test_bracket_stop_first_is_loss(tmp_path):
    # Long entry 100, stop 99, target 102. Price drops to 98 first.
    j = _journal(tmp_path, [100, 98, 102, 103])
    j.add(_bracket(1, 100, 99, 102))
    changed = j.check_open()
    assert changed and changed[0].status == "miss" and changed[0].outcome_r == -1.0


def test_bracket_short_target(tmp_path):
    # Short entry 100, stop 101, target 98. Price falls to 97.
    j = _journal(tmp_path, [100, 99, 97, 97])
    j.add(_bracket(-1, 100, 101, 98))
    changed = j.check_open()
    assert changed and changed[0].status == "hit" and changed[0].outcome_r == 2.0


def test_scorecard_reports_expectancy_r(tmp_path):
    j = _journal(tmp_path, [100, 102.5, 103, 103])  # this path hits long target
    j.add(_bracket(1, 100, 99, 102))
    j.check_open()
    sc = j.scorecard()
    assert "expectancy_r" in sc.columns
    assert sc.loc[sc["setup"] == "confluence_r", "expectancy_r"].iloc[0] == 2.0


def test_paper_scan_logs_when_signalling(tmp_path, monkeypatch):
    import kudbee_quant.paper.paper as pp
    # Force a strong long confluence signal (60% of factors aligned).
    fake_levels = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                                "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake_levels)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC")})
    j = TradeJournal(path=tmp_path / "j.json", client=C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, journal=j, client=C())
    assert len(logged) == 1
    p = logged[0]
    assert p.kind == "bracket" and p.direction == 1.0 and p.target == 102.0 and p.stop == 99.0
    # Re-scan: already open on BTCUSDT -> no duplicate.
    assert pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, journal=j, client=C()) == []
    # Below-threshold confluence (40%) -> nothing logged on a fresh symbol.
    fake_levels["confluence_pct"] = [0.4]
    j2 = TradeJournal(path=tmp_path / "j2.json", client=C())
    assert pp.paper_scan(["ETHUSDT"], min_pct=0.5, journal=j2, client=C()) == []
