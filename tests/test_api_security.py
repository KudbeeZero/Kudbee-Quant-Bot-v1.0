"""Security tests for the hardened API: token auth (fail-closed), input
validation, and rate limiting on the write endpoints."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import kudbee_quant.api as api  # noqa: E402
from kudbee_quant.api_security import _reset_rate_limits  # noqa: E402


def _client(tmp_path, monkeypatch, token="testtoken"):
    from kudbee_quant.journal import TradeJournal
    monkeypatch.setattr(api, "TradeJournal", lambda: TradeJournal(path=tmp_path / "j.json"))
    if token is not None:
        monkeypatch.setenv("KUDBEE_API_TOKEN", token)
    else:
        monkeypatch.delenv("KUDBEE_API_TOKEN", raising=False)
    _reset_rate_limits()
    return TestClient(api.app)


_GOOD = {"symbol": "BTCUSDT", "direction": 1, "entry": 100.0, "stop": 99.0,
         "target": 103.0, "target_r": 3.0, "conf": 0.6, "tf": "1h", "note": "ok"}


def test_alert_requires_token(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    assert c.post("/api/alert", json=_GOOD).status_code == 401            # no header
    assert c.post("/api/alert", json=_GOOD,
                  headers={"X-API-Token": "wrong"}).status_code == 401     # bad token


def test_writes_disabled_when_no_token_configured(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, token=None)
    assert c.post("/api/alert", json=_GOOD).status_code == 503             # fail closed


def test_alert_rejects_bad_input(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    h = {"X-API-Token": "testtoken"}
    bad_symbol = {**_GOOD, "symbol": "../../etc/passwd"}
    assert c.post("/api/alert", json=bad_symbol, headers=h).status_code == 422
    bad_note = {**_GOOD, "note": "x" * 600}
    assert c.post("/api/alert", json=bad_note, headers=h).status_code == 422
    bad_dir = {**_GOOD, "direction": 5}
    assert c.post("/api/alert", json=bad_dir, headers=h).status_code == 422


def test_rate_limit_trips(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    h = {"X-API-Token": "testtoken"}
    codes = [c.post("/api/alert", json=_GOOD, headers=h).status_code for _ in range(13)]
    assert 429 in codes        # the write limiter (10/min) trips within 13 calls


def test_signal_rejects_bad_symbol(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    assert c.get("/api/signal/" + "A" * 40).status_code == 422   # fails whitelist
    assert c.get("/api/signal/BTCUSDT?interval=9z").status_code == 422
