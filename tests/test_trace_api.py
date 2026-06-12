"""Tests for the trace / sandbox / replay API endpoints + CLI trace (no network)."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import kudbee_quant.api as api  # noqa: E402
from kudbee_quant.api_security import _reset_rate_limits, safe_spec  # noqa: E402
from kudbee_quant.journal import Prediction, TradeJournal  # noqa: E402

client = TestClient(api.app)


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


class _FakeRouter:
    """Records the spec it was asked for — proves safe_spec routing. Bars end
    at the current hour so replay windows (created_at ~ now) overlap them."""
    last_spec = None

    def klines(self, symbol, interval="1h", limit=600):
        _FakeRouter.last_spec = symbol
        df = _ohlcv(700)
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        df["timestamp"] = pd.date_range(now - timedelta(hours=699), periods=700,
                                        freq="h", tz="UTC")
        return df


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    _reset_rate_limits()
    monkeypatch.setattr(api, "RouterClient", _FakeRouter)
    yield


def test_safe_spec_preserves_source_prefix():
    assert safe_spec("btcusdt") == "BTCUSDT"
    assert safe_spec("yahoo:gc=f") == "yahoo:GC=F"
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        safe_spec("evil:../../x")


def test_trace_endpoint_shape_and_tradfi_routing():
    r = client.get("/api/trace/BTCUSDT?bars=5")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTCUSDT" and len(body["bars"]) == 5
    bar = body["bars"][-1]
    assert {"timestamp", "factors", "net_score", "confluence_pct", "direction"} <= set(bar)
    assert len(bar["factors"]) == 10
    assert {"key", "label", "vote", "detail"} <= set(bar["factors"][0])
    assert body["config"]["min_pct"] == 0.5
    # TradFi spec routes with its prefix intact (the safe_symbol gap is closed).
    r = client.get("/api/trace/yahoo:GC=F?bars=1")
    assert r.status_code == 200
    assert r.json()["symbol"] == "yahoo:GC=F"
    assert _FakeRouter.last_spec == "yahoo:GC=F"


def test_trace_endpoint_validation():
    assert client.get("/api/trace/BTCUSDT?bars=0").status_code == 422
    assert client.get("/api/trace/BTCUSDT?bars=999").status_code == 422
    assert client.get("/api/trace/BTCUSDT?interval=7h").status_code == 422


def test_sandbox_endpoint_happy_path_no_token():
    r = client.post("/api/sandbox/trace",
                    json={"symbol": "BTCUSDT", "ema": {"ema_50": 100},
                          "factors": ["v_emastack", "v_vwap"], "bars": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["unvalidated"] is True
    assert "UNVALIDATED" in body["sandbox_note"]
    assert body["bars"][-1]["n_factors"] == 2
    assert body["params"]["ema"] == {"ema_50": 100}


def test_sandbox_endpoint_validation():
    bad = [
        {"symbol": "BTCUSDT", "ema": {"ema_50": 99999}},
        {"symbol": "BTCUSDT", "ema": {"ema_7": 10}},
        {"symbol": "BTCUSDT", "factors": []},
        {"symbol": "BTCUSDT", "factors": ["v_nope"]},
        {"symbol": "BTCUSDT", "min_pct": 2.0},
        {"symbol": "BTCUSDT", "bars": 0},
    ]
    for payload in bad:
        assert client.post("/api/sandbox/trace", json=payload).status_code == 422, payload


def _journal_with_trade(tmp_path):
    j = TradeJournal(path=tmp_path / "j.json", client=_FakeRouter())
    now = datetime.now(timezone.utc)
    p = Prediction(symbol="BTCUSDT", kind="bracket", level=100, entry=100, stop=99,
                   target=103, direction=1.0, target_r=3.0, deadline_days=3.0,
                   setup="confluence_r")
    p.created_at = (now - timedelta(hours=10)).isoformat()
    p.status, p.outcome_r = "hit", 3.0
    p.resolved_at = (now - timedelta(hours=2)).isoformat()
    j.add(p)
    return j, p


def test_replay_endpoint(tmp_path, monkeypatch):
    j, p = _journal_with_trade(tmp_path)
    monkeypatch.setattr(api, "TradeJournal", lambda: j)

    assert client.get("/api/replay/ZZZZ").status_code == 422
    assert client.get("/api/replay/aaaaaaaa").status_code == 404
    r = client.get(f"/api/replay/{p.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["trade"]["id"] == p.id
    assert body["bars"] and len(body["bars"][0]["factors"]) == 10
    assert "NOT_REPRODUCED" in body["caveat"]
    assert any("SIGNAL" in ls for ls in body["events"].values())


def test_journal_resolved_series_carries_ids(tmp_path):
    j, p = _journal_with_trade(tmp_path)
    rows = j.resolved_series()
    assert rows and rows[-1]["id"] == p.id
    assert rows[-1]["symbol"] == "BTCUSDT"


def test_cli_trade_trace_smoke(tmp_path, monkeypatch, capsys):
    import argparse

    import kudbee_quant.cli as cli
    import kudbee_quant.replay as replay_mod

    j, p = _journal_with_trade(tmp_path)
    monkeypatch.setattr(replay_mod, "TradeJournal", lambda: j)
    monkeypatch.setattr(replay_mod, "RouterClient", _FakeRouter)
    args = argparse.Namespace(trade_id=p.id, symbol=None, interval="1h", bars=48)
    cli._trade_trace(args)
    out = capsys.readouterr().out
    assert f"trade {p.id}" in out
    assert "LONG" in out and "HIT" in out
    assert "SIGNAL" in out               # event marker rendered
    assert "Honest read:" in out
    # Exactly-one-mode guard.
    cli._trade_trace(argparse.Namespace(trade_id=None, symbol=None, interval="1h", bars=48))
    assert "exactly one" in capsys.readouterr().out
