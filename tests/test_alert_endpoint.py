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
