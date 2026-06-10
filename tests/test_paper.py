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


def _pending(direction, limit, stop, target, days=2.0, fill_days=0.5):
    p = Prediction(symbol="X", kind="bracket", level=limit, entry=limit, stop=stop,
                   target=target, direction=direction, target_r=3.0, deadline_days=days,
                   pending_limit=True, signal_price=limit + direction, fill_deadline_days=fill_days,
                   setup="confluence_r")
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    return p


def test_pending_limit_fills_then_wins(tmp_path):
    # Long limit at 99.5 (below signal). Price dips to 99.5 (fills), then runs to
    # target 99.5+3=102.5. Stop 98.5. Path: 100,99.4(fill),101,103.
    j = _journal(tmp_path, [100, 99.4, 101, 103])
    j.add(_pending(1, 99.5, 98.5, 102.5))
    changed = j.check_open()
    assert changed and changed[-1].status == "hit" and changed[-1].outcome_r == 3.0


def test_pending_limit_cancelled_if_never_filled(tmp_path):
    # Price never dips to the 99.5 limit within the fill window -> cancelled.
    j = _journal(tmp_path, [100, 100.5, 101, 102])
    p = _pending(1, 99.5, 98.5, 102.5, fill_days=0.01)  # tiny fill window (already passed)
    j.add(p)
    changed = j.check_open()
    assert changed and changed[-1].status == "cancelled"
    assert changed[-1].outcome_r is None  # no trade -> not scored


def test_pending_limit_stays_pending_within_window(tmp_path):
    # Not filled yet, fill window still open -> remains pending (no resolution).
    j = _journal(tmp_path, [100, 100.5, 101, 101])
    p = Prediction(symbol="X", kind="bracket", level=99.5, entry=99.5, stop=98.5,
                   target=102.5, direction=1.0, target_r=3.0, deadline_days=5,
                   pending_limit=True, fill_deadline_days=5.0, setup="c")
    j.add(p)
    assert j.check_open() == []  # still pending, nothing changed
    assert j.predictions[-1].status == "pending"


def test_bracket_partial_tp1_banks_then_breakeven(tmp_path):
    # Long entry 100, stop 99, TP1 at 101 (half), TP2/target at 103.
    # Price hits 101 (banks 0.5*1R=0.5R, stop->BE 100), then falls back to 100
    # before TP2 -> remainder ~0R. Blended = 0.5R. Path: 100,101,100,99.9.
    j = _journal(tmp_path, [100, 101, 100, 99.9])
    p = Prediction(symbol="X", kind="bracket", level=100, entry=100, stop=99,
                   target=103, tp1=101, tp1_frac=0.5, be_after_tp1=True,
                   direction=1.0, target_r=3.0, deadline_days=1.0, setup="partial")
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    j.add(p)
    changed = j.check_open()
    assert changed and changed[-1].outcome_r is not None
    assert abs(changed[-1].outcome_r - 0.5) < 1e-9
    assert changed[-1].tp1_filled_at is not None


def test_bracket_partial_full_run_blends_targets(tmp_path):
    # TP1 at 101 (half @ +1R), TP2 at 103 (half @ +3R). Price runs to 103.
    # Blended = 0.5*1 + 0.5*3 = 2.0R. Path: 100,101,103,103.
    j = _journal(tmp_path, [100, 101, 103, 103])
    p = Prediction(symbol="X", kind="bracket", level=100, entry=100, stop=99,
                   target=103, tp1=101, tp1_frac=0.5, be_after_tp1=True,
                   direction=1.0, target_r=3.0, deadline_days=1.0, setup="partial")
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    j.add(p)
    changed = j.check_open()
    assert changed and changed[-1].status == "hit"
    assert abs(changed[-1].outcome_r - 2.0) < 1e-9


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
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, retrace_atr=0.25,
                           stop_atr=1.0, journal=j, client=C())
    assert len(logged) == 1
    p = logged[0]
    # Pending LIMIT entry at a 0.25 ATR retrace: 100 - 0.25 = 99.75; stop 98.75;
    # target 99.75 + 2*1 = 101.75.
    assert p.kind == "bracket" and p.pending_limit and p.direction == 1.0
    assert abs(p.entry - 99.75) < 1e-9 and abs(p.stop - 98.75) < 1e-9 and abs(p.target - 101.75) < 1e-9
    # Re-scan: already open on BTCUSDT -> no duplicate.
    assert pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, journal=j, client=C()) == []
    # Below-threshold confluence (40%) -> nothing logged on a fresh symbol.
    fake_levels["confluence_pct"] = [0.4]
    j2 = TradeJournal(path=tmp_path / "j2.json", client=C())
    assert pp.paper_scan(["ETHUSDT"], min_pct=0.5, journal=j2, client=C()) == []


def test_paper_scan_tags_tradfi_venue(tmp_path, monkeypatch):
    """A yahoo: (TradFi) spec is logged with the '_tradfi' setup tag so its
    forward record scores separately from the fee-paying crypto book; a bare
    crypto symbol is NOT tagged."""
    import kudbee_quant.paper.paper as pp
    fake_levels = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                                "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake_levels)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC")})

    j = TradeJournal(path=tmp_path / "tf.json", client=C())
    logged = pp.paper_scan(["yahoo:GC=F"], min_pct=0.5, target_r=2.0, retrace_atr=0.25,
                           stop_atr=1.0, journal=j, client=C())
    assert len(logged) == 1
    p = logged[0]
    assert p.symbol == "YAHOO:GC=F"        # spec preserved; source lowercased on route
    assert p.setup.endswith("_tradfi")     # separate scorecard row
    assert "TradFi 0-fee venue" in p.note

    j2 = TradeJournal(path=tmp_path / "cr.json", client=C())
    crypto = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, retrace_atr=0.25,
                           stop_atr=1.0, journal=j2, client=C())
    assert crypto and "_tradfi" not in crypto[0].setup
