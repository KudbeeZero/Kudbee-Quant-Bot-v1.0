"""Performance recaps for Telegram — a rich DAILY and WEEKLY wrap.

What the owner asked for: "weekly average, go by the days (past 7 days), the good trades."
So this surfaces, fee-accurately (uses ``journal.net_outcome_r``):

  * WEEKLY  — net R (+ gross), win rate, avg R/trade, a by-day table, top + worst trades,
    and the best-contributing symbol. One honest line that 7d is a small sample.
  * DAILY   — yesterday's headline + the rolling 7-day total/average + the day's top trades.

Both are cron-driven CLI emitters (``python -m kudbee_quant.notifications.recap --daily|--weekly``),
default-off behind the ``daily_recap`` / ``weekly_recap`` toggles, and fail-open. The same
``format_weekly_recap`` powers the on-demand ``/recap`` Telegram command.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .telegram import send_telegram, telegram_enabled

_RULE = "━" * 21


def _parse(ts):
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def _closed(journal, since, until):
    """Closed trades resolved in [since, until): net (fee-adjusted) + gross R per trade."""
    from ..journal import net_outcome_r
    rows = []
    for p in getattr(journal, "predictions", []) or []:
        if getattr(p, "status", None) not in ("hit", "miss"):
            continue
        r = getattr(p, "outcome_r", None)
        if r is None:
            continue
        t = _parse(getattr(p, "resolved_at", None) or getattr(p, "created_at", None))
        if t is None or t < since or t >= until:
            continue
        try:
            net = net_outcome_r(p)
        except Exception:  # noqa: BLE001 — a fee-calc hiccup must not break the recap
            net = None
        rows.append({"t": t, "gross": float(r),
                     "net": float(net) if net is not None else float(r),
                     "symbol": getattr(p, "symbol", "?") or "?"})
    return rows


def _stats(rows):
    n = len(rows)
    wins = sum(1 for x in rows if x["gross"] > 0)
    net = sum(x["net"] for x in rows)
    return {"n": n, "wins": wins, "losses": n - wins,
            "gross": sum(x["gross"] for x in rows), "net": net,
            "wr": (wins / n * 100) if n else 0.0, "avg": (net / n) if n else 0.0}


def _top(rows, n=3, worst=False):
    return sorted(rows, key=lambda x: x["gross"], reverse=not worst)[:n]


def _best_symbol(rows):
    by = {}
    for x in rows:
        by[x["symbol"]] = by.get(x["symbol"], 0.0) + x["net"]
    return max(by.items(), key=lambda kv: kv[1]) if by else None


def _quip(net: float) -> str:
    if net > 10:
        return "🔥 Huge week — the edge is showing."
    if net > 3:
        return "💪 Strong, consistent week."
    if net > 0:
        return "✅ Green week. Process over outcome."
    return "🛡️ Down week — risk stayed controlled, that's the job."


def format_weekly_recap(journal, *, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = _closed(journal, start, now)
    s = _stats(rows)
    lines = [
        f"📅 WEEKLY RECAP — {start.date()} → {now.date()}",
        _RULE,
        f"Net R:      {s['net']:+.2f}R   (gross {s['gross']:+.2f}R)",
        f"Win rate:   {s['wr']:.0f}%   ({s['wins']}W / {s['losses']}L, {s['n']} trades)",
        f"Avg/trade:  {s['avg']:+.2f}R",
    ]
    if rows:
        by = {}
        for x in rows:
            by.setdefault(x["t"].date(), []).append(x)
        lines.append(_RULE)
        lines.append("By day:")
        for day in sorted(by):
            rr = by[day]
            w = sum(1 for x in rr if x["gross"] > 0)
            dnet = sum(x["net"] for x in rr)
            lines.append(f"  {day.strftime('%a %m-%d')}   {dnet:+5.1f}R   {w}W/{len(rr) - w}L")
        lines.append(_RULE)
        top = _top(rows, 3)
        worst = _top(rows, 1, worst=True)
        lines.append("🏆 Top: " + " · ".join(f"{x['symbol']} {x['gross']:+.1f}R" for x in top))
        if worst:
            w0 = worst[0]
            lines.append(f"🔻 Worst: {w0['symbol']} {w0['gross']:+.1f}R")
        bs = _best_symbol(rows)
        if bs:
            lines.append(f"Best symbol: {bs[0]} ({bs[1]:+.1f}R net)")
    lines.append(_RULE)
    lines.append(f"{_quip(s['net'])}  (7d sample — not a validated edge.)")
    return "\n".join(lines)


def format_daily_recap(journal, *, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    y0 = today0 - timedelta(days=1)
    week0 = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    y = _closed(journal, y0, today0)
    wk = _closed(journal, week0, now)
    ys, ws = _stats(y), _stats(wk)
    lines = [
        f"☀️ DAILY RECAP — {y0.date()}",
        f"Yesterday: {ys['net']:+.2f}R  ({ys['wins']}W/{ys['losses']}L, {ys['n']} trades)",
        f"Rolling 7d: {ws['net']:+.2f}R · {ws['wr']:.0f}% win · avg {ws['avg']:+.2f}R",
    ]
    top = _top(y, 3)
    if top:
        lines.append("🏆 Top: " + " · ".join(f"{x['symbol']} {x['gross']:+.1f}R" for x in top))
    else:
        lines.append("No trades closed yesterday.")
    return "\n".join(lines)


def _enabled(flag: str) -> bool:
    from ..config.feature_toggles import is_enabled
    return is_enabled(flag)


def emit_weekly(journal=None, *, force: bool = False, dry_run: bool = False) -> bool:
    return _emit(format_weekly_recap, "weekly_recap", journal, force=force, dry_run=dry_run)


def emit_daily(journal=None, *, force: bool = False, dry_run: bool = False) -> bool:
    return _emit(format_daily_recap, "daily_recap", journal, force=force, dry_run=dry_run)


def _emit(fmt, flag, journal, *, force, dry_run) -> bool:
    try:
        if not force and not _enabled(flag):
            return False
        from ..journal import TradeJournal
        text = fmt(journal or TradeJournal())
        if dry_run:
            print(text)
            return True
        return send_telegram(text) if telegram_enabled() else False
    except Exception:  # noqa: BLE001
        return False


def _main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="recap")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    force = args.force or args.dry_run
    if args.daily:
        ok = emit_daily(force=force, dry_run=args.dry_run)
        print(f"daily-recap: {'sent' if ok else 'skipped'}.")
    if args.weekly or not args.daily:
        ok = emit_weekly(force=force, dry_run=args.dry_run)
        print(f"weekly-recap: {'sent' if ok else 'skipped'}.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
