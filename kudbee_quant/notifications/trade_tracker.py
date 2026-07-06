"""Live trade tracker — an hourly per-position status ping while a bracket is open.

Cron-driven (NOT an always-on loop): the new ``telegram-scheduled.yml`` workflow runs
``python -m kudbee_quant.notifications.trade_tracker --emit`` every 30 min. It reads the
OPEN brackets from the durable journal and marks them with the same live-mark path
``notify_summary`` uses (``review.open_trades_report``) — no new in-memory store (which
couldn't survive an ephemeral runner). Default-off behind ``TELEGRAM_LIVE_TRACKER_ENABLED``
(or the ``live_tracker`` toggle); fail-open; no open positions -> sends nothing.
"""
from __future__ import annotations

from .notify import _g
from .telegram import send_telegram, telegram_enabled


def _dur(hours: float | None) -> str:
    if hours is None:
        return "—"
    h = int(hours)
    return f"{h}h" if h < 24 else f"{h // 24}d {h % 24}h"


def format_trade_update(p, t: dict) -> str:
    """Pure formatter: one 'TRADE UPDATE' block for an open bracket ``p`` + its marked
    trade dict ``t`` (from open_trades_report). Never raises."""
    try:
        side = "LONG" if (p.direction or 0) > 0 else "SHORT"
        risk = abs((p.entry or 0) - (p.stop or 0)) or 0.0
        ur, pct = t.get("unrealized_r"), t.get("pnl_pct")
        ur_txt = f"{ur:+.2f}R" if ur is not None else "n/a"
        pct_txt = f"  ({pct:+.1f}%)" if pct is not None else ""
        be_moved = getattr(p, "tp1_filled_at", None) is not None and getattr(p, "be_after_tp1", False)
        stop_lbl = "🔒 moved to breakeven" if be_moved else "original"
        if t.get("tp1_touched") or getattr(p, "tp1_filled_at", None) is not None:
            tp1_s = "✅ hit"
        elif p.tp1 is not None and risk:
            tp1_s = f"⏳ ${_g(p.tp1)} (+{abs(p.tp1 - p.entry) / risk:.1f}R)"
        else:
            tp1_s = "—"
        tp2_r = p.target_r if p.target_r is not None else (abs(p.target - p.entry) / risk if risk else 0.0)
        tp2_s = f"⏳ ${_g(p.target)} (+{tp2_r:.1f}R)"
        return "\n".join([
            f"📊 TRADE UPDATE — {p.symbol} {side}",
            f"Open since: {_dur(t.get('time_in_trade_hours'))}",
            f"Current P&L: {ur_txt}{pct_txt}",
            f"Stop: ${_g(p.stop)}  {stop_lbl}",
            f"TP1: {tp1_s}",
            f"TP2: {tp2_s}",
        ])
    except Exception:  # noqa: BLE001
        return f"📊 TRADE UPDATE — {getattr(p, 'symbol', '?')} (details unavailable)"


def live_tracker_enabled() -> bool:
    from ..config.feature_toggles import is_enabled
    return is_enabled("live_tracker")


def build_messages(journal=None, client=None) -> list[str]:
    """One update string per OPEN (filled) bracket. Pure-ish (reads journal + a live mark)."""
    from ..journal import TradeJournal
    from ..review import open_trades_report
    j = journal or TradeJournal()
    report = open_trades_report(j, client)
    by_id = {t["id"]: t for t in report.get("trades", [])}
    out = []
    for p in j.predictions:
        if p.status != "open" or p.kind != "bracket":
            continue
        out.append(format_trade_update(p, by_id.get(p.id, {})))
    return out


def emit(journal=None, client=None, *, force: bool = False, dry_run: bool = False) -> int:
    """Send one update per open position. Default-off unless ``force``; ``dry_run`` prints
    instead of sending. Returns the number emitted. Never raises into the caller."""
    try:
        if not force and not live_tracker_enabled():
            return 0
        msgs = build_messages(journal, client)
        if dry_run:
            for m in msgs:
                print(m + "\n")
            return len(msgs)
        if not telegram_enabled():
            return 0
        return sum(1 for m in msgs if send_telegram(m))
    except Exception:  # noqa: BLE001
        return 0


def _main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="trade_tracker")
    ap.add_argument("--emit", action="store_true", help="send the updates now")
    ap.add_argument("--dry-run", action="store_true", help="print instead of sending")
    ap.add_argument("--force", action="store_true", help="ignore the feature flag")
    args = ap.parse_args(argv)
    n = emit(force=args.force or args.dry_run, dry_run=args.dry_run)
    if n == 0 and not (args.force or args.dry_run) and not live_tracker_enabled():
        # A green run with 0 sends is indistinguishable from a working feature with
        # no open trades — say WHY so the Actions log is diagnosable at a glance.
        print("trade-tracker: 0 update(s) — feature 'live_tracker' is OFF "
              "(set repo variable TELEGRAM_LIVE_TRACKER_ENABLED=true or flip it in "
              "data/feature_flags.json).")
    else:
        print(f"trade-tracker: {n} update(s).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
