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
    notify_summary,
    notify_test,
    notify_trades_opened,
    notify_trades_resolved,
)
from .telegram import send_telegram, telegram_enabled

__all__ = [
    "send_telegram",
    "telegram_enabled",
    "notify_trades_opened",
    "notify_trades_resolved",
    "notify_summary",
    "notify_error",
    "notify_test",
]
