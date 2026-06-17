"""Tests for the Telegram notification layer (no real network).

Covers the two things that matter: (1) the gating — with no creds everything is a
silent no-op and never raises; (2) the message formatting — pure functions that
turn Predictions / report dicts into the strings we'd send.
"""
from __future__ import annotations

import kudbee_quant.notifications.telegram as tg
from kudbee_quant.journal import Prediction
from kudbee_quant.notifications import (
    notify_summary,
    notify_trades_opened,
    notify_trades_resolved,
    send_telegram,
    telegram_enabled,
)
from kudbee_quant.notifications.notify import (
    format_summary,
    format_trades_opened,
    format_trades_resolved,
)
from kudbee_quant.notifications.telegram import _split


def _pred(symbol="BTCUSDT", direction=1.0, status="open", outcome_r=None, pending=True):
    return Prediction(
        symbol=symbol, kind="bracket", level=100.0, deadline_days=3.0,
        entry=100.0, stop=99.0, target=103.0, direction=direction, target_r=3.0,
        timeframe="1h", status=status, outcome_r=outcome_r, pending_limit=pending,
    )


# --- gating: no creds -> silent no-op, never raises -------------------------

def _clear_env(monkeypatch):
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "KUDBEE_TELEGRAM_ENABLED"):
        monkeypatch.delenv(k, raising=False)


def test_disabled_without_creds(monkeypatch):
    _clear_env(monkeypatch)
    assert telegram_enabled() is False
    # Every entry point must no-op (return False) and not touch the network.
    assert send_telegram("hi") is False
    assert notify_trades_opened([_pred()]) is False
    assert notify_trades_resolved([_pred(status="hit", outcome_r=3.0)]) is False
    assert notify_summary() is False


def test_killswitch_overrides_creds(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("KUDBEE_TELEGRAM_ENABLED", "false")
    assert telegram_enabled() is False
    monkeypatch.setenv("KUDBEE_TELEGRAM_ENABLED", "1")
    assert telegram_enabled() is True


def test_enabled_with_both_creds(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.delenv("KUDBEE_TELEGRAM_ENABLED", raising=False)
    assert telegram_enabled() is True


def test_send_swallows_network_error(monkeypatch):
    """A raising HTTP client must not propagate — send returns False."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.delenv("KUDBEE_TELEGRAM_ENABLED", raising=False)

    class _Boom:
        def post(self, *a, **k):
            raise RuntimeError("network down")

    monkeypatch.setitem(__import__("sys").modules, "requests", _Boom())
    assert send_telegram("hi") is False


def test_send_error_does_not_leak_token(monkeypatch, caplog):
    """A network error must not log the bot token (it lives in the request URL)."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "SECRET123:abcdef")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.delenv("KUDBEE_TELEGRAM_ENABLED", raising=False)

    class _Boom:
        def post(self, *a, **k):
            # Mimic requests embedding the token-bearing URL in its message.
            raise RuntimeError(
                "Max retries exceeded with url: /botSECRET123:abcdef/sendMessage")

    monkeypatch.setitem(__import__("sys").modules, "requests", _Boom())
    import logging
    with caplog.at_level(logging.WARNING):
        assert send_telegram("hi") is False
    assert "SECRET123:abcdef" not in caplog.text
    assert "***" in caplog.text


def test_send_success_path(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.delenv("KUDBEE_TELEGRAM_ENABLED", raising=False)
    sent = {}

    class _Resp:
        status_code = 200
        text = "ok"

    class _OK:
        def post(self, url, json, timeout):
            sent["json"] = json
            return _Resp()

    monkeypatch.setitem(__import__("sys").modules, "requests", _OK())
    assert send_telegram("hello") is True
    assert sent["json"]["text"] == "hello"
    assert sent["json"]["chat_id"] == "1"


# --- formatting (pure) ------------------------------------------------------

def test_format_trades_opened():
    msg = format_trades_opened([_pred("BTCUSDT"), _pred("ETHUSDT", direction=-1.0)])
    assert "2 new trade setups" in msg
    assert "LONG BTCUSDT" in msg
    assert "SHORT ETHUSDT" in msg
    assert "limit pending" in msg


def test_format_trades_opened_singular():
    assert "1 new trade setup logged" in format_trades_opened([_pred()])


def test_format_trades_resolved_filters_and_totals():
    preds = [
        _pred("BTCUSDT", status="hit", outcome_r=3.0),
        _pred("ETHUSDT", status="miss", outcome_r=-1.0),
        _pred("SOLUSDT", status="open"),          # still open -> excluded
    ]
    msg = format_trades_resolved(preds)
    assert "2 trades resolved" in msg
    assert "+2.00R total" in msg          # 3.0 + (-1.0)
    assert "✅ BTCUSDT" in msg
    assert "❌ ETHUSDT" in msg
    assert "SOLUSDT" not in msg


def test_format_summary():
    report = {"portfolio": {
        "total_open": 3, "total_unrealized_r": 1.25, "total_unrealized_usd": None,
        "winners_open": 2, "losers_open": 1, "total_open_risk_pct": 3.0,
        "closest_to_stop": "ETHUSDT", "closest_to_tp": "BTCUSDT", "warnings": ["XRPUSDT near stop"],
    }}
    record = {"crypto": {"n": 10, "hits": 4, "net_expectancy_r": 0.12}}
    msg = format_summary(report, record=record)
    assert "Open: 3" in msg
    assert "+1.25R" in msg
    assert "near stop" in msg
    assert "crypto 4/10" in msg


def test_split_long_message():
    chunks = _split("x" * 5000)
    assert len(chunks) >= 2
    assert all(len(c) <= tg._MAX_LEN for c in chunks)
    short = _split("just one line")
    assert short == ["just one line"]
