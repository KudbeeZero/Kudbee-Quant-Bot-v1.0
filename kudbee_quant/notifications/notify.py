"""Message formatting + the high-level hooks the CLI calls.

Formatters are pure (Prediction/report dict in, ``str`` out) so they're trivially
unit-tested with no network. The ``notify_*`` wrappers add the only side effect —
a :func:`send_telegram` call, guarded by :func:`telegram_enabled` and wrapped so
they never raise.
"""
from __future__ import annotations

import datetime
import os
import re
import time
from typing import TYPE_CHECKING

from .telegram import send_telegram, telegram_enabled

if TYPE_CHECKING:  # type-only import; no runtime cost / cycle
    from ..journal import Prediction

# Keep batch messages readable — list at most this many trades, then summarise.
_MAX_LINES = 25


def _session_name() -> str:
    """Coarse trading-session label from the current UTC hour (cosmetic)."""
    h = datetime.datetime.now(datetime.timezone.utc).hour
    if 0 <= h < 8:
        return "Asia session"
    if 8 <= h < 13:
        return "London session"
    if 13 <= h < 21:
        return "NY session"
    return "London close"


def _why_fired(note, setup) -> list:
    """Honest 'why this fired' bullets DERIVED from the trade's own note/setup —
    no per-trade claims invented; each line is only added when the note states it."""
    lines = []
    n = (note or "").lower()
    s = setup or ""
    m = re.search(r"(\d+)%\s*confluence.*?strength\s*(\d+)", n)
    if m:
        lines.append(f"▸ {m.group(2)} confluence factors checked — {m.group(1)}% gate cleared")
    m2 = re.search(r"retrace\s*([\d.]+)\s*atr", n)
    if m2:
        lines.append(f"▸ Limit entry — {m2.group(1)} ATR pullback before fill  (maker-side)")
    elif "retrace" in n:
        lines.append("▸ Limit entry — waited for pullback before filling")
    if "_cts" in s:
        lines.append("▸ EMA 5 / 13 / 50 stack aligned  (clean trend stack confirmed)")
    if "maker" in n:
        lines.append("▸ Maker-favorable fill — no chasing")
    return lines


def _side(p: "Prediction") -> str:
    return "LONG" if p.direction > 0 else ("SHORT" if p.direction < 0 else "FLAT")


def _g(x: float | None) -> str:
    """Compact price format — never scientific notation on mobile."""
    if x is None:
        return "?"
    if abs(x) >= 1_000:
        return f"{x:,.0f}"   # 64170 -> "64,170"  |  1735 -> "1,735"
    if abs(x) >= 1:
        return f"{x:.4g}"    # 591.3 -> "591.3"
    return f"{x:.5g}"        # 0.08349 -> "0.08349"  (DOGE etc)


def _book_tag(setup: str | None) -> str:
    """Short label for the experiment 'book' so pings are distinguishable on mobile:
    §C clean-trend-stack -> [trend], §A long-only -> [longs]; baseline -> ''."""
    s = setup or ""
    if "_cts" in s:
        return " [trend]"
    if "_lo" in s:
        return " [longs]"
    return ""


def _book_label(setup: str | None) -> str:
    """Human bucket for the per-book summary breakdown. The validated book is
    'core'; the separately-tagged experiments split out (§C '_cts' -> trend,
    §A '_lo' -> longs, tradfi venue -> tradfi)."""
    s = setup or ""
    if "_cts" in s:
        return "trend"
    if "_lo" in s:
        return "longs"
    if "_tradfi" in s:
        return "tradfi"
    return "core"


# Stable display order for the book breakdown (validated book first).
_BOOK_ORDER = ("core", "trend", "longs", "tradfi")


def _opened_line(p: "Prediction") -> str:
    pend = " (limit pending)" if getattr(p, "pending_limit", False) else ""
    tr = f" {p.target_r:g}R" if getattr(p, "target_r", None) is not None else ""
    return (f"• {_side(p)} {p.symbol} [{p.timeframe}]{_book_tag(getattr(p, 'setup', None))} "
            f"entry {_g(p.entry)} stop {_g(p.stop)} target {_g(p.target)}{tr}{pend}")


def format_trades_opened(preds: list["Prediction"]) -> str:
    """One batched message for newly logged setups (paper scan / ingested alert)."""
    n = len(preds)
    head = f"📈 {n} new trade setup{'s' if n != 1 else ''} logged"
    lines = [_opened_line(p) for p in preds[:_MAX_LINES]]
    if n > _MAX_LINES:
        lines.append(f"…and {n - _MAX_LINES} more")
    return "\n".join([head, *lines])


def _resolved_line(p: "Prediction") -> str:
    icon = {"hit": "◆", "miss": "◇", "cancelled": "—"}.get(p.status, "•")
    r = getattr(p, "outcome_r", None)
    rtxt = f" {r:+.2f}R" if r is not None else ""
    label = {"hit": "TARGET", "miss": "STOPPED", "cancelled": "cancelled"}.get(p.status, p.status)
    return f"{icon} {p.symbol} [{p.timeframe}] {_side(p)} {label}{rtxt}"


def format_trades_resolved(preds: list["Prediction"]) -> str:
    """One batched message for trades that just closed (hit / miss / cancelled)."""
    closed = [p for p in preds if p.status in ("hit", "miss", "cancelled")]
    n = len(closed)
    realized = sum(p.outcome_r for p in closed if getattr(p, "outcome_r", None) is not None)
    head = f"🔔 {n} trade{'s' if n != 1 else ''} resolved ({realized:+.2f}R total)"
    lines = [_resolved_line(p) for p in closed[:_MAX_LINES]]
    if n > _MAX_LINES:
        lines.append(f"…and {n - _MAX_LINES} more")
    return "\n".join([head, *lines])


def _book_breakdown_line(trades: list[dict]) -> str | None:
    """`By book: core 3 (+0.4R) • trend 1 (+0.1R)` — open count + unrealized R per
    book, validated 'core' first. None when there are no open trades to split."""
    if not trades:
        return None
    agg: dict[str, list[float]] = {}
    for t in trades:
        b = agg.setdefault(_book_label(t.get("setup")), [0.0, 0.0])  # [count, sum_r]
        b[0] += 1
        ur = t.get("unrealized_r")
        if ur is not None:
            b[1] += ur
    if len(agg) < 2:
        return None  # one book -> the headline already says it; don't be noisy
    books = sorted(agg, key=lambda b: (_BOOK_ORDER.index(b) if b in _BOOK_ORDER else 99, b))
    return "By book: " + "  •  ".join(
        f"{b} {int(agg[b][0])} ({agg[b][1]:+.2f}R)" for b in books)


def _best_worst_line(trades: list[dict]) -> str | None:
    """`Best: ETH +1.2R (+3.1%) • Worst: SOL -0.6R (-1.4%)` over marked open trades."""
    marked = [t for t in trades if t.get("unrealized_r") is not None]
    if not marked:
        return None
    best = max(marked, key=lambda t: t["unrealized_r"])
    worst = min(marked, key=lambda t: t["unrealized_r"])

    def _bit(t: dict) -> str:
        pct = t.get("pnl_pct")
        pct_txt = "" if pct is None else f" ({pct:+.1f}%)"
        return f"{t['symbol']} {t['unrealized_r']:+.2f}R{pct_txt}"

    if best is worst:
        return f"Open: {_bit(best)}"
    return f"Best: {_bit(best)}  •  Worst: {_bit(worst)}"


def _deadline_line(trades: list[dict], *, soon_hours: float = 6.0) -> str | None:
    """`⏰ Expiring: SOL 2.1h • overdue: XRP` — open trades at/over their deadline
    (overdue) or within ``soon_hours`` of it, so nothing rots unresolved. None when
    nothing is close. Trades with no deadline info are skipped."""
    overdue, soon = [], []
    for t in trades:
        h = t.get("hours_to_deadline")
        if h is None:
            continue
        if h <= 0:
            overdue.append(t["symbol"])
        elif h <= soon_hours:
            soon.append((t["symbol"], h))
    if not overdue and not soon:
        return None
    bits = []
    if soon:
        soon.sort(key=lambda x: x[1])
        bits.append("Expiring: " + ", ".join(f"{s} {h:.1f}h" for s, h in soon))
    if overdue:
        bits.append("overdue: " + ", ".join(dict.fromkeys(overdue)))
    return "⏰ " + "  •  ".join(bits)


# A book down at least this much R since the day open gets a 🛑 cut-watch flag.
_CUT_WATCH_R = -3.0


def _today_breakdown_lines(today: dict) -> list[str]:
    """The daily-autopsy lines under 'Today:' — which book dragged, the single
    best/worst trade, and a cut-watch flag for any book bleeding hard today. All
    gated on the richer keys (by_book/best/worst) so older callers are unaffected."""
    out: list[str] = []
    by_book = today.get("by_book") or {}
    if len(by_book) >= 2:
        items = sorted(by_book.items(), key=lambda kv: kv[1]["r"])   # worst book first
        out.append("Today by book: " + "  •  ".join(
            f"{b} {v['r']:+.1f}R" for b, v in items))
    best, worst = today.get("best"), today.get("worst")
    if best and worst and best != worst:
        out.append(f"Today best: {best[0]} {best[1]:+.2f}R  •  "
                   f"worst: {worst[0]} {worst[1]:+.2f}R")
    bleeding = sorted((f"{b} {v['r']:+.1f}R" for b, v in by_book.items()
                       if v["r"] <= _CUT_WATCH_R))
    if bleeding:
        out.append("△ Cut watch (today): " + ", ".join(bleeding))
    return out


def format_summary(report: dict, *, record: dict | None = None,
                   realized_today: dict | None = None,
                   schedule_health: dict | None = None,
                   delta_line: str | None = None) -> str:
    """Portfolio snapshot from :func:`review.open_trades_report` (+ optional record).

    ``report`` is the dict that function returns; ``record`` is an optional
    ``{venue: {...}}`` map from ``TradeJournal.venue_record`` for a one-line
    track-record footer. ``realized_today`` is an optional ``{"r": float, "n": int}``
    of fee-net R closed since the New York open (08:00 NY — see :func:`_realized_today`).
    ``schedule_health`` is an optional heartbeat dict (see
    :mod:`notifications.heartbeat`) — when runs are being dropped it adds a visible
    warning line so a silent scheduler can't masquerade as 'nothing to report'.
    """
    p = report.get("portfolio", {})
    trades = report.get("trades", []) or []
    n = p.get("total_open", 0)
    usd = p.get("total_unrealized_usd")
    usd_txt = "" if usd is None else f" / {usd:+.2f} USD"
    winners, losers = p.get("winners_open", 0), p.get("losers_open", 0)
    # Opens with no live mark are unfilled/unpriced (pending limits); a mark of
    # exactly 0 is flat. Neither is "up" or "down", so count them explicitly —
    # otherwise the Up/Down tally silently drops them and won't reconcile with n.
    pending = sum(1 for t in trades if t.get("unrealized_r") is None)
    flat = sum(1 for t in trades if t.get("unrealized_r") == 0)
    # Only claim "all in profit" when EVERY open is a marked winner — not merely
    # "no losers" (which is also true while trades sit pending/unfilled).
    green_tag = "  ·  all in profit ◆" if winners == n and n > 0 else ""
    ud = f"Up / Down   {winners} ▸ {losers}"
    extra = [f"{c} {label}" for c, label in ((flat, "flat"), (pending, "pending")) if c]
    if extra:
        ud += "  ·  " + ", ".join(extra)
    lines = ["⬡ KUDBEE QUANT — Live Read"]
    # One-line "since last read" delta header (read-only event layer) so an
    # outside observer sees WHAT changed, not just bouncing snapshots.
    if delta_line:
        lines.append(delta_line)
    lines += [
        f"◇ {n} open{green_tag}  ·  {p.get('total_unrealized_r', 0):+.2f}R unrealized{usd_txt}",
        f"{ud}  ·  Risk {p.get('total_open_risk_pct', 0):.1f}% of account",
    ]
    book_line = _book_breakdown_line(trades)
    if book_line:
        lines.append(book_line)
    bw_line = _best_worst_line(trades)
    if bw_line:
        lines.append(bw_line)
    dl_line = _deadline_line(trades)
    if dl_line:
        lines.append(dl_line)
    if realized_today and realized_today.get("n"):
        lines.append(f"Today: {realized_today.get('r', 0):+.2f}R on "
                     f"{realized_today['n']} closed")
        lines.extend(_today_breakdown_lines(realized_today))
    if p.get("closest_to_stop") or p.get("closest_to_tp"):
        lines.append(f"Closest to stop: {p.get('closest_to_stop') or '—'}  •  "
                     f"closest to target: {p.get('closest_to_tp') or '—'}")
    if p.get("warnings"):
        lines.append("⚠ " + "; ".join(p["warnings"]))
    if schedule_health is not None:
        from .heartbeat import health_line
        hl = health_line(schedule_health)
        if hl:
            lines.append(hl)
    if record:
        bits = [f"{v} {r['hits']}/{r['n']} ({r['net_expectancy_r']:+.2f}R net)"
                for v, r in record.items() if r.get("n")]
        if bits:
            lines.append("Record: " + "  ".join(bits))
    return "\n".join(lines)


def _realized_today(predictions: list["Prediction"]) -> dict:
    """``{"r": fee-net R, "n": closes}`` for trades resolved since the current trading
    day began — the most recent **New York open (08:00 NY)**, NOT UTC midnight, so the
    day rolls when the session does (matches the desk's day / the Asia-open alerts).
    Uses :func:`net_outcome_r` (after-fee). Unparseable/unresolved records are skipped."""
    from datetime import datetime, timezone
    from ..journal import net_outcome_r
    from ..context.calendar import session_day_start

    start = session_day_start()
    rs: list[float] = []
    for p in predictions:
        if p.status not in ("hit", "miss", "cancelled") or not p.resolved_at:
            continue
        try:
            dt = datetime.fromisoformat(p.resolved_at)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt < start:
            continue
        nr = net_outcome_r(p)
        if nr is not None:
            rs.append(nr)
    return {"r": round(sum(rs), 2), "n": len(rs)}


# --- high-level hooks (guarded + non-raising) -------------------------------

def notify_trades_opened(preds: list["Prediction"]) -> bool:
    if not preds or not telegram_enabled():
        return False
    return send_telegram(format_trades_opened(preds))


def notify_trades_resolved(preds: list["Prediction"]) -> bool:
    closed = [p for p in preds if p.status in ("hit", "miss", "cancelled")]
    if not closed or not telegram_enabled():
        return False
    return send_telegram(format_trades_resolved(closed))


def notify_summary(only_if_open: bool = False) -> bool:
    """Build + send the portfolio snapshot. Returns False if muted or on error.

    ``only_if_open``: skip sending when there are NO open positions — used by the
    dense (every-5-min) open-position reminder so it pings while you hold trades but
    stays silent when flat (no spam)."""
    if not telegram_enabled():
        return False
    try:
        from ..journal import TradeJournal
        from ..review import open_trades_report
        j = TradeJournal()
        report = open_trades_report(journal=j)
        if only_if_open and report.get("portfolio", {}).get("total_open", 0) == 0:
            return False
        # Read-only event + delta layer: ping intra-trade transitions (approaching
        # stop, warning cleared, recovered, slipped) and build the "since last read"
        # header by diffing the persisted snapshot. Wrapped so it can never break the
        # summary, and it touches nothing on the trading path.
        #
        # Runs ONLY on the hourly committing read (``only_if_open`` False). The
        # every-5-min reminder (paper-status.yml) passes ``only_if_open=True`` and
        # commits nothing, so its snapshot-save would be ephemeral — it would
        # re-detect (and re-ping) the same transition every 5 min until the next
        # hourly commit advances the baseline. Gating on the committing path keeps
        # "since last read" anchored to the last hourly read and fires each event once.
        delta_line = None
        if not only_if_open:
            try:
                from . import events as ev
                prev = ev.load_state()
                curr = ev.snapshot(report)
                for e in ev.diff_events(prev, curr):
                    send_telegram(ev.format_event(e))
                delta_line = ev.delta_summary(prev, curr) or None
                ev.save_state(curr)
            except Exception:  # noqa: BLE001 — the event layer must never break the read
                delta_line = None
        record = {v: r for v, r in j.venue_record().items() if r["n"]}
        from ..scorecard import today_autopsy           # richer "Today" (by book + best/worst)
        realized = today_autopsy(j)
        from .heartbeat import load_health               # read-only run-health line
        health = load_health()
        return send_telegram(format_summary(report, record=record or None,
                                            realized_today=realized,
                                            schedule_health=health,
                                            delta_line=delta_line))
    except Exception:  # noqa: BLE001 — a summary failure must not break the run
        return False


def notify_scan_blocked(event_name: str, hours_until: float) -> bool:
    """Ping that the scanner SKIPPED a scan because of binary-event risk.

    Lets the Telegram channel know WHY no setups fired (a silent skip is
    indistinguishable from 'nothing set up'). No-op when Telegram isn't
    configured — :func:`send_telegram` self-guards on :func:`telegram_enabled` —
    and never raises (a ping must never break a scan).
    """
    when = f"in {hours_until:.1f}h" if hours_until > 0 else "now"
    msg = (
        f"⚡ KUDBEE QUANT\n"
        f"◇ Scan paused\n"
        f"{'─' * 22}\n"
        f"▸ {event_name} {when}\n"
        f"▸ No new positions until event passes\n"
        f"▸ Existing positions unaffected\n"
        f"\n"
        f"Tino rule: do not enter before binary events."
    )
    try:
        return send_telegram(msg)
    except Exception:  # noqa: BLE001 — a ping must never break a scan
        return False


def notify_error(context: str, detail: str = "") -> bool:
    """Ping on a bot/health problem (e.g. an Action step failed)."""
    if not telegram_enabled():
        return False
    msg = f"△ Kudbee bot: {context}"
    if detail:
        msg += f"\n{detail}"
    return send_telegram(msg)


def notify_test() -> bool:
    """Send a one-off 'wired up correctly' ping (for `cli notify-test`)."""
    if not telegram_enabled():
        return False
    return send_telegram("◆ Kudbee Telegram notifications are wired up.")


# --- individual per-trade event alerts (open / close) -----------------------
# These fire ONE Telegram message per trade EVENT, in ADDITION to the batched
# notify_trades_opened / notify_trades_resolved digests (left exactly as-is). The
# package default is batched (rate limits + sanity); these per-trade pings are an
# opt-in upgrade, wired from the CLI off the already-deduped "just-logged" /
# "just-resolved" lists. A short freshness window is a SECOND safety net so a
# re-scan can never double-announce the same trade.

# Only alert on an event newer than this many minutes — a backstop against
# re-firing on the next scan (the source lists are already new-only).
_EVENT_FRESH_MIN = 20.0


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> bool:
    """Send ONE message for a per-trade alert.

    A thin wrapper over the package transport (:func:`send_telegram`) so the
    per-trade pings ride the SAME audited path (kill-switch, 4096-char splitting,
    bot-token redaction in logs). ``bot_token`` / ``chat_id`` are taken for an
    explicit, self-documenting signature; the transport reads the same
    ``TELEGRAM_*`` env creds the caller sources them from. Returns True iff
    delivered; never raises (a failed ping must never break a scan).
    """
    try:
        return send_telegram(text)
    except Exception:  # noqa: BLE001 — a ping must never break the run
        return False


def notify_trade_opened(bot_token: str, chat_id: str, trade: dict) -> bool:
    """Fire a single '🆕 Trade Opened' alert.

    ``trade`` keys: ``symbol``, ``direction`` ('LONG'/'SHORT'), ``timeframe``,
    ``entry_price``, ``stop_price``, ``target_price``, ``book``. Returns True iff
    sent; never raises.
    """
    try:
        side = "LONG" if trade["direction"] == "LONG" else "SHORT"
        entry, stop, target = (trade["entry_price"], trade["stop_price"],
                               trade["target_price"])
        risk = abs(entry - stop)
        rtxt = f"{abs(target - entry) / risk:.0f}R" if risk else "target"
        parts = [
            "⚡ KUDBEE QUANT",
            "◇ Trade Opened",
            "─" * 22,
            f"{trade['symbol']}  ▸ {side}  [{trade['timeframe']}  ·  {_session_name()}]",
            "",
            f"Entry    ${_g(entry)}",
            f"Stop     ${_g(stop)}   ← 1R if wrong",
            f"Target   ${_g(target)}   ← {rtxt} if right",
        ]
        why = _why_fired(trade.get("note"), trade.get("setup"))
        if why:
            parts += ["", "Why this fired:", *why]
        parts += ["", f"Book: {trade.get('book', 'core')}  ·  Paper mode"]
        return send_telegram_message(bot_token, chat_id, "\n".join(parts))
    except Exception:  # noqa: BLE001 — never let an alert break the scan
        return False


def notify_trade_closed(bot_token: str, chat_id: str, trade: dict) -> bool:
    """Fire a single trade-closed alert (WIN / BREAKEVEN / STOPPED + held time).

    ``trade`` keys: ``symbol``, ``direction``, ``timeframe``, ``entry_price``,
    ``exit_price``, ``r_result``, ``open_time``, ``close_time`` (epoch-ms ints or
    ``datetime``). Returns True iff sent; never raises.
    """
    try:
        r = trade.get("r_result", 0.0) or 0.0
        sym = trade["symbol"]
        if r >= 2.5:
            header, tag = f"◆ TARGET HIT — {sym}", "◈ full target reached"
        elif r >= 0.5:
            header, tag = f"◆ WIN — {sym}", ""
        elif r >= -0.1:
            header, tag = f"〽 FLAT — {sym}", "scratch"
        else:
            header, tag = f"◇ STOPPED — {sym}", "← cost of being in the game"
        result_line = f"Result   {r:+.2f}R" + (f"   {tag}" if tag else "")

        held = _format_held(trade.get("open_time"), trade.get("close_time"))
        side = "LONG" if trade.get("direction") == "LONG" else "SHORT"
        parts = [
            "⚡ KUDBEE QUANT",
            header,
            "─" * 22,
            f"▸ {side}  [{trade['timeframe']}]  ·  held {held}",
            "",
            f"Entry    ${_g(trade['entry_price'])}",
            f"Exit     ${_g(trade['exit_price'])}",
            result_line,
            "",
            f"Book: {trade.get('book', 'core')}  ·  Paper",
        ]
        return send_telegram_message(bot_token, chat_id, "\n".join(parts))
    except Exception:  # noqa: BLE001
        return False


def _format_held(open_time, close_time) -> str:
    """'2h 15m' / '45m' held duration from epoch-ms ints or datetimes. '—' if
    either is missing or unparseable."""
    try:
        ot, ct = open_time, close_time
        if isinstance(ot, (int, float)):
            ot = datetime.datetime.fromtimestamp(ot / 1000)
        if isinstance(ct, (int, float)):
            ct = datetime.datetime.fromtimestamp(ct / 1000)
        total_min = int((ct - ot).total_seconds() / 60)
        if total_min >= 60:
            return f"{total_min // 60}h {total_min % 60}m"
        return f"{total_min}m"
    except Exception:  # noqa: BLE001
        return "—"


def _event_ms(iso_ts: "str | None") -> "int | None":
    """ISO-8601 timestamp -> epoch milliseconds (int). None if missing/unparseable.
    Naive timestamps are treated as UTC (the journal writes UTC)."""
    if not iso_ts:
        return None
    try:
        dt = datetime.datetime.fromisoformat(iso_ts)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return int(dt.timestamp() * 1000)


def _is_fresh_event(event_ms: "int | None", *, now_ms: "float | None" = None) -> bool:
    """True if ``event_ms`` is within :data:`_EVENT_FRESH_MIN` minutes of now — the
    dedup backstop. A missing timestamp is treated as NOT fresh (never fire on an
    event we cannot date)."""
    if event_ms is None:
        return False
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    return (now_ms - event_ms) / 60000.0 <= _EVENT_FRESH_MIN


def _open_alert_dict(p) -> dict:
    """Translate a just-logged ``Prediction`` into the open-alert payload."""
    return {
        "symbol": p.symbol,
        "direction": "LONG" if (p.direction or 0) > 0 else "SHORT",
        "timeframe": p.timeframe,
        "entry_price": p.entry,
        "stop_price": p.stop,
        "target_price": p.target,
        "book": _book_label(getattr(p, "setup", None)),
        "note": getattr(p, "note", None),
        "setup": getattr(p, "setup", None),
        "open_time": _event_ms(getattr(p, "created_at", None)),
    }


def _close_alert_dict(p) -> dict:
    """Translate a just-resolved ``Prediction`` into the close-alert payload.

    There is no stored exit FILL price on a Prediction, so the displayed exit is
    derived from the outcome: a 'hit' exits at ``target``, a 'miss' at ``stop``.
    """
    exit_price = p.target if p.status == "hit" else p.stop
    return {
        "symbol": p.symbol,
        "direction": "LONG" if (p.direction or 0) > 0 else "SHORT",
        "timeframe": p.timeframe,
        "entry_price": p.entry,
        "exit_price": exit_price,
        "r_result": p.outcome_r if p.outcome_r is not None else 0.0,
        "book": _book_label(getattr(p, "setup", None)),
        "open_time": _event_ms(getattr(p, "created_at", None)),
        "close_time": _event_ms(getattr(p, "resolved_at", None)),
    }


def notify_trade_open_events(preds) -> int:
    """Fire an INDIVIDUAL '🆕 Trade Opened' alert per genuinely-new bracket trade in
    ``preds`` (the just-logged list from paper-scan / ingest-alerts).

    No-op without Telegram creds. Deduped by event freshness (the source list is
    already new-only; this is a backstop so a re-scan can't double-announce).
    Returns the count actually sent. Never raises — a ping must not break a scan.
    """
    if not preds or not telegram_enabled():
        return 0
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    sent = 0
    for p in preds:
        try:
            if getattr(p, "kind", "bracket") != "bracket":
                continue   # only bracket paper trades have entry/stop/target
            d = _open_alert_dict(p)
            if not _is_fresh_event(d["open_time"]):
                continue   # already announced on a prior scan -> skip
            if notify_trade_opened(token, chat, d):
                sent += 1
        except Exception:  # noqa: BLE001 — one bad trade must not stop the rest
            continue
    return sent


def notify_trade_close_events(preds) -> int:
    """Fire an INDIVIDUAL close alert per trade that JUST resolved hit/miss in
    ``preds`` (the just-resolved list from journal-check).

    'cancelled' (a limit that never filled) is intentionally left to the batched
    digest — there is no real entry/exit to report. No-op without creds; deduped
    by close-event freshness. Returns the count sent. Never raises.
    """
    if not preds or not telegram_enabled():
        return 0
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    sent = 0
    for p in preds:
        try:
            if getattr(p, "status", None) not in ("hit", "miss"):
                continue   # skip 'cancelled' (never filled) + anything unresolved
            d = _close_alert_dict(p)
            if not _is_fresh_event(d["close_time"]):
                continue
            if notify_trade_closed(token, chat, d):
                sent += 1
        except Exception:  # noqa: BLE001
            continue
    return sent
