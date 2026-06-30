"""Circuit-breaker alert — immediate Telegram ping when the drawdown breaker flips.

Registered as the ``on_state_change`` callback on :meth:`DrawdownGuard.update`. The
breaker uses rolling-R hysteresis (pause below ``pause_threshold_r``, resume at/above
``resume_threshold_r``), so the messages describe THAT honestly — no invented
"consecutive losses" count or time cooldown the guard doesn't actually track.

This is intentionally NOT behind a feature flag: if the ``_dcb`` breaker is active at
all, a state change is important enough to always announce. Every send is fail-open.
"""
from __future__ import annotations

from .telegram import send_telegram

_RULE = "━" * 21


def _trip_message(guard) -> str:
    return "\n".join([
        "⚠️ <b>CIRCUIT BREAKER TRIPPED</b>",
        _RULE,
        "Bot is now <b>PAUSED</b> — no new entries.",
        f"Rolling R (last {guard.window} closed): <b>{guard.rolling_r:+.2f}R</b>"
        f"  (pause &lt; {guard.pause_threshold_r:+.1f}R)",
        _RULE,
        f"Resumes automatically when rolling R recovers to ≥ {guard.resume_threshold_r:+.1f}R.",
        "Use /resume to override manually.",
    ])


def _reset_message(guard) -> str:
    return "\n".join([
        "✅ <b>CIRCUIT BREAKER RESET</b>",
        f"Bot is <b>ACTIVE</b> again — rolling R {guard.rolling_r:+.2f}R "
        f"(≥ resume {guard.resume_threshold_r:+.1f}R).",
    ])


def notify_state_change(old_state: str, new_state: str, guard) -> bool:
    """Send the trip/reset card. ``new_state`` is ``"paused"`` or ``"active"``.
    Returns True iff delivered; never raises."""
    try:
        if new_state == "paused":
            text = _trip_message(guard)
        elif new_state == "active":
            text = _reset_message(guard)
        else:
            return False
        return send_telegram(text, parse_mode="HTML")
    except Exception:  # noqa: BLE001
        return False
