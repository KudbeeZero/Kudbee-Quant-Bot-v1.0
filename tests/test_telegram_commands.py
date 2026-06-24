"""Tests for the two-way Telegram command system (paper-only).

No network: the two webhook-gate tests use FastAPI's TestClient and a recorded
sender; the handler tests use a temp journal + a stub client (so open_trades_report
needs no live price) and clear the module-level state between tests."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

import kudbee_quant.telegram_commands as tc
from kudbee_quant.alert_inbox import log_alert
from kudbee_quant.api import app
from kudbee_quant.journal import TradeJournal

CHAT = "123456"
SECRET = "hook-secret"
SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Isolate module-level pending/rate-limit state + env per test."""
    tc.PENDING_TRADES.clear()
    tc._LAST_SCAN.clear()
    monkeypatch.setenv("TELEGRAM_CHAT_ID", CHAT)
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    monkeypatch.delenv("KUDBEE_GH_TOKEN", raising=False)   # push_inbox_entry no-ops
    yield
    tc.PENDING_TRADES.clear()
    tc._LAST_SCAN.clear()


class _StubClient:
    """Returns no marks (raises) so open_trades_report runs fully offline."""
    def klines(self, *a, **k):
        raise RuntimeError("no network in tests")


def _journal(tmp_path, symbols=("SOLUSDT", "ETHUSDT")):
    j = TradeJournal(path=tmp_path / "journal.json")
    for i, sym in enumerate(symbols):
        price = 100.0 + i
        alert = {"symbol": sym, "direction": 1.0, "entry": price,
                 "stop": price * 0.99, "target": price * 1.03, "target_r": 3.0,
                 "tf": "1h", "setup": "tg_manual"}
        log_alert(j, alert, f"id_{sym}")
    return j


# ── Gate 1 & Gate 2 (the webhook) ────────────────────────────────────────────

def test_webhook_secret_gate(monkeypatch):
    sent = []
    monkeypatch.setattr(tc, "send_telegram", lambda *_: sent.append(1))
    client = TestClient(app)
    # No secret header -> 403 (Gate 2), nothing dispatched.
    r = client.post("/api/telegram", json={"message": {"chat": {"id": int(CHAT)}, "text": "/help"}})
    assert r.status_code == 403
    assert sent == []


def test_chat_id_gate(monkeypatch):
    sent = []
    monkeypatch.setattr(tc, "send_telegram", lambda *_: sent.append(1))
    client = TestClient(app)
    # Correct secret, WRONG chat id -> 200 OK silent drop, no reply sent (Gate 1).
    r = client.post("/api/telegram",
                    headers={SECRET_HEADER: SECRET},
                    json={"message": {"chat": {"id": 999999}, "text": "/help"}})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert sent == []


def test_webhook_owner_help_replies(monkeypatch):
    sent = []
    monkeypatch.setattr(tc, "send_telegram", lambda msg: sent.append(msg) or True)
    client = TestClient(app)
    r = client.post("/api/telegram",
                    headers={SECRET_HEADER: SECRET},
                    json={"message": {"chat": {"id": int(CHAT)}, "text": "/help"}})
    assert r.status_code == 200
    assert sent and "/trade" in sent[0] and "/status" in sent[0]


# ── Tier 1 read ──────────────────────────────────────────────────────────────

def test_cmd_status(tmp_path):
    j = _journal(tmp_path)
    out = tc.cmd_status(j, client=_StubClient())
    assert "SOLUSDT" in out and "ETHUSDT" in out
    assert "2 open" in out


# ── Tier 3 paper-trade gate ──────────────────────────────────────────────────

def test_cmd_trade_parse():
    reply = tc.cmd_trade("/trade SOLUSDT LONG 72.87", CHAT)
    assert CHAT in tc.PENDING_TRADES
    assert tc.PENDING_TRADES[CHAT]["symbol"] == "SOLUSDT"
    assert "Stop" in reply and "Target" in reply and "expires" in reply


def test_cmd_trade_invalid_symbol():
    reply = tc.cmd_trade("/trade DOGEINU LONG 0.001", CHAT)
    assert "Unknown symbol" in reply
    assert CHAT not in tc.PENDING_TRADES


def test_cmd_yes_valid(tmp_path):
    j = TradeJournal(path=tmp_path / "journal.json")
    tc.cmd_trade("/trade SOLUSDT LONG 72.87", CHAT)
    reply = tc.cmd_yes(CHAT, journal=j)
    assert reply.startswith("✅") and "#tg_manual" in reply
    assert CHAT not in tc.PENDING_TRADES
    logged = [p for p in j.predictions if p.setup == "tg_manual"]
    assert len(logged) == 1
    assert logged[0].source == "human" and logged[0].symbol == "SOLUSDT"


def test_cmd_yes_expired(tmp_path):
    j = TradeJournal(path=tmp_path / "journal.json")
    tc.PENDING_TRADES[CHAT] = {"symbol": "SOLUSDT", "side": "LONG", "direction": 1.0,
                               "price": 72.87, "stop": 72.5, "target": 73.9,
                               "ts": time.time() - 61}
    reply = tc.cmd_yes(CHAT, journal=j)
    assert "expired" in reply.lower()
    assert CHAT not in tc.PENDING_TRADES
    assert len(j.predictions) == 0          # nothing written


def test_cmd_yes_no_pending(tmp_path):
    j = TradeJournal(path=tmp_path / "journal.json")
    reply = tc.cmd_yes(CHAT, journal=j)
    assert "No pending trade" in reply
    assert len(j.predictions) == 0
