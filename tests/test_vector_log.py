"""Vector-candle logger + study tests — hermetic (synthetic bars, no network)."""
from __future__ import annotations

import json

import pandas as pd

from kudbee_quant.signals.vector_log import (
    _nearest_level, detect_vector_events, scan_and_log,
)
from kudbee_quant.signals.vector_study import summarize, vector_outcomes


def _frame(n=60, climax_at=40, climax_up=True, forward="up", atr=1.0):
    """OHLCV frame with one dominant climax bar + a deterministic forward path.

    Baseline volume DESCENDS so no flat bar ties the PVSRA rolling-max (real data
    never ties); only the injected high-volume bar is a climax. Includes
    `daily_open`/`atr` so detect/outcomes skip the heavy build_levels."""
    ts = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
    rows = []
    for i in range(n):
        vol = 500.0 - i * 2.0           # strictly descending => unique max = climax bar
        o = c = 100.0
        hi, lo = 100.3, 99.7
        if i == climax_at:
            o, c = 100.0, (101.0 if climax_up else 99.0)
            hi, lo = 101.3, 99.7
            vol = 5000.0                 # dominant volume => the climax
        elif i > climax_at:
            step = (i - climax_at) * 1.0
            base = 100.0 + step if forward == "up" else 100.0 - step
            o = c = base
            hi = base + (0.6 if forward == "up" else 0.2)
            lo = base - (0.2 if forward == "up" else 0.6)
        rows.append((ts[i], o, hi, lo, c, vol))
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["daily_open"] = 100.0
    df["atr"] = atr
    return df


# --- nearest-level tagging --------------------------------------------------

def test_nearest_level_picks_closest_within_atr():
    row = pd.Series({"close": 100.0, "vwap": 100.3, "daily_open": 102.0})
    name, dist = _nearest_level(row, atr=1.0)
    assert name == "vwap" and round(dist, 2) == 0.30

def test_nearest_level_open_space_when_far():
    row = pd.Series({"close": 100.0, "vwap": 105.0, "daily_open": 110.0})
    name, _ = _nearest_level(row, atr=1.0)
    assert name == "open_space"


# --- detection --------------------------------------------------------------

def test_detect_finds_the_climax_candle():
    df = _frame(climax_up=True)
    events = detect_vector_events(df, "TESTUSDT", "5m")
    assert any(e.vector == "bull_climax" for e in events)
    ev = next(e for e in events if e.vector == "bull_climax")
    assert ev.symbol == "TESTUSDT" and ev.timeframe == "5m"
    assert ev.vol_ratio > 2.0          # the climax bar is >2x average volume

def test_detect_last_only_returns_nothing_when_last_bar_is_quiet():
    df = _frame(climax_at=40)          # last bar (idx 59) is not a climax
    assert detect_vector_events(df, "T", "5m", last_only=True) == []


# --- outcomes ---------------------------------------------------------------

def test_bull_climax_then_rally_resolves_positive():
    df = _frame(climax_up=True, forward="up", atr=1.0)
    rows = vector_outcomes(df, "T", "5m", max_bars=24, stop_atr=1.0, target_r=3.0)
    climax = [r for r in rows if r["vector"] == "bull_climax"]
    assert climax and climax[0]["outcome_r"] > 0      # rally hit the long target
    assert climax[0]["net_r"] < climax[0]["outcome_r"]  # fee subtracted

def test_bull_climax_then_selloff_resolves_negative():
    df = _frame(climax_up=True, forward="down", atr=1.0)
    rows = vector_outcomes(df, "T", "5m", max_bars=24, stop_atr=1.0, target_r=3.0)
    climax = [r for r in rows if r["vector"] == "bull_climax"]
    assert climax and climax[0]["outcome_r"] < 0      # long stopped out


# --- aggregation ------------------------------------------------------------

def test_summarize_groups_and_computes_net():
    rows = [
        {"level": "vwap", "outcome_r": 3.0, "fee_r": 0.1, "net_r": 2.9},
        {"level": "vwap", "outcome_r": -1.0, "fee_r": 0.1, "net_r": -1.1},
        {"level": "open_space", "outcome_r": -1.0, "fee_r": 0.1, "net_r": -1.1},
    ]
    t = summarize(rows, ("level",))
    vwap = t[t["level"] == "vwap"].iloc[0]
    assert vwap["n"] == 2 and vwap["win_rate"] == 0.5
    assert round(vwap["exp_net_r"], 2) == 0.90


# --- scan + log (dedupe, tmp path, fake client) -----------------------------

class _FakeClient:
    def __init__(self, df):
        self._df = df
    def klines(self, symbol, interval="5m", limit=300):
        return self._df

def test_scan_and_log_writes_and_dedupes(tmp_path):
    df = _frame(climax_up=True)
    client = _FakeClient(df)
    path = tmp_path / "vector_log.json"
    first = scan_and_log(["TESTUSDT"], ["5m"], client=client, path=path, last_only=False)
    assert len(first) >= 1 and path.exists()
    logged = json.loads(path.read_text())
    assert len(logged) == len(first)
    # second identical scan adds nothing (dedupe by symbol+tf+timestamp)
    second = scan_and_log(["TESTUSDT"], ["5m"], client=client, path=path, last_only=False)
    assert second == []
    assert len(json.loads(path.read_text())) == len(first)
