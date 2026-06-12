"""Test the TradingView alert webhook -> journal loop (no network)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import kudbee_quant.api as api  # noqa: E402


def test_alert_webhook_logs_bracket(tmp_path, monkeypatch):
    # Point the journal at a temp file so no real journal is touched.
    from kudbee_quant.journal import TradeJournal
    from kudbee_quant.api_security import _reset_rate_limits
    monkeypatch.setattr(api, "TradeJournal", lambda: TradeJournal(path=tmp_path / "j.json"))
    monkeypatch.setenv("KUDBEE_API_TOKEN", "testtoken")   # writes require the token
    _reset_rate_limits()
    client = TestClient(api.app)
    hdr = {"X-API-Token": "testtoken"}
    payload = {"symbol": "solusdt", "direction": -1, "entry": 65.0, "stop": 66.5,
               "target": 60.5, "target_r": 3.0, "conf": 0.6, "tf": "1h", "note": "x"}
    r = client.post("/api/alert", json=payload, headers=hdr)
    assert r.status_code == 200
    body = r.json()
    assert body["logged"] and body["symbol"] == "SOLUSDT" and body["status"] == "pending"
    # Duplicate on same symbol+tf is rejected.
    r2 = client.post("/api/alert", json=payload, headers=hdr)
    assert r2.json()["logged"] is False


def _setup(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    from kudbee_quant.api_security import _reset_rate_limits
    jpath = tmp_path / "j.json"
    monkeypatch.setattr(api, "TradeJournal", lambda: TradeJournal(path=jpath))
    monkeypatch.setenv("KUDBEE_API_TOKEN", "testtoken")
    _reset_rate_limits()
    return TestClient(api.app), jpath


def _payload(**kw):
    base = {"symbol": "ethusdt", "direction": 1, "entry": 2500.0, "stop": 2450.0,
            "target": 2650.0, "tf": "1h", "note": "tv test"}
    base.update(kw)
    return base


def test_alert_token_in_body_tradingview_path(tmp_path, monkeypatch):
    # TradingView cannot send custom headers — the token rides in the JSON body.
    client, jpath = _setup(tmp_path, monkeypatch)
    r = client.post("/api/alert", json=_payload(token="testtoken"))
    assert r.status_code == 200 and r.json()["logged"]
    # The trade is provenance-tagged as the trader's read, not the bot's,
    # and the secret never lands in the journal file.
    from kudbee_quant.journal import TradeJournal
    j = TradeJournal(path=jpath)
    assert j.predictions[-1].source == "human"
    assert "testtoken" not in jpath.read_text()


def test_alert_token_in_query(tmp_path, monkeypatch):
    client, _ = _setup(tmp_path, monkeypatch)
    r = client.post("/api/alert?token=testtoken", json=_payload())
    assert r.status_code == 200 and r.json()["logged"]


def test_alert_rejects_bad_or_missing_token(tmp_path, monkeypatch):
    client, jpath = _setup(tmp_path, monkeypatch)
    assert client.post("/api/alert", json=_payload()).status_code == 401
    assert client.post("/api/alert", json=_payload(token="wrong")).status_code == 401
    assert client.post("/api/alert?token=wrong", json=_payload()).status_code == 401
    assert not jpath.exists() or "ETHUSDT" not in jpath.read_text()


def test_alert_rejects_zero_direction(tmp_path, monkeypatch):
    # direction=0 used to silently coerce to SHORT — must 422 instead.
    client, _ = _setup(tmp_path, monkeypatch)
    r = client.post("/api/alert", json=_payload(direction=0, token="testtoken"))
    assert r.status_code == 422
