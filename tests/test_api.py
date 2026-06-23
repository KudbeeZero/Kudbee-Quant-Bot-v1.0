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

    def source_record(self):
        return {"bot": {"n": 0}, "human": {"n": 0}}

    def venue_record(self):
        return {"crypto": {"n": 0}, "tradfi": {"n": 0}}

    def resolved_series(self):
        return []

# --- self-registering Telegram webhook endpoint ------------------------------

import kudbee_quant.api as _api  # noqa: E402


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _arm_telegram(monkeypatch, *, token="tok-123", bot="999:BOTABC", secret="whsecret"):
    monkeypatch.setenv("KUDBEE_API_TOKEN", token)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", bot)
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", secret)
    captured = {}

    def _fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResp({"ok": True, "result": True, "description": "Webhook was set"})

    monkeypatch.setattr(_api.requests, "post", _fake_post)
    return captured


def test_register_webhook_success(monkeypatch):
    cap = _arm_telegram(monkeypatch)
    r = client.get("/api/telegram/register-webhook",
                   params={"token": "tok-123", "url": "https://app.example.com"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["registered"] is True
    assert body["webhook_url"] == "https://app.example.com/api/telegram"
    assert body["secret_set"] is True
    # Calls Telegram setWebhook with the bot token in the URL + secret in the body.
    assert cap["url"] == "https://api.telegram.org/bot999:BOTABC/setWebhook"
    assert cap["json"]["url"] == "https://app.example.com/api/telegram"
    assert cap["json"]["secret_token"] == "whsecret"
    # The bot token is never echoed back to the caller.
    assert "999:BOTABC" not in r.text


def test_register_webhook_bad_token_401(monkeypatch):
    _arm_telegram(monkeypatch, token="right")
    r = client.get("/api/telegram/register-webhook",
                   params={"token": "wrong", "url": "https://app.example.com"})
    assert r.status_code == 401


def test_register_webhook_rejects_non_https(monkeypatch):
    _arm_telegram(monkeypatch)
    r = client.get("/api/telegram/register-webhook",
                   params={"token": "tok-123", "url": "http://insecure.example.com"})
    assert r.status_code == 400


def test_register_webhook_503_without_bot_token(monkeypatch):
    monkeypatch.setenv("KUDBEE_API_TOKEN", "tok-123")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    r = client.get("/api/telegram/register-webhook",
                   params={"token": "tok-123", "url": "https://app.example.com"})
    assert r.status_code == 503
