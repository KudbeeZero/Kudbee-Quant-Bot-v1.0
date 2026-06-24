"""Unit tests for the INDIVIDUAL per-trade Telegram alerts (open / close).

These cover the message formatting, the WIN / BREAKEVEN / STOPPED classification,
the never-raises guarantee, and the freshness dedup guard — all with the network
fully mocked, so they need no Telegram creds and send nothing. They do NOT touch
the existing batched summary path.
"""
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from kudbee_quant.notifications import notify


# --- fixtures -----------------------------------------------------------------

def _open_trade(direction="LONG"):
    return {
        "symbol": "ETHUSDT",
        "direction": direction,
        "timeframe": "1h",
        "entry_price": 3421.5,
        "stop_price": 3380.0,
        "target_price": 3540.0,
        "book": "core",
    }


def _closed_trade(r_result, **over):
    now_ms = time.time() * 1000
    base = {
        "symbol": "SOLUSDT",
        "direction": "LONG",
        "timeframe": "1h",
        "entry_price": 142.5,
        "exit_price": 150.0,
        "r_result": r_result,
        "open_time": now_ms - 135 * 60 * 1000,   # 2h 15m ago
        "close_time": now_ms,
    }
    base.update(over)
    return base


def _pred(created_at, **over):
    """A minimal duck-typed Prediction for the dispatcher/dedup tests."""
    base = dict(symbol="ETHUSDT", direction=1.0, timeframe="1h", entry=3400.0,
                stop=3380.0, target=3540.0, setup="confluence_r_50pct", kind="bracket",
                status="pending", created_at=created_at, resolved_at=None, outcome_r=None)
    base.update(over)
    return SimpleNamespace(**base)


# --- open alert content -------------------------------------------------------

def test_notify_trade_opened_long():
    with mock.patch.object(notify, "send_telegram_message", return_value=True) as send:
        ok = notify.notify_trade_opened("tok", "chat", _open_trade("LONG"))
    assert ok is True
    msg = send.call_args[0][2]
    for sub in ("▸ LONG", "Entry", "Stop", "Target", "Trade Opened", "ETHUSDT", "Book"):
        assert sub in msg, f"missing {sub!r} in:\n{msg}"


def test_notify_trade_opened_short():
    with mock.patch.object(notify, "send_telegram_message", return_value=True) as send:
        notify.notify_trade_opened("tok", "chat", _open_trade("SHORT"))
    msg = send.call_args[0][2]
    assert "▸ SHORT" in msg


# --- close alert content + classification ------------------------------------

def test_notify_trade_closed_win():
    with mock.patch.object(notify, "send_telegram_message", return_value=True) as send:
        notify.notify_trade_closed("tok", "chat", _closed_trade(3.0))
    msg = send.call_args[0][2]
    for sub in ("TARGET HIT", "+3.00R", "◈"):
        assert sub in msg, f"missing {sub!r} in:\n{msg}"


def test_notify_trade_closed_stop():
    with mock.patch.object(notify, "send_telegram_message", return_value=True) as send:
        notify.notify_trade_closed("tok", "chat", _closed_trade(-1.0))
    msg = send.call_args[0][2]
    assert "STOPPED" in msg and "-1.00R" in msg


def test_notify_trade_closed_breakeven():
    with mock.patch.object(notify, "send_telegram_message", return_value=True) as send:
        notify.notify_trade_closed("tok", "chat", _closed_trade(0.05))
    msg = send.call_args[0][2]
    assert "FLAT" in msg


def test_notify_trade_closed_held_duration():
    # 2h 15m apart -> "2h 15m"
    with mock.patch.object(notify, "send_telegram_message", return_value=True) as send:
        notify.notify_trade_closed("tok", "chat", _closed_trade(3.0))
    msg = send.call_args[0][2]
    assert "held 2h 15m" in msg


# --- never-raises -------------------------------------------------------------

def test_notify_failure_doesnt_crash():
    with mock.patch.object(notify, "send_telegram_message", side_effect=RuntimeError("boom")):
        # The send blows up, but the try/except inside the notify fns swallows it.
        assert notify.notify_trade_opened("tok", "chat", _open_trade("LONG")) is False
        assert notify.notify_trade_closed("tok", "chat", _closed_trade(3.0)) is False


# --- freshness dedup guard (on the dispatcher) -------------------------------

def test_dedup_guard_old_trade():
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    p = _pred(old)
    with mock.patch.object(notify, "telegram_enabled", return_value=True), \
         mock.patch.object(notify, "notify_trade_opened", return_value=True) as one:
        n = notify.notify_trade_open_events([p])
    one.assert_not_called()
    assert n == 0


def test_dedup_guard_new_trade():
    new = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    p = _pred(new)
    with mock.patch.object(notify, "telegram_enabled", return_value=True), \
         mock.patch.object(notify, "notify_trade_opened", return_value=True) as one:
        n = notify.notify_trade_open_events([p])
    one.assert_called_once()
    assert n == 1


def test_close_events_skips_cancelled():
    """A 'cancelled' (limit never filled) must NOT get an individual close alert."""
    now = datetime.now(timezone.utc).isoformat()
    cancelled = _pred(now, status="cancelled", resolved_at=now, outcome_r=None)
    with mock.patch.object(notify, "telegram_enabled", return_value=True), \
         mock.patch.object(notify, "notify_trade_closed", return_value=True) as one:
        n = notify.notify_trade_close_events([cancelled])
    one.assert_not_called()
    assert n == 0


def test_disabled_telegram_is_silent_noop():
    """With Telegram off, the dispatchers send nothing and return 0."""
    new = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with mock.patch.object(notify, "telegram_enabled", return_value=False), \
         mock.patch.object(notify, "notify_trade_opened") as one:
        n = notify.notify_trade_open_events([_pred(new)])
    one.assert_not_called()
    assert n == 0


# --- data-derived "why this fired" bullets ------------------------------------

def test_why_fired_parses_real_bot_note():
    note = ("Auto confluence-R long scalp: 50% confluence (strength 5). "
            "LIMIT 6.3e4 (retrace 0.25 ATR from 6.4e4), stop 6.2e4, "
            "target 6.5e4 (3.0R, maker).")
    lines = notify._why_fired(note, "confluence_r_50pct")
    joined = "\n".join(lines)
    assert "5 confluence factors checked — 50% gate cleared" in joined
    assert "0.25 ATR pullback" in joined
    assert "Maker-favorable fill" in joined
    assert "EMA 5 / 13 / 50" not in joined          # not a _cts trade


def test_why_fired_adds_cts_stack_line():
    lines = notify._why_fired("50% confluence (strength 6), retrace 0.25 ATR, maker",
                              "clean_trend_stack_cts")
    assert any("EMA 5 / 13 / 50" in ln for ln in lines)


def test_open_message_includes_why_block():
    trade = _open_trade("SHORT")
    trade["note"] = "60% confluence (strength 7), retrace 0.25 ATR, maker"
    trade["setup"] = "confluence_r_50pct"
    with mock.patch.object(notify, "send_telegram_message", return_value=True) as send:
        notify.notify_trade_opened("tok", "chat", trade)
    msg = send.call_args[0][2]
    assert "Why this fired:" in msg
    assert "7 confluence factors checked — 60% gate cleared" in msg
