"""Trade-review reports: open positions + closed history (text + graph-ready JSON).

Two reports, both built from the journal and the shared excursion helper so they
never disagree with the resolver:

  * :func:`open_trades_report` — every open/pending trade with live mark, MFE/MAE,
    level touches, distances, a health label, and a plain-English line, plus a
    portfolio block.
  * :func:`trade_history_report` — closed-trade detail + portfolio analytics
    (win/loss, profit factor, expectancy, TP/stop hit rates, MFE/MAE, equity curve,
    per-symbol and per-hour breakdowns), with filters.

Numbers are honest: R is the native unit; USD only appears when a trade carries a
``position_size_usd`` (otherwise it's ``None`` — we don't invent an account size).
Reuses ``TradeJournal`` aggregates and ``compute_excursion``; no new strategy logic.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .ingest import RouterClient
from .journal import Prediction, TradeJournal
from .journal.excursion import Excursion, compute_excursion
from .journal.journal import net_outcome_r

_CLOSED = ("hit", "miss", "cancelled")


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def _hours_since(start: str | None, end: datetime | None = None) -> float | None:
    d0 = _dt(start)
    if d0 is None:
        return None
    return ((end or datetime.now(timezone.utc)) - d0).total_seconds() / 3600.0


def _pct_distance(current: float | None, level: float | None) -> float | None:
    """Signed % distance from current price to a level (positive = level is above)."""
    if current is None or level is None or current == 0:
        return None
    return (level - current) / current * 100.0


def _health(p: Prediction, exc: Excursion) -> str:
    """A coarse, honest health label from the live mark + time in trade."""
    if exc.unrealized_r is None:
        return "pending"
    hours = _hours_since(p.filled_at or p.created_at) or 0.0
    stale_hrs = (p.deadline_days or 0) * 24
    tr = p.target_r or 3.0
    if exc.unrealized_r <= -0.7 or exc.stop_touched:
        return "near stop"
    if exc.unrealized_r >= 0.7 * tr or exc.tp2_touched:
        return "near TP"
    if stale_hrs and hours > stale_hrs:
        return "stale"
    if exc.unrealized_r < -0.3:
        return "warning"
    return "healthy"


def _summary(p: Prediction, exc: Excursion) -> str:
    side = "long" if p.direction > 0 else "short"
    if exc.unrealized_r is None:
        return f"{side} {p.symbol} pending fill (limit not yet reached)."
    bits = [f"{side} {p.symbol} {p.timeframe}: {exc.unrealized_r:+.2f}R unrealized "
            f"({exc.pnl_pct:+.2f}%)"]
    bits.append(f"ran to {exc.mfe_r:+.2f}R best / {exc.mae_r:+.2f}R worst")
    if exc.tp1_touched:
        bits.append("touched TP1" + (" and banked it" if p.tp1_filled_at else " (not banked)"))
    if exc.stop_touched:
        bits.append("tagged stop")
    return ", ".join(bits) + "."


def _excursion(p: Prediction, client: RouterClient | None) -> Excursion:
    try:
        return compute_excursion(p, client=client)
    except Exception:                       # one bad symbol shouldn't sink the report
        from .journal.excursion import _empty
        return _empty()


# --- open trades ------------------------------------------------------------

def open_trades_report(journal: TradeJournal | None = None,
                       client: RouterClient | None = None) -> dict:
    j = journal or TradeJournal()
    client = client or j.client
    opens = [p for p in j.predictions if p.status in ("open", "pending")]
    trades, total_unreal_r, total_unreal_usd, winners, losers = [], 0.0, 0.0, 0, 0
    has_usd = False
    for p in opens:
        exc = _excursion(p, client)
        ur = exc.unrealized_r
        pnl_usd = (p.position_size_usd * exc.pnl_pct / 100.0
                   if (p.position_size_usd and exc.pnl_pct is not None) else None)
        if ur is not None:
            total_unreal_r += ur
            winners += ur > 0
            losers += ur < 0
        if pnl_usd is not None:
            total_unreal_usd += pnl_usd
            has_usd = True
        trades.append({
            "id": p.id, "symbol": p.symbol, "timeframe": p.timeframe, "mode": p.mode,
            "status": p.status, "entry_time": p.filled_at or p.created_at,
            "setup": p.setup,
            "entry_price": p.entry, "current_price": exc.current_price,
            "unrealized_r": ur, "unrealized_pnl_usd": pnl_usd, "pnl_pct": exc.pnl_pct,
            "mfe_r": exc.mfe_r, "mae_r": exc.mae_r,
            "tp1": p.tp1, "tp1_touched": exc.tp1_touched, "tp1_filled": p.tp1_filled_at is not None,
            "tp2": p.target, "tp2_touched": exc.tp2_touched, "tp2_filled": False,
            "stop": p.stop, "stop_touched": exc.stop_touched,
            "dist_to_tp1_pct": _pct_distance(exc.current_price, p.tp1),
            "dist_to_tp2_pct": _pct_distance(exc.current_price, p.target),
            "dist_to_stop_pct": _pct_distance(exc.current_price, p.stop),
            "time_in_trade_hours": _hours_since(p.filled_at or p.created_at),
            "health": _health(p, exc), "summary": _summary(p, exc),
        })
    # portfolio block
    risk_per = 0.01
    open_risk_pct = len(opens) * risk_per * 100.0
    with_mark = [t for t in trades if t["unrealized_r"] is not None]
    closest_stop = min(with_mark, key=lambda t: abs(t["dist_to_stop_pct"] or 1e9), default=None)
    closest_tp = min(with_mark,
                     key=lambda t: min(abs(t["dist_to_tp1_pct"] or 1e9),
                                       abs(t["dist_to_tp2_pct"] or 1e9)), default=None)
    warnings = [f"{t['symbol']} {t['health']}" for t in trades
                if t["health"] in ("near stop", "warning")]
    return {
        "trades": trades,
        "portfolio": {
            "total_open": len(opens),
            "total_unrealized_r": round(total_unreal_r, 4),
            "total_unrealized_usd": round(total_unreal_usd, 2) if has_usd else None,
            "winners_open": winners, "losers_open": losers,
            "total_open_risk_pct": round(open_risk_pct, 2),
            "closest_to_stop": closest_stop["symbol"] if closest_stop else None,
            "closest_to_tp": closest_tp["symbol"] if closest_tp else None,
            "warnings": warnings,
        },
    }


# --- trade history ----------------------------------------------------------

def _passes(p: Prediction, *, symbol, date_from, date_to, mode, status, timeframe) -> bool:
    if symbol and p.symbol.upper() != symbol.upper():
        return False
    if timeframe and p.timeframe != timeframe:
        return False
    if mode and p.mode != mode:
        return False
    if status == "closed" and p.status not in _CLOSED:
        return False
    if status == "open" and p.status not in ("open", "pending"):
        return False
    if status in ("hit", "miss", "cancelled") and p.status != status:
        return False
    when = _dt(p.resolved_at or p.created_at)
    if date_from and when and when < _dt(date_from):
        return False
    if date_to and when and when > _dt(date_to):
        return False
    return True


def trade_history_report(journal: TradeJournal | None = None,
                         client: RouterClient | None = None, *,
                         symbol: str | None = None, date_from: str | None = None,
                         date_to: str | None = None, mode: str | None = None,
                         status: str = "closed", timeframe: str | None = None,
                         with_excursion: bool = True) -> dict:
    j = journal or TradeJournal()
    client = client or j.client
    sel = [p for p in j.predictions
           if _passes(p, symbol=symbol, date_from=date_from, date_to=date_to,
                      mode=mode, status=status, timeframe=timeframe)]

    trades, r_vals, mfes, maes = [], [], [], []
    tp1_n = tp1_touch = tp2_n = tp2_touch = stop_n = stop_touch = 0
    per_symbol: dict[str, list[float]] = {}
    per_hour: dict[int, list[float]] = {}
    equity, cum = [], 0.0
    for p in sorted(sel, key=lambda x: x.resolved_at or x.created_at):
        risk = abs(p.entry - p.stop) if (p.entry is not None and p.stop is not None) else None
        exit_price = (p.entry + p.direction * p.outcome_r * risk
                      if (risk and p.outcome_r is not None) else None)
        pnl_pct = (p.outcome_r * risk / p.entry * 100.0
                   if (risk and p.outcome_r is not None and p.entry) else None)
        pnl_usd = (p.position_size_usd * pnl_pct / 100.0
                   if (p.position_size_usd and pnl_pct is not None) else None)
        exc = _excursion(p, client) if (with_excursion and p.kind == "bracket") else None
        if p.outcome_r is not None:
            r_vals.append(float(p.outcome_r))
            per_symbol.setdefault(p.symbol, []).append(float(p.outcome_r))
            wt = _dt(p.resolved_at or p.created_at)
            if wt:
                per_hour.setdefault(wt.hour, []).append(float(p.outcome_r))
            cum += float(p.outcome_r)
            equity.append({"t": p.resolved_at or p.created_at, "cum_r": round(cum, 4),
                           "r": float(p.outcome_r), "symbol": p.symbol})
        if exc is not None:
            mfes.append(exc.mfe_r)
            maes.append(exc.mae_r)
            if p.tp1 is not None:
                tp1_n += 1
                tp1_touch += exc.tp1_touched
            if p.target is not None:
                tp2_n += 1
                tp2_touch += exc.tp2_touched
            stop_n += 1
            stop_touch += exc.stop_touched
        trades.append({
            "id": p.id, "symbol": p.symbol, "timeframe": p.timeframe, "mode": p.mode,
            "status": p.status, "entry_time": p.filled_at or p.created_at,
            "exit_time": p.resolved_at, "entry_price": p.entry, "exit_price": exit_price,
            "position_size_usd": p.position_size_usd,
            "realized_r": p.outcome_r, "net_r": net_outcome_r(p),
            "realized_pnl_pct": pnl_pct, "realized_pnl_usd": pnl_usd,
            "mfe_r": exc.mfe_r if exc else None, "mae_r": exc.mae_r if exc else None,
            "ever_in_profit": exc.ever_in_profit if exc else None,
            "ever_in_loss": exc.ever_in_loss if exc else None,
            "tp1_touched": exc.tp1_touched if exc else None, "tp1_filled": p.tp1_filled_at is not None,
            "tp2_touched": exc.tp2_touched if exc else None, "tp2_filled": p.status == "hit",
            "stop_touched": exc.stop_touched if exc else None,
            "exit_reason": p.reason_closed or ("target/TP win" if p.status == "hit"
                           else "stop/time loss" if p.status == "miss" else p.status),
            "duration_hours": _hours_since(p.filled_at or p.created_at, _dt(p.resolved_at)),
            "notes": p.note,
        })

    wins = [r for r in r_vals if r > 0]
    losses = [r for r in r_vals if r < 0]
    n = len(r_vals)

    def _rank(best: bool):
        agg = {s: sum(v) for s, v in per_symbol.items()}
        return sorted(agg.items(), key=lambda kv: kv[1], reverse=best)[:5]

    portfolio = {
        "total_trades": len(trades), "n_resolved": n,
        "win_rate": (len(wins) / n) if n else None,
        "loss_rate": (len(losses) / n) if n else None,
        "avg_win_r": (sum(wins) / len(wins)) if wins else None,
        "avg_loss_r": (sum(losses) / len(losses)) if losses else None,
        "profit_factor": (sum(wins) / abs(sum(losses))) if losses else None,
        "expectancy_r": (sum(r_vals) / n) if n else None,
        "total_r": round(sum(r_vals), 4) if n else 0.0,
        "best_trade_r": max(r_vals) if n else None,
        "worst_trade_r": min(r_vals) if n else None,
        "most_traded": sorted(((s, len(v)) for s, v in per_symbol.items()),
                              key=lambda kv: kv[1], reverse=True)[:5],
        "best_symbols": _rank(best=True), "worst_symbols": _rank(best=False),
        "per_symbol": {s: {"n": len(v), "total_r": round(sum(v), 4),
                           "expectancy_r": sum(v) / len(v)} for s, v in per_symbol.items()},
        "per_hour": {h: {"n": len(v), "expectancy_r": sum(v) / len(v)}
                     for h, v in sorted(per_hour.items())},
        "tp1_hit_rate": (tp1_touch / tp1_n) if tp1_n else None,
        "tp2_hit_rate": (tp2_touch / tp2_n) if tp2_n else None,
        "stop_hit_rate": (stop_touch / stop_n) if stop_n else None,
        "avg_mfe_r": (sum(mfes) / len(mfes)) if mfes else None,
        "avg_mae_r": (sum(maes) / len(maes)) if maes else None,
    }
    return {"trades": trades, "portfolio": portfolio, "equity_curve": equity,
            "filters": {"symbol": symbol, "date_from": date_from, "date_to": date_to,
                        "mode": mode, "status": status, "timeframe": timeframe}}


# --- text rendering ---------------------------------------------------------

_NA = "  n/a"

def _r(x, p=2):
    return _NA if x is None else f"{x:+.{p}f}"

def _pct(x):
    return _NA if x is None else f"{x:.0%}"


def render_open_text(rep: dict) -> str:
    out = ["Open trades review:"]
    if not rep["trades"]:
        return "No open/pending trades right now."
    hdr = (f"  {'sym':10}{'tf':>4}{'mode':>6}{'unrl_R':>8}{'pnl%':>8}"
           f"{'MFE':>7}{'MAE':>7}{'health':>11}  to_stop%")
    out.append(hdr)
    for t in rep["trades"]:
        out.append(f"  {t['symbol']:10}{t['timeframe']:>4}{t['mode']:>6}"
                   f"{_r(t['unrealized_r']):>8}{_r(t['pnl_pct']):>8}"
                   f"{_r(t['mfe_r']):>7}{_r(t['mae_r']):>7}{t['health']:>11}  "
                   f"{_r(t['dist_to_stop_pct'],1):>7}")
    p = rep["portfolio"]
    out.append("")
    usd = "" if p["total_unrealized_usd"] is None else f" / {p['total_unrealized_usd']:+.2f} USD"
    out.append(f"Portfolio: {p['total_open']} open, "
               f"{p['total_unrealized_r']:+.2f}R unrealized{usd}; "
               f"{p['winners_open']} up / {p['losers_open']} down; "
               f"open risk {p['total_open_risk_pct']:.1f}% of account.")
    if p["closest_to_stop"] or p["closest_to_tp"]:
        out.append(f"  closest to stop: {p['closest_to_stop']}; "
                   f"closest to a target: {p['closest_to_tp']}.")
    if p["warnings"]:
        out.append("  ⚠ " + "; ".join(p["warnings"]))
    out.append("\nNot financial advice. Unrealized marks use the latest bar close.")
    return "\n".join(out)


def render_history_text(rep: dict) -> str:
    p = rep["portfolio"]
    if not p["n_resolved"]:
        return "No closed trades match those filters yet."
    pf = _NA if p["profit_factor"] is None else f"{p['profit_factor']:.2f}"
    out = [f"Trade history ({p['total_trades']} trades, {p['n_resolved']} resolved):"]
    out.append(f"  win rate     {_pct(p['win_rate'])}    profit factor {pf}")
    out.append(f"  expectancy   {_r(p['expectancy_r'],3)}R/trade   total {p['total_r']:+.1f}R")
    out.append(f"  avg win      {_r(p['avg_win_r'])}R    avg loss {_r(p['avg_loss_r'])}R")
    out.append(f"  best/worst   {_r(p['best_trade_r'])}R / {_r(p['worst_trade_r'])}R")
    out.append(f"  TP1 hit {_pct(p['tp1_hit_rate'])}  TP2 hit {_pct(p['tp2_hit_rate'])}  "
               f"stop hit {_pct(p['stop_hit_rate'])}")
    out.append(f"  avg MFE {_r(p['avg_mfe_r'])}R  avg MAE {_r(p['avg_mae_r'])}R")
    if p["best_symbols"]:
        out.append("  best symbols:  " + ", ".join(f"{s} {v:+.1f}R" for s, v in p["best_symbols"]))
        out.append("  worst symbols: " + ", ".join(f"{s} {v:+.1f}R" for s, v in p["worst_symbols"]))
    out.append("\nHonest read: R is the native unit; this is a measured record, not a "
               "projection.\nNot financial advice.")
    return "\n".join(out)
