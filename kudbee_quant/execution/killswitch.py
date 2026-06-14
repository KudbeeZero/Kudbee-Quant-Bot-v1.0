"""Daily-loss kill-switch for live execution.

The single hard cap on a bad day: if today's REALIZED live loss reaches
``MAX_DAILY_LOSS_USD`` the executor refuses to open anything new. It is checked
before every live submit (see ``execution/live.py``).

R -> USD bridge (honest, no extra inputs): a resolved bracket's PnL in dollars is
its net-of-fee R times the dollar risk that was actually on the line —

    risk_usd  = position_size_usd * |entry - stop| / entry        # qty * stop-dist
    pnl_usd   = net_outcome_r(p) * risk_usd

``position_size_usd`` is stamped on the trade when it is placed, so only LIVE
trades (which carry it) contribute. Paper/legacy trades without a size are valued
at $0 and simply don't move the live kill-switch — which is correct, they risk no
real money.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..journal import Prediction, TradeJournal, net_outcome_r


class DailyLossLimitReached(RuntimeError):
    """Raised/returned when today's realized live loss hits the cap."""


def realized_usd_pnl(p: Prediction) -> float:
    """Realized USD PnL for one resolved live bracket (0.0 if it can't be valued)."""
    if p.outcome_r is None or p.position_size_usd is None:
        return 0.0
    if p.entry is None or p.stop is None or p.entry <= 0:
        return 0.0
    net_r = net_outcome_r(p)
    if net_r is None:
        return 0.0
    risk_usd = p.position_size_usd * abs(p.entry - p.stop) / p.entry
    return float(net_r) * risk_usd


def realized_loss_usd_today(journal: TradeJournal, *, now: datetime | None = None) -> float:
    """Sum of TODAY's (UTC) realized live PnL, as a POSITIVE loss magnitude.

    Only negative-PnL live trades resolved today count toward the loss; winners
    do not bank headroom against the cap (a loss limit is a floor, not a budget).
    """
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(timezone.utc).date()
    loss = 0.0
    for p in journal.predictions:
        if p.mode != "live" or p.status not in ("hit", "miss"):
            continue
        stamp = p.resolved_at or p.created_at
        try:
            when = datetime.fromisoformat(stamp).astimezone(timezone.utc).date()
        except (ValueError, TypeError):
            continue
        if when != today:
            continue
        pnl = realized_usd_pnl(p)
        if pnl < 0:
            loss += -pnl
    return loss


def check_daily_loss(journal: TradeJournal, max_daily_loss_usd: float,
                     *, now: datetime | None = None) -> float:
    """Raise :class:`DailyLossLimitReached` if today's realized live loss has hit
    the cap; otherwise return the current loss so callers can log headroom."""
    loss = realized_loss_usd_today(journal, now=now)
    if loss >= max_daily_loss_usd:
        raise DailyLossLimitReached(
            f"daily loss kill-switch TRIPPED: realized live loss today "
            f"${loss:.2f} >= MAX_DAILY_LOSS_USD ${max_daily_loss_usd:.2f}; "
            "no new live orders until tomorrow (UTC)."
        )
    return loss
