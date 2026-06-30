"""Outbound notifications — Telegram pings on trade events + a periodic report.

This package is a THIN, side-effect-safe layer bolted onto the existing CLI
commands. Design rules (so it can never hurt the bot):

  * **Opt-in by config.** Nothing is sent unless ``TELEGRAM_BOT_TOKEN`` and
    ``TELEGRAM_CHAT_ID`` are set (see :func:`telegram.telegram_enabled`). With
    no creds — local dev, tests, CI without the secrets — every call is a silent
    no-op. The hourly Action is the only place the secrets live.
  * **Never raises.** A network blip or a bad token must not crash the paper-
    trade run. Every public ``notify_*`` swallows its own errors and returns a
    bool (sent / not sent) so callers can stay one-liners.
  * **Batched.** A scan can log dozens of setups across ~100 coins x 5 TFs; we
    send ONE message summarising them, not one ping per trade (Telegram rate
    limits + your sanity).

Public surface:
  * :func:`telegram_enabled` / :func:`send_telegram` — the transport.
  * :func:`notify_trades_opened` / :func:`notify_trades_resolved` /
    :func:`notify_summary` / :func:`notify_error` / :func:`notify_test` — the
    high-level hooks the CLI calls.
"""
from __future__ import annotations

from .notify import (
    notify_error,
    notify_scan_blocked,
    notify_summary,
    notify_test,
    notify_trade_close_events,
    notify_trade_closed,
    notify_trade_open_events,
    notify_trade_opened,
    notify_trades_opened,
    notify_trades_resolved,
    send_telegram_message,
)
from .card_builder import SignalEvent, build_signal_card, notify_signal_card
from .telegram import send_telegram, telegram_enabled
from .weekly_brief import format_weekly_brief, notify_weekly_brief

__all__ = [
    "send_telegram",
    "send_telegram_message",
    "telegram_enabled",
    "SignalEvent",
    "build_signal_card",
    "notify_signal_card",
    "format_weekly_brief",
    "notify_weekly_brief",
    "notify_trades_opened",
    "notify_trades_resolved",
    "notify_trade_opened",
    "notify_trade_closed",
    "notify_trade_open_events",
    "notify_trade_close_events",
    "notify_summary",
    "notify_scan_blocked",
    "notify_error",
    "notify_test",
]
