"""Session-open brief (F3) — a context ping at London (08:00) / NY (13:00) UTC.

Cron-driven: ``python -m kudbee_quant.notifications.session_brief --session london`` from the
new scheduled workflow. Composes DXY regime + open positions + today's blocked-signal counts
(from ``data/skips/``) + the circuit-breaker state. Default-off behind
``TELEGRAM_SESSION_BRIEF_ENABLED``; fail-open.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .skip_reporter import count_by_gate, read_skips
from .telegram import send_telegram, telegram_enabled

_RULE = "━" * 17
_SESSIONS = {"london": ("🌅", "LONDON"), "ny": ("🗽", "NY")}


def _today_start_iso() -> str:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _dxy_line(client) -> str:
    try:
        from ..signals.dxy_regime import compute_dxy, state_name
        d = compute_dxy(client)
        return state_name(d["state"]) if d.get("ok") else "n/a (DXY data unavailable)"
    except Exception:  # noqa: BLE001
        return "n/a"


def _open_positions(journal) -> tuple[int, list[str]]:
    syms = [p.symbol for p in journal.predictions
            if p.status in ("open", "pending") and p.kind == "bracket"]
    return len(syms), sorted(set(syms))


def _breaker_line() -> str:
    try:
        from .. import control
        if control.is_paused():
            return "⏸ manually paused (/resume to re-enable)"
        from ..risk.drawdown_guard import DrawdownGuard
        return DrawdownGuard()._load_paused() and "🔴 tripped" or "🟢 active"
    except Exception:  # noqa: BLE001
        return "n/a"


def format_brief(session: str, journal, client=None) -> str:
    emoji, name = _SESSIONS.get(session.lower(), ("🌐", session.upper()))
    n, syms = _open_positions(journal)
    skips = read_skips(_today_start_iso())
    by = count_by_gate(skips)
    fp = sum(v for k, v in by.items() if "_fp" in k)
    adr = sum(v for k, v in by.items() if "_adr" in k)
    dxy = sum(v for k, v in by.items() if "_dxy" in k)
    sym_txt = ", ".join(syms) if syms else "none"
    return "\n".join([
        f"{emoji} {name} OPEN BRIEF",
        _RULE,
        f"DXY Regime:     {_dxy_line(client)}",
        f"Open positions: {n} ({sym_txt})",
        f"Signals blocked today: {len(skips)} (fingerprint: {fp}, ADR: {adr}, DXY: {dxy})",
        f"Circuit breaker: {_breaker_line()}",
        _RULE,
        "Good hunting. 🎯",
    ])


def session_brief_enabled() -> bool:
    from ..config.feature_toggles import is_enabled
    return is_enabled("session_brief")


def emit(session: str, journal=None, client=None, *, force: bool = False, dry_run: bool = False) -> bool:
    try:
        if not force and not session_brief_enabled():
            return False
        from ..journal import TradeJournal
        text = format_brief(session, journal or TradeJournal(), client)
        if dry_run:
            print(text)
            return True
        return send_telegram(text) if telegram_enabled() else False
    except Exception:  # noqa: BLE001
        return False


def _main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="session_brief")
    ap.add_argument("--session", default="london", choices=["london", "ny"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    ok = emit(args.session, force=args.force or args.dry_run, dry_run=args.dry_run)
    if not ok and not (args.force or args.dry_run) and not session_brief_enabled():
        print(f"session-brief({args.session}): skipped — feature 'session_brief' is OFF "
              "(set repo variable TELEGRAM_SESSION_BRIEF_ENABLED=true or flip it in "
              "data/feature_flags.json).")
    else:
        print(f"session-brief({args.session}): {'sent' if ok else 'skipped'}.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
