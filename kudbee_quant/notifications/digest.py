"""Weekly performance digest (F6) — Sunday 20:00 UTC summary.

Cron-driven: ``python -m kudbee_quant.notifications.digest --emit``. Reads CLOSED trades from
the journal (``resolved_series``) and the week's skips from ``data/skips/``. The "gate R saved"
figure is an explicit ESTIMATE (assumes each skipped signal would have hit its stop ≈ −1R
avoided) — labelled as such, never presented as realised. Default-off behind
``TELEGRAM_WEEKLY_DIGEST_ENABLED``; fail-open.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .skip_reporter import count_by_gate, read_skips
from .telegram import send_telegram, telegram_enabled

_RULE = "━" * 21
_GATE_LABELS = [("_dxy", "DXY filter"), ("_fp", "Fingerprint gate"), ("_adr", "ADR filter"),
                ("_cg", "Correlation guard"), ("_dcb", "Circuit breaker")]


def _quip(total_r: float) -> str:
    if total_r > 5:
        return "🔥  Outstanding week. The edge is showing."
    if total_r > 2:
        return "💪  Solid. Consistent execution."
    if total_r > 0:
        return "✅  Green is green. Process over outcome."
    return "🛡️  Difficult week. The gates held — that's what matters."


def _parse(ts) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def format_digest(journal, *, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    start_iso = start.isoformat()

    closed = []
    for row in journal.resolved_series():
        t = _parse(row.get("t"))
        if t is not None and t >= start and row.get("r") is not None:
            closed.append((row.get("symbol", "?"), float(row["r"])))
    total = sum(r for _, r in closed)
    wins = sum(1 for _, r in closed if r > 0)
    losses = len(closed) - wins
    wr = (wins / len(closed) * 100) if closed else 0.0
    best = max(closed, key=lambda x: x[1]) if closed else None
    worst = min(closed, key=lambda x: x[1]) if closed else None

    taken = sum(1 for p in journal.predictions
                if p.kind == "bracket" and (_parse(p.created_at) or start) >= start)
    week_skips = read_skips(start_iso)
    by = count_by_gate(week_skips)

    def _saved(suffix: str) -> float:
        return float(sum(v for k, v in by.items() if suffix in k))   # ~1R avoided each (estimate)

    lines = [
        "📅 WEEKLY PERFORMANCE DIGEST",
        f"Week of {start.date()} → {now.date()}",
        _RULE,
        f"Total R:        {total:+.2f}R",
        f"Win rate:       {wr:.0f}%  ({wins}W / {losses}L)",
        f"Best trade:     {best[0]} +{best[1]:.2f}R" if best else "Best trade:     —",
        f"Worst trade:    {worst[0]} {worst[1]:.2f}R" if worst else "Worst trade:    —",
        f"Signals taken:  {taken}",
        f"Signals skipped: {len(week_skips)}",
        _RULE,
        "Gate R saved (estimated; assumes each skip would have hit its stop ≈ −1R):",
    ]
    lines += [f"  {label}: +{_saved(suffix):.2f}R" for suffix, label in _GATE_LABELS]
    lines += [_RULE, _quip(total)]
    return "\n".join(lines)


def weekly_digest_enabled() -> bool:
    from ..config.feature_toggles import is_enabled
    return is_enabled("weekly_digest")


def emit(journal=None, *, force: bool = False, dry_run: bool = False) -> bool:
    try:
        if not force and not weekly_digest_enabled():
            return False
        from ..journal import TradeJournal
        text = format_digest(journal or TradeJournal())
        if dry_run:
            print(text)
            return True
        return send_telegram(text) if telegram_enabled() else False
    except Exception:  # noqa: BLE001
        return False


def _main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="digest")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    ok = emit(force=args.force or args.dry_run, dry_run=args.dry_run)
    print(f"weekly-digest: {'sent' if ok else 'skipped'}.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
