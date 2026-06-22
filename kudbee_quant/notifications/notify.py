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


def format_summary(report: dict, *, record: dict | None = None) -> str:
    """Portfolio snapshot from :func:`review.open_trades_report` (+ optional record).

    ``report`` is the dict that function returns; ``record`` is an optional
    ``{venue: {...}}`` map from ``TradeJournal.venue_record`` for a one-line
    track-record footer.
    """
    p = report.get("portfolio", {})
    n = p.get("total_open", 0)
    usd = p.get("total_unrealized_usd")
    usd_txt = "" if usd is None else f" / {usd:+.2f} USD"
    lines = [
        "📊 Kudbee paper-trade summary",
        f"Open: {n}  •  Unrealized: {p.get('total_unrealized_r', 0):+.2f}R{usd_txt}",
        f"Up/Down: {p.get('winners_open', 0)}/{p.get('losers_open', 0)}  •  "
        f"Open risk: {p.get('total_open_risk_pct', 0):.1f}% of account",
    ]
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


def notify_summary() -> bool:
    """Build + send the portfolio snapshot. Returns False if muted or on error."""
    if not telegram_enabled():
        return False
    try:
        from ..journal import TradeJournal
        from ..review import open_trades_report
        j = TradeJournal()
        report = open_trades_report(journal=j)
        record = {v: r for v, r in j.venue_record().items() if r["n"]}
        return send_telegram(format_summary(report, record=record or None))
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
