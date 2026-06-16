"""Telegram transport — the only thing here that touches the network.

Reads its config from the environment (via the masked :func:`get_secret`):

  * ``TELEGRAM_BOT_TOKEN`` — the bot token from @BotFather.
  * ``TELEGRAM_CHAT_ID``   — the numeric chat id to deliver to (you, or a group).
  * ``KUDBEE_TELEGRAM_ENABLED`` — optional kill-switch. Unset = enabled whenever
    both creds are present; set to a false-y value ("0"/"false"/"no"/"off") to
    mute even with creds present (handy for a dry Action run).

Nothing here raises on a send failure: :func:`send_telegram` returns ``True`` on
a confirmed delivery and ``False`` otherwise (not configured, network error,
non-200). That keeps every caller a safe one-liner inside the paper-trade run.
"""
from __future__ import annotations

import logging

from ..config.secrets import get_secret

log = logging.getLogger(__name__)

# Telegram caps a single sendMessage at 4096 chars; we split below this with a
# little headroom for the continuation marker.
_MAX_LEN = 3900
_API = "https://api.telegram.org/bot{token}/sendMessage"
_FALSEY = {"0", "false", "no", "off", ""}


def _token() -> str | None:
    s = get_secret("TELEGRAM_BOT_TOKEN", required=False)
    return s.reveal() if s else None


def _chat_id() -> str | None:
    s = get_secret("TELEGRAM_CHAT_ID", required=False)
    return s.reveal() if s else None


def telegram_enabled() -> bool:
    """True only if a token + chat id are set AND the kill-switch isn't off.

    Everything in this package short-circuits on this, so with no creds the whole
    notification layer is a silent no-op (local dev, tests, CI without secrets).
    """
    switch = get_secret("KUDBEE_TELEGRAM_ENABLED", required=False)
    if switch is not None and switch.reveal().strip().lower() in _FALSEY:
        return False
    return bool(_token()) and bool(_chat_id())


def _split(text: str, limit: int = _MAX_LEN) -> list[str]:
    """Split a long message on line boundaries so no chunk exceeds Telegram's cap."""
    if len(text) <= limit:
        return [text]
    chunks, cur = [], ""
    for line in text.split("\n"):
        # A single monster line still has to be hard-split.
        while len(line) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)
    return chunks


def send_telegram(text: str, *, disable_preview: bool = True, timeout: float = 10.0) -> bool:
    """Deliver ``text`` to the configured chat. Returns True iff fully delivered.

    No-ops (returns False) when not configured. Splits over-long messages and
    swallows any network/HTTP error so a failed ping can never crash the bot.
    """
    if not telegram_enabled():
        return False
    import requests  # local import: keeps module import cheap + test-friendly

    token, chat_id = _token(), _chat_id()
    url = _API.format(token=token)
    ok = True
    for chunk in _split(text):
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": disable_preview,
                },
                timeout=timeout,
            )
            if resp.status_code != 200:
                log.warning("telegram sendMessage HTTP %s: %s", resp.status_code, resp.text[:200])
                ok = False
        except Exception as exc:  # noqa: BLE001 — never let a ping break the run
            log.warning("telegram send failed: %s", exc)
            ok = False
    return ok
