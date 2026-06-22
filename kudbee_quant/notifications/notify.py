"""Message formatting + the high-level hooks the CLI calls.

Formatters are pure (Prediction/report dict in, ``str`` out) so they're trivially
unit-tested with no network. The ``notify_*`` wrappers add the only side effect —
a :func:`send_telegram` call, guarded by :func:`telegram_enabled` and wrapped so
they never raise.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .telegram import send_telegram, telegram_enabled

if TYPE_CHECKING:  # type-only import; no runtime cost / cycle
    from ..journal import Prediction

# Keep batch messages readable — list at most this many trades, then summarise.
_MAX_LINES = 25


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
    icon = {"hit": "✅", "miss": "❌", "cancelled": "⚪"}.get(p.status, "•")
    r = getattr(p, "outcome_r", None)
    rtxt = f" {r:+.2f}R" if r is not None else ""
    label = {"hit": "TARGET", "miss": "STOP", "cancelled": "cancelled"}.get(p.status, p.status)
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


def format_summary(report: dict, *, record: dict | None = None,
                   realized_today: dict | None = None) -> str:
    """Portfolio snapshot from :func:`review.open_trades_report` (+ optional record).

    ``report`` is the dict that function returns; ``record`` is an optional
    ``{venue: {...}}`` map from ``TradeJournal.venue_record`` for a one-line
    track-record footer. ``realized_today`` is an optional ``{"r": float, "n": int}``
    of fee-net R closed since the New York open (08:00 NY — see :func:`_realized_today`).
    """
    p = report.get("portfolio", {})
    trades = report.get("trades", []) or []
    n = p.get("total_open", 0)
    usd = p.get("total_unrealized_usd")
    usd_txt = "" if usd is None else f" / {usd:+.2f} USD"
    lines = [
        "📊 Kudbee paper-trade summary",
        f"Open: {n}  •  Unrealized: {p.get('total_unrealized_r', 0):+.2f}R{usd_txt}",
        f"Up/Down: {p.get('winners_open', 0)}/{p.get('losers_open', 0)}  •  "
        f"Open risk: {p.get('total_open_risk_pct', 0):.1f}% of account",
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
    if p.get("closest_to_stop") or p.get("closest_to_tp"):
        lines.append(f"Closest to stop: {p.get('closest_to_stop') or '—'}  •  "
                     f"closest to target: {p.get('closest_to_tp') or '—'}")
    if p.get("warnings"):
        lines.append("⚠ " + "; ".join(p["warnings"]))
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
        record = {v: r for v, r in j.venue_record().items() if r["n"]}
        realized = _realized_today(j.predictions)
        return send_telegram(format_summary(report, record=record or None,
                                            realized_today=realized))
    except Exception:  # noqa: BLE001 — a summary failure must not break the run
        return False


def notify_error(context: str, detail: str = "") -> bool:
    """Ping on a bot/health problem (e.g. an Action step failed)."""
    if not telegram_enabled():
        return False
    msg = f"🚨 Kudbee bot: {context}"
    if detail:
        msg += f"\n{detail}"
    return send_telegram(msg)


def notify_test() -> bool:
    """Send a one-off 'wired up correctly' ping (for `cli notify-test`)."""
    if not telegram_enabled():
        return False
    return send_telegram("✅ Kudbee Telegram notifications are wired up.")
