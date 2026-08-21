"""Poll Telegram for slash commands — the no-server command path (§86).

Slash commands normally arrive via the webhook → the FastAPI app — but until the
API is deployed (CROSSROADS X2 step 3) Telegram has nowhere to deliver them and
every command dies silently. This module answers them from a GitHub Actions cron
instead, using ``getUpdates`` long-polling semantics in one-shot mode:

  1. **Stand down when a webhook exists.** Telegram forbids ``getUpdates`` while
     a webhook is registered, so the first check is ``getWebhookInfo`` — once the
     Fly deploy + register workflow set the webhook, this becomes a silent no-op
     and the instant webhook path takes over. No flag to flip, no race.
  2. Fetch pending updates, run each through the SAME gate + dispatch the webhook
     uses (:func:`telegram_commands.handle_update` — chat-id whitelist, admin
     gate, reply via ``send_telegram``). No second command implementation.
  3. **Ack** by calling ``getUpdates`` again with ``offset = last_update_id + 1``:
     Telegram then drops the confirmed updates server-side, so the workflow needs
     NO local offset state between runs (updates are held ~24h either way).

Latency is the cron interval (~10 min best-effort), not instant — the honest
trade for needing zero servers. Never raises: a Telegram/API hiccup returns 0
and the next cron retries.
"""
from __future__ import annotations

import os

import requests

_API = "https://api.telegram.org"


def _bot_token() -> str | None:
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return tok or None


def _get(method: str, token: str, **params):
    """GET a Telegram method, returning the parsed JSON body.

    Always returns a dict (``{}`` on transport error) AND surfaces Telegram's own
    error envelope via ``ok``/``description`` — callers must check ``ok`` (a proxy
    HTML 200 or an HTTP error still parses to ``{}`` here, and Telegram returns
    HTTP 409 with ``ok:false`` when two pollers overlap, which we must not swallow).
    """
    try:
        r = requests.get(f"{_API}/bot{token}/{method}", params=params, timeout=20)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "description": f"transport error: {type(exc).__name__}"}
    body = {}
    try:
        body = r.json()
    except ValueError:
        return {"ok": False, "description": f"non-JSON response HTTP {r.status_code}"}
    if not body.get("ok"):
        body.setdefault("ok", False)
    return body


def webhook_active(token: str) -> bool:
    """True when a webhook URL is registered (polling must stand down)."""
    info = _get("getWebhookInfo", token)
    return bool((info.get("result") or {}).get("url"))


def poll_once(*, handler=None) -> int:
    """One fetch→dispatch→ack cycle. Returns the number of updates processed.

    ``handler`` overrides :func:`telegram_commands.handle_update` in tests.
    """
    token = _bot_token()
    if not token:
        print("telegram-poll: TELEGRAM_BOT_TOKEN not set — nothing to poll.")
        return 0
    if webhook_active(token):
        print("telegram-poll: a webhook is registered — polling stands down "
              "(the webhook path owns command delivery now).")
        return 0

    if handler is None:
        from .telegram_commands import handle_update
        handler = handle_update

    resp = _get("getUpdates", token, timeout=0, allowed_updates='["message"]')
    if resp.get("ok") is False:
        desc = resp.get("description", "unknown error")
        # Telegram forbids getUpdates while a webhook (or another poller) owns the
        # connection — 409 "conflict". Stand down cleanly; the next cron retries.
        if "conflict" in desc.lower():
            print(f"telegram-poll: conflict ({desc}) — another poller/webhook owns "
                  f"getUpdates; standing down this run.")
            return 0
        print(f"telegram-poll: getUpdates failed: {desc}")
        return 0

    updates = resp.get("result") or []
    handled = 0
    last_id = None
    for u in updates:
        last_id = u.get("update_id", last_id)
        try:
            if handler(u) is not None:
                handled += 1
        except Exception as exc:  # noqa: BLE001 — one bad update must not block the rest
            print(f"telegram-poll: update {u.get('update_id')} failed: {type(exc).__name__}")
    if last_id is not None:
        # Confirm everything up to last_id so Telegram drops it server-side —
        # the next run starts clean with no local offset file to persist.
        _get("getUpdates", token, offset=last_id + 1, limit=1, timeout=0)
    print(f"telegram-poll: {len(updates)} update(s) fetched, {handled} command(s) answered.")
    return handled


def _main(argv=None) -> int:  # pragma: no cover — thin CLI shim
    poll_once()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
