"""Two-way Telegram command handlers (paper-only) for the /api/telegram webhook.

Lets the owner drive the bot FROM Telegram:
  Tier 1 (read-only): /status /score /positions
  Tier 2 (trigger):   /scan (fire the GitHub paper-trade run), /summary
  Tier 3 (paper log): /trade SYMBOL DIR PRICE  ->  /yes | /cancel  (60s gate)

SECURITY / SCOPE (hard rules):
  - The webhook (api.py) verifies the Telegram secret header AND the chat-id
    whitelist BEFORE any handler runs; only the owner's chat can trigger anything.
  - NOTHING here ever calls an exchange or places a real order. A /trade is logged
    as a PAPER bracket through the SAME audited path as /api/alert
    (alert_inbox.inbox_entry + log_alert + push_inbox_entry), tagged "tg_manual",
    so the hourly Action ingests and scores it durably (the host journal is
    ephemeral — see alert_inbox.py).
  - The confirmation gate is one-time and expires in 60s; /yes consumes it.

Handlers are plain functions so they unit-test offline (inject a journal / fake
client). The webhook wires them up in api.py.
"""
from __future__ import annotations

import os
import time

from .alert_inbox import inbox_entry, log_alert, push_inbox_entry
from .journal import TradeJournal
from .notifications import send_telegram
from .notifications.notify import _g, format_summary
from .review import open_trades_report
from .scorecard import today_autopsy
from .universe import TOP_10_CRYPTO

# In-memory state (single-process, single-user). Intentionally NOT persisted —
# a Render restart clears a pending confirmation, which is safe (it just expires).
PENDING_TRADES: dict[str, dict] = {}     # chat_id -> {symbol, side, direction, price, stop, target, ts}
_LAST_SCAN: dict[str, float] = {}        # chat_id -> last /scan epoch (rate limit)

_PENDING_TTL = 60.0          # seconds a /trade confirmation stays valid
_SCAN_COOLDOWN = 300.0       # min seconds between /scan per chat
_STOP_PCT = 0.005            # default 0.5% stop (no live ATR available in-process)
_GH_API = "https://api.github.com"


# ── Tier 1: read-only ────────────────────────────────────────────────────────

def _position_lines(report: dict, journal: TradeJournal) -> list[str]:
    """One line per open trade: 'SOLUSDT LONG @ 72.87 | 4h | est +0.8R'."""
    by_id = {t["id"]: t for t in report.get("trades", [])}
    lines = []
    for p in journal.predictions:
        if p.status not in ("open", "pending") or p.kind != "bracket":
            continue
        t = by_id.get(p.id, {})
        side = "LONG" if (p.direction or 0) > 0 else "SHORT"
        r = t.get("unrealized_r")
        rtxt = f"{r:+.1f}R" if r is not None else "n/a"
        hrs = t.get("time_in_trade_hours")
        htxt = f"{hrs:.0f}h" if hrs else "—"
        book = p.setup or ""
        tag = f" #{book}" if book else ""
        lines.append(f"{p.symbol} {side} @ {_g(p.entry)} | {htxt} | est {rtxt}{tag}")
    return lines


def cmd_status(journal: TradeJournal, client=None) -> str:
    """Portfolio summary + each open position (open count, unrealized R, risk)."""
    report = open_trades_report(journal, client)
    summary = format_summary(report, realized_today=today_autopsy(journal))
    lines = _position_lines(report, journal)
    return summary + ("\n\n" + "\n".join(lines) if lines else "")


def cmd_positions(journal: TradeJournal, client=None) -> str:
    """Full open book, one line per trade."""
    report = open_trades_report(journal, client)
    lines = _position_lines(report, journal)
    return "📋 Open positions:\n" + "\n".join(lines) if lines else "No open positions."


def cmd_score(journal: TradeJournal) -> str:
    """Today's closed trades, net R, best/worst (NY-day window, net of fees)."""
    a = today_autopsy(journal)
    if not a.get("n"):
        return "Today: no closed trades yet."
    parts = [f"Today: {a['r']:+.2f}R on {a['n']} closed"]
    best, worst = a.get("best"), a.get("worst")
    if best:
        parts.append(f"Best: {best[0]} {best[1]:+.2f}R")
    if worst and worst != best:
        parts.append(f"Worst: {worst[0]} {worst[1]:+.2f}R")
    return " | ".join(parts)


# ── Tier 2: trigger ──────────────────────────────────────────────────────────

def cmd_scan(chat_id: str) -> str:
    """Fire workflow_dispatch on paper-trade.yml (same call the Cloudflare worker
    makes). Rate-limited to 1 per 5 min per chat."""
    now = time.time()
    wait = _SCAN_COOLDOWN - (now - _LAST_SCAN.get(chat_id, 0.0))
    if wait > 0:
        return f"⏳ Scan rate-limited — try again in {int(wait)}s."
    token = os.environ.get("KUDBEE_GH_TOKEN", "")
    if not token:
        return "❌ Scan unavailable: KUDBEE_GH_TOKEN not configured."
    repo = os.environ.get("KUDBEE_GH_REPO", "KudbeeZero/Kudbee-Quant-Bot-v1.0")
    ref = os.environ.get("KUDBEE_GH_BRANCH", "main")
    try:
        import requests
        r = requests.post(
            f"{_GH_API}/repos/{repo}/actions/workflows/paper-trade.yml/dispatches",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"},
            json={"ref": ref}, timeout=8,
        )
    except Exception as e:  # noqa: BLE001
        return f"❌ Dispatch error: {type(e).__name__}"
    if r.status_code == 204:
        _LAST_SCAN[chat_id] = now
        return "✅ Scan triggered — results in a minute."
    return f"❌ Dispatch failed: {r.status_code}"


def cmd_summary() -> str:
    """Force the hourly Telegram summary now (sends to the configured chat)."""
    from .notifications import notify_summary
    return "✅ Summary sent." if notify_summary() else "❌ Summary failed (Telegram not configured?)."


# ── Tier 3: paper trade logging with a confirmation gate ─────────────────────

def cmd_trade(text: str, chat_id: str) -> str:
    """Parse '/trade SYMBOL LONG|SHORT PRICE', stage a pending PAPER bracket."""
    parts = text.split()
    if len(parts) != 4:
        return "Usage: /trade SYMBOL LONG|SHORT PRICE   (e.g. /trade SOLUSDT LONG 72.87)"
    _, sym, side, price_s = parts
    sym, side = sym.upper(), side.upper()
    if sym not in TOP_10_CRYPTO:
        return f"❌ Unknown symbol {sym}. Allowed: {', '.join(TOP_10_CRYPTO)}."
    if side not in ("LONG", "SHORT"):
        return "❌ Direction must be LONG or SHORT."
    try:
        price = float(price_s)
    except ValueError:
        return "❌ Price must be a number."
    if price <= 0:
        return "❌ Price must be positive."
    direction = 1.0 if side == "LONG" else -1.0
    stop = price * (1 - _STOP_PCT) if direction > 0 else price * (1 + _STOP_PCT)
    risk = abs(price - stop)
    target = price + 3.0 * risk * direction
    PENDING_TRADES[chat_id] = {"symbol": sym, "side": side, "direction": direction,
                               "price": price, "stop": stop, "target": target, "ts": time.time()}
    return ("⚠️ Paper trade:\n"
            f"{sym} {side} @ {_g(price)}\n"
            f"Stop: {_g(stop)} | Target: {_g(target)} (~3.0R)\n"
            "Reply /yes to log or /cancel to abort\n"
            "(expires in 60s)")


def cmd_yes(chat_id: str, journal: TradeJournal | None = None) -> str:
    """Confirm + log the pending paper trade. PAPER ONLY — never an exchange call."""
    pend = PENDING_TRADES.get(chat_id)
    if not pend:
        return "No pending trade. Use /trade first."
    if time.time() - pend["ts"] > _PENDING_TTL:
        PENDING_TRADES.pop(chat_id, None)
        return "⏱ Confirmation expired. Re-enter /trade to retry."
    alert = {"symbol": pend["symbol"], "direction": pend["direction"],
             "entry": pend["price"], "stop": pend["stop"], "target": pend["target"],
             "target_r": 3.0, "tf": "1h", "note": "Telegram manual entry",
             "setup": "tg_manual"}
    j = journal or TradeJournal()
    try:
        entry = inbox_entry(alert)
        p = log_alert(j, alert, entry["id"])          # host-local journal (instant)
    except Exception as e:  # noqa: BLE001 — never silently succeed on a write failure
        return f"❌ Failed to log trade: {type(e).__name__}: {e}"
    PENDING_TRADES.pop(chat_id, None)
    if p is None:
        return f"⚠️ Not logged — already in a trade on {pend['symbol']} 1h."
    pushed = push_inbox_entry(entry)                  # durable -> Action ingests & scores
    tail = "" if pushed else " (host-local only — set KUDBEE_GH_TOKEN to score it)"
    return f"✅ Paper trade logged: {pend['symbol']} {pend['side']} @ {_g(pend['price'])} | #tg_manual{tail}"


def cmd_cancel(chat_id: str) -> str:
    PENDING_TRADES.pop(chat_id, None)
    return "🚫 Trade cancelled."


def cmd_help() -> str:
    return ("Kudbee commands (paper-only):\n"
            "/status — open positions + unrealized R\n"
            "/score — today's closed trades\n"
            "/positions — full open book\n"
            "/scan — trigger a fresh scan now\n"
            "/summary — force the hourly summary now\n"
            "/trade SYMBOL LONG|SHORT PRICE — log a paper trade (confirmation required)\n"
            "/yes — confirm pending trade\n"
            "/cancel — cancel pending trade\n"
            "/help — this menu")


# ── webhook glue (gate 1 + dispatch + reply) ─────────────────────────────────

def dispatch(text: str, chat_id: str, journal: TradeJournal | None = None) -> str:
    """Route a '/command ...' line to its handler and return the reply text."""
    j = journal or TradeJournal()
    cmd = text.split()[0].lower().split("@")[0]      # tolerate /cmd@botname
    table = {
        "/status": lambda: cmd_status(j),
        "/score": lambda: cmd_score(j),
        "/positions": lambda: cmd_positions(j),
        "/scan": lambda: cmd_scan(chat_id),
        "/summary": lambda: cmd_summary(),
        "/trade": lambda: cmd_trade(text, chat_id),
        "/yes": lambda: cmd_yes(chat_id, j),
        "/cancel": lambda: cmd_cancel(chat_id),
        "/help": lambda: cmd_help(),
    }
    return table.get(cmd, lambda: "Unknown command. Try /help.")()


def handle_update(body: dict, *, journal: TradeJournal | None = None, sender=None) -> str | None:
    """Gate 1 (chat-id whitelist) + dispatch + send the reply. Returns the reply
    text (or None if dropped). The webhook-secret gate (Gate 2) lives in api.py."""
    message = body.get("message") or body.get("edited_message") or {}
    chat_id = str((message.get("chat") or {}).get("id", ""))
    text = (message.get("text") or "").strip()
    if not chat_id or chat_id != os.environ.get("TELEGRAM_CHAT_ID", ""):
        return None                                   # silent drop — not the owner
    if not text.startswith("/"):
        return None
    reply = dispatch(text, chat_id, journal=journal)
    (sender or send_telegram)(reply)
    return reply
