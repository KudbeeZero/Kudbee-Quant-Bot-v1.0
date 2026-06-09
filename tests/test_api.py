"""Tests for the backend API (no network — health + journal only)."""
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from kudbee_quant.api import app  # noqa: E402

client = TestClient(app)


def test_health_returns_validated_config():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # Reflects the validated config (3R, 0.5 confluence, 0.25 retrace).
    assert body["config"]["target_r"] == 3.0
    assert body["config"]["min_pct"] == 0.5
    assert body["config"]["retrace_atr"] == 0.25


def test_journal_endpoint_shape(tmp_path, monkeypatch):
    # Point the journal at a temp empty file (no network).
    import kudbee_quant.api as api
    monkeypatch.setattr(api, "TradeJournal", lambda: _EmptyJournal())
    r = client.get("/api/journal")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"counts", "scorecard", "open"}


class _EmptyJournal:
    predictions: list = []

    def scorecard(self):
        import pandas as pd
        return pd.DataFrame()
