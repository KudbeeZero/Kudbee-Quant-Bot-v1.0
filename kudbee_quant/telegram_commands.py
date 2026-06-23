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
from .intelligence.d1_client import d1_query
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


# ── TR Level Intelligence (read-only D1 lookups) ─────────────────────────────

def _fmt(val) -> str:
    """Format a price level for Telegram."""
    if val is None:
        return "—"
    try:
        return f"{float(val):.4f}"
    except (TypeError, ValueError):
        return str(val)


def cmd_levels(text: str) -> str:
    """/levels SYMBOL — today's full TR level grid (latest row for the symbol)."""
    parts = text.strip().split()
    if len(parts) < 2:
        return "Usage: /levels SYMBOL (e.g. /levels SOLUSDT)"
    symbol = parts[1].upper()

    try:
        rows = d1_query("""
            SELECT * FROM daily_levels
            WHERE symbol = ?
            ORDER BY recorded_at DESC LIMIT 1
        """, [symbol])
    except Exception as e:  # noqa: BLE001 — D1 outage must not 500 the webhook
        return f"⚠️ Level lookup unavailable: {type(e).__name__}"
    if not rows:
        return f"No level data for {symbol}. Runs after the next scan."

    r = rows[0]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow = r.get("day_of_week")
    dow_txt = days[int(dow)] if dow is not None else "—"
    cloud = r.get("ema_cloud_pos")
    cloud_txt = ("↑ above" if cloud == 1 else "↓ below" if cloud == -1 else "→ inside")
    prev = "🟢" if r.get("prev_day_color") == 1 else "🔴"
    return (
        f"📊 TR Levels — {symbol} ({r['date']})\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"M5: {_fmt(r['mlevel_m5'])}  R3: {_fmt(r['pivot_r3'])}\n"
        f"M4: {_fmt(r['mlevel_m4'])}  R2: {_fmt(r['pivot_r2'])}\n"
        f"M3: {_fmt(r['mlevel_m3'])}  R1: {_fmt(r['pivot_r1'])}\n"
        f"PP: {_fmt(r['pivot_pp'])}\n"
        f"M2: {_fmt(r['mlevel_m2'])}  S1: {_fmt(r['pivot_s1'])}\n"
        f"M1: {_fmt(r['mlevel_m1'])}  S2: {_fmt(r['pivot_s2'])}\n"
        f"M0: {_fmt(r['mlevel_m0'])}  S3: {_fmt(r['pivot_s3'])}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Daily Open:  {_fmt(r['daily_open'])}\n"
        f"Asia H/L:    {_fmt(r['asian_high'])} / {_fmt(r['asian_low'])}\n"
        f"Brinks(LDN): {_fmt(r['brinks_high'])} / {_fmt(r['brinks_low'])}\n"
        f"Brinks(NY):  {_fmt(r['ny_brinks_high'])} / {_fmt(r['ny_brinks_low'])}\n"
        f"ADR H/L:     {_fmt(r['adr_high'])} / {_fmt(r['adr_low'])}\n"
        f"PDH/PDL:     {_fmt(r['pdh'])} / {_fmt(r['pdl'])}\n"
        f"EMA 5/13/50: {_fmt(r['ema_5'])} / {_fmt(r['ema_13'])} / {_fmt(r['ema_50'])}\n"
        f"Cloud: {cloud_txt}\n"
        f"DOW: {dow_txt}  Prev day: {prev}"
    )


def cmd_history(text: str) -> str:
    """/history SYMBOL — daily open + Asia H/L + PP for the last 7 days."""
    parts = text.strip().split()
    if len(parts) < 2:
        return "Usage: /history SYMBOL"
    symbol = parts[1].upper()

    try:
        rows = d1_query("""
            SELECT date, daily_open, asian_high, asian_low,
                   pdh, pdl, pivot_pp, prev_day_color, day_of_week
            FROM daily_levels
            WHERE symbol = ?
            GROUP BY date
            ORDER BY date DESC LIMIT 7
        """, [symbol])
    except Exception as e:  # noqa: BLE001
        return f"⚠️ History lookup unavailable: {type(e).__name__}"
    if not rows:
        return f"No history for {symbol} yet."

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    lines = [f"📅 Level History — {symbol}"]
    for r in rows:
        dow = r.get("day_of_week")
        dow_txt = days[int(dow)] if dow is not None else "—"
        color = "🟢" if r.get("prev_day_color") == 1 else "🔴"
        lines.append(
            f"{r['date']} {dow_txt} {color} | "
            f"Open:{_fmt(r['daily_open'])} "
            f"Asia:{_fmt(r['asian_high'])}/{_fmt(r['asian_low'])} "
            f"PP:{_fmt(r['pivot_pp'])}"
        )
    return "\n".join(lines)


def cmd_vectors(text: str) -> str:
    """/vectors SYMBOL — unrecovered climax candles (price magnets still open)."""
    parts = text.strip().split()
    if len(parts) < 2:
        return "Usage: /vectors SYMBOL"
    symbol = parts[1].upper()

    try:
        rows = d1_query("""
            SELECT candle_type, candle_high, candle_low,
                   body_close, days_open, candle_time
            FROM unrecovered_vectors
            WHERE symbol = ? AND active = 1
            ORDER BY days_open DESC LIMIT 10
        """, [symbol])
    except Exception as e:  # noqa: BLE001
        return f"⚠️ Vector lookup unavailable: {type(e).__name__}"
    if not rows:
        return f"✅ No unrecovered vectors for {symbol}."

    lines = [f"🧲 Unrecovered Vectors — {symbol}"]
    for r in rows:
        icon = "🟢" if r["candle_type"] == "bull_climax" else "🔴"
        zone = f"{_fmt(r['candle_low'])}–{_fmt(r['candle_high'])}"
        days_open = r.get("days_open")
        days_txt = f"{days_open}d ago" if days_open is not None else "—"
        lines.append(
            f"{icon} {r['candle_type']} @ {zone} | "
            f"{days_txt} | {str(r['candle_time'])[:10]}"
        )
    lines.append(f"\nTotal active: {len(rows)}")
    return "\n".join(lines)


def cmd_help() -> str:
    return ("Kudbee commands (paper-only):\n"
            "/status — open positions + unrealized R\n"
            "/score — today's closed trades\n"
            "/positions — full open book\n"
            "/scan — trigger a fresh scan now\n"
            "/summary — force the hourly summary now\n"
            "/levels SYMBOL — full TR level grid (M0-M5, PP, Asia, Brinks, EMA)\n"
            "/history SYMBOL — daily open + Asia H/L for last 7 days\n"
            "/vectors SYMBOL — unrecovered climax candles (price magnets)\n"
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
        "/levels": lambda: cmd_levels(text),
        "/history": lambda: cmd_history(text),
        "/vectors": lambda: cmd_vectors(text),
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
