"""Tests for the TR Level Intelligence layer (D1 persistence) — no network.

A FakeD1 (in-memory sqlite, loaded from the real migration) stands in for the
Cloudflare D1 REST client, so d1_execute/d1_query semantics — INSERT OR REPLACE
idempotency, INSERT OR IGNORE change counts, UPDATE recovery — are exercised for
real, just without the HTTP hop.
"""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from kudbee_quant.intelligence import level_recorder, vector_tracker
from kudbee_quant.levels import build_levels

_MIGRATION = (Path(__file__).resolve().parents[1]
              / "cloudflare" / "trade-bot-cron" / "migrations" / "0001_tr_levels.sql")


class FakeD1:
    """In-memory sqlite mirroring the d1_client execute/query contract."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_MIGRATION.read_text())

    def execute(self, sql, params=None):
        cur = self.conn.execute(sql, params or [])
        self.conn.commit()
        return {"changes": cur.rowcount, "last_row_id": cur.lastrowid}

    def query(self, sql, params=None):
        cur = self.conn.execute(sql, params or [])
        return [dict(row) for row in cur.fetchall()]


@pytest.fixture
def db(monkeypatch):
    """Wire FakeD1 into every module that talks to D1."""
    fake = FakeD1()
    monkeypatch.setattr(level_recorder, "d1_execute", fake.execute)
    monkeypatch.setattr(vector_tracker, "d1_execute", fake.execute)
    monkeypatch.setattr(vector_tracker, "d1_query", fake.query)
    import kudbee_quant.telegram_commands as tc
    monkeypatch.setattr(tc, "d1_query", fake.query)
    return fake


# ── helpers ──────────────────────────────────────────────────────────────────

def _ohlcv(n=400, seed=0):
    """A realistic-ish hourly OHLCV frame for build_levels()."""
    ts = pd.date_range(datetime.now(timezone.utc) - timedelta(hours=n - 1),
                       periods=n, freq="h", tz="UTC")
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"timestamp": ts, "open": close,
                         "high": close + 1.0, "low": close - 1.0,
                         "close": close + rng.normal(0, 0.3, n),
                         "volume": rng.uniform(1, 5, n)})


def _vec_frame(bars):
    """Build a frame from explicit bars [(o, h, l, c, v), ...]. Bar 0 is always a
    PVSRA climax (it is its own rolling vol*spread max); make later bars have a
    far-smaller vol*spread so ONLY bar 0 classifies as a climax."""
    n = len(bars)
    ts = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    o, h, l, c, v = zip(*bars, strict=True)
    return pd.DataFrame({"timestamp": ts, "open": o, "high": h,
                         "low": l, "close": c, "volume": v})


# A single bull climax at low=100 (big body + volume), then quiet bars.
def _bull_climax_bar():
    return (99.0, 101.5, 100.0, 101.0, 1000.0)  # o,h,l,c,v -> bull, low=100


# ── level recorder ───────────────────────────────────────────────────────────

def test_record_levels_idempotent(db):
    f = build_levels(_ohlcv())
    level_recorder.record_levels(f, symbol="BTCUSDT", timeframe="1h")
    level_recorder.record_levels(f, symbol="BTCUSDT", timeframe="1h")  # must not raise
    rows = db.query("SELECT * FROM daily_levels WHERE symbol='BTCUSDT'")
    assert len(rows) == 1               # INSERT OR REPLACE -> exactly one row
    assert rows[0]["timeframe"] == "1h"
    assert rows[0]["pivot_pp"] is not None


# ── vector tracker ───────────────────────────────────────────────────────────

def test_vector_tracker_new(db):
    quiet = [(105.0, 105.2, 104.8, 105.0, 1.0)] * 4   # above the recovery zone
    f = _vec_frame([_bull_climax_bar()] + quiet)
    stats = vector_tracker.update_vectors(f, symbol="ETHUSDT", timeframe="1h")
    assert stats["new"] == 1
    rows = db.query("SELECT * FROM unrecovered_vectors WHERE symbol='ETHUSDT' AND active=1")
    assert len(rows) == 1
    assert rows[0]["candle_type"] == "bull_climax"


def test_vector_recovery_bull(db):
    # Bull climax low=100; a later bar dips to 100.2 (within 0.3% -> recovered).
    dip = [(100.5, 100.7, 100.2, 100.6, 1.0)]
    f = _vec_frame([_bull_climax_bar()] + dip + [(105.0, 105.2, 104.8, 105.0, 1.0)])
    stats = vector_tracker.update_vectors(f, symbol="SOLUSDT", timeframe="1h")
    assert stats["recovered"] == 1
    rows = db.query("SELECT * FROM unrecovered_vectors WHERE symbol='SOLUSDT'")
    assert len(rows) == 1
    assert rows[0]["active"] == 0
    assert rows[0]["recovery_price"] is not None


def test_vector_no_recovery_bull(db):
    # Bull climax low=100; lowest later bar is 102 (out of the 0.3% zone).
    far = [(102.5, 102.7, 102.0, 102.4, 1.0)] * 3
    f = _vec_frame([_bull_climax_bar()] + far)
    stats = vector_tracker.update_vectors(f, symbol="ADAUSDT", timeframe="1h")
    assert stats["recovered"] == 0
    rows = db.query("SELECT * FROM unrecovered_vectors WHERE symbol='ADAUSDT'")
    assert len(rows) == 1 and rows[0]["active"] == 1


# ── telegram command handlers ────────────────────────────────────────────────

def test_cmd_levels_no_data(db):
    import kudbee_quant.telegram_commands as tc
    out = tc.cmd_levels("/levels BTCUSDT")
    assert "No level data" in out          # empty D1 -> helpful message, no crash


def test_cmd_vectors_empty(db):
    import kudbee_quant.telegram_commands as tc
    out = tc.cmd_vectors("/vectors BTCUSDT")
    assert "No unrecovered vectors" in out


def test_cmd_levels_renders_after_record(db):
    import kudbee_quant.telegram_commands as tc
    level_recorder.record_levels(build_levels(_ohlcv()), symbol="BTCUSDT")
    out = tc.cmd_levels("/levels BTCUSDT")
    assert "TR Levels — BTCUSDT" in out and "PP:" in out


# ── non-blocking guarantee ───────────────────────────────────────────────────

def test_d1_write_failure_doesnt_crash_scan(monkeypatch):
    """A D1 write that raises must be absorbed by the cli intelligence wrapper —
    the scan path completes and _record_intelligence returns without raising."""
    import kudbee_quant.cli as cli
    import kudbee_quant.ingest as ingest

    class _FakeClient:
        def klines(self, symbol, interval="1h", limit=600):
            return _ohlcv()

    monkeypatch.setenv("D1_DATABASE_ID", "test-db")
    monkeypatch.setattr(ingest, "RouterClient", _FakeClient)

    def _boom(*a, **k):
        raise RuntimeError("D1 down")
    monkeypatch.setattr(level_recorder, "d1_execute", _boom)

    # Must not raise — the try/except in cli._record_intelligence absorbs it.
    assert cli._record_intelligence(["BTCUSDT"]) is None


def test_intelligence_skipped_when_unconfigured(monkeypatch):
    """No D1_DATABASE_ID -> silent no-op (no network, no D1 calls)."""
    import kudbee_quant.cli as cli
    monkeypatch.delenv("D1_DATABASE_ID", raising=False)
    called = {"n": 0}

    def _spy(*a, **k):
        called["n"] += 1
        raise AssertionError("should not be reached when unconfigured")
    monkeypatch.setattr(level_recorder, "d1_execute", _spy)
    assert cli._record_intelligence(["BTCUSDT"]) is None
    assert called["n"] == 0
