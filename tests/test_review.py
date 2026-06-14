"""Tests for the open-trades + trade-history review reports (no network)."""
from datetime import datetime, timedelta, timezone

import pandas as pd

from kudbee_quant.journal import Prediction, TradeJournal
from kudbee_quant.review import (
    open_trades_report,
    render_history_text,
    render_open_text,
    trade_history_report,
)


class _Client:
    """Returns a controlled OHLCV frame so excursions are deterministic."""
    def __init__(self, highs, lows, closes, start):
        self.highs, self.lows, self.closes, self.start = highs, lows, closes, start

    def klines(self, symbol, interval="1h", limit=1000):
        n = len(self.closes)
        ts = pd.date_range(self.start, periods=n, freq="h", tz="UTC")
        return pd.DataFrame({"timestamp": ts, "open": self.closes, "high": self.highs,
                             "low": self.lows, "close": self.closes, "volume": 1.0})


def _start(n):
    return datetime.now(timezone.utc) - timedelta(hours=n - 1)


def _open(symbol="BTCUSDT", entry=100.0, stop=99.0, target=103.0, tp1=None, n=4):
    p = Prediction(symbol=symbol, kind="bracket", level=entry, deadline_days=7,
                   entry=entry, stop=stop, target=target, direction=1.0, target_r=3.0,
                   tp1=tp1, status="open")
    s = _start(n)
    p.created_at = s.isoformat()
    p.filled_at = s.isoformat()
    return p


def _journal(tmp_path, preds):
    j = TradeJournal(path=tmp_path / "j.json", client=_Client([100], [100], [100], _start(1)))
    j.predictions = preds
    return j


# --- open-trades report -----------------------------------------------------

def test_open_no_trades(tmp_path):
    rep = open_trades_report(_journal(tmp_path, []))
    assert rep["trades"] == [] and rep["portfolio"]["total_open"] == 0
    assert "No open" in render_open_text(rep)

def test_open_one_profitable(tmp_path):
    p = _open()
    cl = _Client([100.5, 101, 101.7, 101.5], [99.8, 100.2, 100.8, 101.0],
                 [100.2, 100.8, 101.4, 101.5], _start(4))
    rep = open_trades_report(_journal(tmp_path, [p]), client=cl)
    t = rep["trades"][0]
    assert t["unrealized_r"] > 0 and t["mfe_r"] > 0 and t["health"] == "healthy"
    assert rep["portfolio"]["winners_open"] == 1
    assert "Open trades" in render_open_text(rep)

def test_open_one_losing(tmp_path):
    p = _open()
    cl = _Client([100.1, 100.0, 99.9, 99.8], [99.5, 99.4, 99.5, 99.4],
                 [99.8, 99.7, 99.6, 99.5], _start(4))
    rep = open_trades_report(_journal(tmp_path, [p]), client=cl)
    t = rep["trades"][0]
    assert t["unrealized_r"] < 0 and rep["portfolio"]["losers_open"] == 1

def test_open_tp1_touched_not_filled(tmp_path):
    p = _open(tp1=101.0)                      # TARGET ONE at 101; never banked
    assert p.tp1_filled_at is None
    cl = _Client([100.5, 101.2, 100.9, 100.8], [99.9, 100.4, 100.3, 100.2],
                 [100.4, 100.8, 100.6, 100.7], _start(4))
    t = open_trades_report(_journal(tmp_path, [p]), client=cl)["trades"][0]
    assert t["tp1_touched"] is True and t["tp1_filled"] is False

def test_open_near_stop(tmp_path):
    p = _open()
    cl = _Client([100.1, 99.8, 99.5, 99.3], [99.6, 99.0, 98.9, 99.1],   # low tags stop 99
                 [99.9, 99.4, 99.2, 99.2], _start(4))
    t = open_trades_report(_journal(tmp_path, [p]), client=cl)["trades"][0]
    assert t["stop_touched"] is True and t["health"] == "near stop"


# --- trade-history report ---------------------------------------------------

def _closed(symbol, outcome_r, status, mode="paper", tf="1h", entry=100.0, stop=99.0):
    p = Prediction(symbol=symbol, kind="bracket", level=entry, deadline_days=7,
                   entry=entry, stop=stop, target=103.0, direction=1.0, target_r=3.0,
                   status=status, outcome_r=outcome_r, timeframe=tf, mode=mode)
    s = _start(4)
    p.created_at = p.filled_at = s.isoformat()
    p.resolved_at = datetime.now(timezone.utc).isoformat()
    return p

def test_history_empty(tmp_path):
    rep = trade_history_report(_journal(tmp_path, []), with_excursion=False)
    assert rep["portfolio"]["n_resolved"] == 0
    assert "No closed trades" in render_history_text(rep)

def test_history_metrics(tmp_path):
    preds = [_closed("BTCUSDT", 3.0, "hit"), _closed("ETHUSDT", -1.0, "miss"),
             _closed("SOLUSDT", 2.0, "hit"), _closed("XRPUSDT", -1.0, "miss"),
             _closed("ADAUSDT", 0.0, "miss")]               # breakeven
    rep = trade_history_report(_journal(tmp_path, preds), with_excursion=False)
    p = rep["portfolio"]
    assert p["n_resolved"] == 5
    assert p["win_rate"] == 2 / 5
    assert p["profit_factor"] == (3.0 + 2.0) / 2.0          # wins/|losses|
    assert round(p["expectancy_r"], 3) == round((3 - 1 + 2 - 1 + 0) / 5, 3)
    assert p["best_trade_r"] == 3.0 and p["worst_trade_r"] == -1.0
    assert len(rep["equity_curve"]) == 5
    assert rep["equity_curve"][-1]["cum_r"] == 3.0
    assert "win rate" in render_history_text(rep)

def test_history_filters(tmp_path):
    preds = [_closed("BTCUSDT", 3.0, "hit", mode="paper"),
             _closed("ETHUSDT", 1.0, "hit", mode="live"),
             _closed("BTCUSDT", -1.0, "miss", tf="4h")]
    j = _journal(tmp_path, preds)
    assert trade_history_report(j, mode="live", with_excursion=False)["portfolio"]["n_resolved"] == 1
    assert trade_history_report(j, symbol="BTCUSDT", with_excursion=False)["portfolio"]["total_trades"] == 2
    assert trade_history_report(j, timeframe="4h", with_excursion=False)["portfolio"]["total_trades"] == 1

def test_history_excursion_hit_rates(tmp_path):
    p = _closed("BTCUSDT", 3.0, "hit")
    # bars that touch the target (103) and the stop (99) over the trade's life
    cl = _Client([101, 103.2, 102, 100], [99.5, 100, 98.9, 99.5],
                 [100.5, 102.0, 101.0, 100.0], _start(4))
    rep = trade_history_report(_journal(tmp_path, [p]), client=cl, with_excursion=True)
    pf = rep["portfolio"]
    assert pf["tp2_hit_rate"] == 1.0 and pf["stop_hit_rate"] == 1.0
    assert pf["avg_mfe_r"] is not None and rep["trades"][0]["mfe_r"] >= 3.0
