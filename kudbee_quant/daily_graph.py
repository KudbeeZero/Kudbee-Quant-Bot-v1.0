"""Daily trade graph — the last 24 hours of trades as a self-contained SVG.

A small, honest "how did today go?" picture: the cumulative NET-R equity curve
over a trailing window (default 24h), one dot per resolved trade (green win /
red loss), plus a header strip of the day's record (trades, win rate, net R,
still-open count).

Design choices that keep it in-keeping with the repo:
  * **No new dependencies.** The graph is emitted as a hand-built, CSP-safe SVG
    string (inline geometry + styles, no external fonts/CDNs) — the same
    lightweight ethos as the website's charts. Renders in any browser/viewer.
  * **Reuses the existing report.** All the trade math comes from
    :func:`kudbee_quant.review.trade_history_report` (windowed by ``date_from`` /
    ``date_to``), so this never disagrees with the resolver or the history skill.
  * **Net R is the headline number** (fees included, per §25/§26) — the honest
    unit the rest of the project reports.

This is read-only over the journal; it adds no strategy logic.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .ingest import RouterClient
from .journal import TradeJournal
from .review import _dt, trade_history_report


def daily_graph_report(journal: TradeJournal | None = None,
                       client: RouterClient | None = None, *,
                       hours: float = 24.0, end: str | None = None,
                       mode: str | None = None) -> dict:
    """Build the trailing-window trade report that backs the daily graph.

    ``end`` anchors the window (defaults to now, UTC); ``hours`` is its width.
    Returns the windowed ``trade_history_report`` plus a ``window`` block and a
    NET-R ``points`` list (one entry per resolved trade, in time order) used to
    draw the curve.
    """
    j = journal or TradeJournal()
    client = client or j.client
    end_dt = _dt(end) if end else datetime.now(timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    start_dt = end_dt - timedelta(hours=hours)

    rep = trade_history_report(
        journal=j, client=client, date_from=start_dt.isoformat(),
        date_to=end_dt.isoformat(), status="closed", mode=mode,
        with_excursion=False)

    # NET-R cumulative curve (fees included) — built from the windowed trades so
    # it stays consistent with the report's own per-trade `net_r`.
    points, cum = [], 0.0
    for t in sorted(rep["trades"], key=lambda x: x["exit_time"] or x["entry_time"]):
        if t["net_r"] is None:
            continue
        cum += float(t["net_r"])
        points.append({
            "t": t["exit_time"] or t["entry_time"],
            "cum_net_r": round(cum, 4),
            "net_r": round(float(t["net_r"]), 4),
            "r": t["realized_r"],
            "symbol": t["symbol"],
            "id": t["id"],
            "win": bool(t["realized_r"] is not None and t["realized_r"] > 0),
        })

    # Trades that are STILL open but were opened inside the window — context the
    # closed-only equity curve can't show.
    open_in_window = [
        p for p in j.predictions
        if p.status in ("open", "pending")
        and (mode is None or p.mode == mode)
        and (lambda w: w is not None and start_dt <= w <= end_dt)(_dt(p.filled_at or p.created_at))
    ]

    return {
        "window": {
            "hours": hours,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "n_resolved": len(points),
            "n_open_in_window": len(open_in_window),
            "net_total_r": round(points[-1]["cum_net_r"], 4) if points else 0.0,
        },
        "points": points,
        "portfolio": rep["portfolio"],
        "trades": rep["trades"],
    }


# --- SVG rendering ----------------------------------------------------------

_W, _H = 920, 460          # full canvas
_PAD_L, _PAD_R = 64, 24    # plot margins
_PAD_T, _PAD_B = 96, 56    # top strip for the header / bottom for the x-axis
_GREEN, _RED, _LINE = "#16a34a", "#dc2626", "#2563eb"
_GRID, _AXIS, _FG, _MUTE = "#e5e7eb", "#9ca3af", "#111827", "#6b7280"


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _fmt_r(x, p=2) -> str:
    return "n/a" if x is None else f"{x:+.{p}f}"


def render_daily_svg(report: dict) -> str:
    """Render the daily-graph report as a standalone SVG string (CSP-safe)."""
    win = report["window"]
    pf = report["portfolio"]
    pts = report["points"]

    start = _dt(win["start"])
    end = _dt(win["end"])
    span = max((end - start).total_seconds(), 1.0)

    x0, x1 = _PAD_L, _W - _PAD_R
    y0, y1 = _PAD_T, _H - _PAD_B
    plot_w, plot_h = x1 - x0, y1 - y0

    # Y range over the cumulative curve, always including 0, padded a touch.
    cums = [p["cum_net_r"] for p in pts]
    lo = min(cums + [0.0])
    hi = max(cums + [0.0])
    if hi - lo < 1e-9:
        lo, hi = lo - 1.0, hi + 1.0
    pad = (hi - lo) * 0.08
    lo, hi = lo - pad, hi + pad

    def px(t_iso: str) -> float:
        t = _dt(t_iso)
        frac = (t - start).total_seconds() / span
        return x0 + max(0.0, min(1.0, frac)) * plot_w

    def py(r: float) -> float:
        frac = (r - lo) / (hi - lo)
        return y1 - frac * plot_h

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" '
        f'viewBox="0 0 {_W} {_H}" font-family="-apple-system,Segoe UI,Roboto,sans-serif">',
        f'<rect width="{_W}" height="{_H}" fill="#ffffff"/>',
    ]

    # --- header strip ---------------------------------------------------------
    wr = pf["win_rate"]
    net = win["net_total_r"]
    net_col = _GREEN if net >= 0 else _RED
    out.append(f'<text x="{_PAD_L}" y="34" font-size="22" font-weight="700" '
               f'fill="{_FG}">Daily trade graph — last {win["hours"]:g}h</text>')
    sub = (f'{win["n_resolved"]} resolved · '
           f'{win["n_open_in_window"]} still open · '
           f'win rate {"n/a" if wr is None else f"{wr:.0%}"} · '
           f'expectancy {_fmt_r(pf["expectancy_r"], 3)}R')
    out.append(f'<text x="{_PAD_L}" y="58" font-size="13" fill="{_MUTE}">{_esc(sub)}</text>')
    out.append(f'<text x="{x1}" y="40" font-size="26" font-weight="700" '
               f'text-anchor="end" fill="{net_col}">{_fmt_r(net, 2)}R net</text>')
    out.append(f'<text x="{x1}" y="58" font-size="11" text-anchor="end" '
               f'fill="{_MUTE}">cumulative, fees included</text>')

    # --- y grid + labels (nice-ish ticks) ------------------------------------
    n_ticks = 4
    for i in range(n_ticks + 1):
        val = lo + (hi - lo) * i / n_ticks
        y = py(val)
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" '
                   f'stroke="{_GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x0 - 8}" y="{y + 4:.1f}" font-size="11" '
                   f'text-anchor="end" fill="{_MUTE}">{val:+.1f}R</text>')
    # emphasise the zero line
    yz = py(0.0)
    out.append(f'<line x1="{x0}" y1="{yz:.1f}" x2="{x1}" y2="{yz:.1f}" '
               f'stroke="{_AXIS}" stroke-width="1.5" stroke-dasharray="4 3"/>')

    # --- x axis (time) labels: every ~6h ------------------------------------
    step_h = max(1, int(win["hours"] // 4))
    t = start
    while t <= end + timedelta(seconds=1):
        x = px(t.isoformat())
        out.append(f'<line x1="{x:.1f}" y1="{y1}" x2="{x:.1f}" y2="{y1 + 5}" '
                   f'stroke="{_AXIS}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{y1 + 20}" font-size="11" '
                   f'text-anchor="middle" fill="{_MUTE}">{t.strftime("%H:%M")}</text>')
        t += timedelta(hours=step_h)
    out.append(f'<text x="{(x0 + x1) / 2:.0f}" y="{_H - 8}" font-size="11" '
               f'text-anchor="middle" fill="{_MUTE}">UTC time →</text>')

    # --- the curve + per-trade dots ------------------------------------------
    if pts:
        # step from the window start at 0R so the line begins at the baseline
        coords = [(x0, py(0.0))] + [(px(p["t"]), py(p["cum_net_r"])) for p in pts]
        path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
        out.append(f'<path d="{path}" fill="none" stroke="{_LINE}" stroke-width="2"/>')
        for p in pts:
            x, y = px(p["t"]), py(p["cum_net_r"])
            col = _GREEN if p["win"] else _RED
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{col}">'
                       f'<title>{_esc(p["symbol"])}  {_fmt_r(p["r"])}R  '
                       f'(net {_fmt_r(p["net_r"])}R)  {_esc(p["t"])}</title></circle>')
    else:
        out.append(f'<text x="{(x0 + x1) / 2:.0f}" y="{(y0 + y1) / 2:.0f}" '
                   f'font-size="15" text-anchor="middle" fill="{_MUTE}">'
                   f'No resolved trades in this window.</text>')

    out.append('</svg>')
    return "\n".join(out)


# --- text rendering ---------------------------------------------------------

def render_daily_text(report: dict) -> str:
    win = report["window"]
    pf = report["portfolio"]
    if not report["points"]:
        return (f"Daily graph (last {win['hours']:g}h): no resolved trades in the "
                f"window. {win['n_open_in_window']} trade(s) opened and still open.")
    wr = pf["win_rate"]
    out = [f"Daily trade graph — last {win['hours']:g}h "
           f"({win['start'][:16]} → {win['end'][:16]} UTC):"]
    out.append(f"  resolved     {win['n_resolved']}    still open {win['n_open_in_window']}")
    out.append(f"  win rate     {'n/a' if wr is None else f'{wr:.0%}'}    "
               f"expectancy {_fmt_r(pf['expectancy_r'], 3)}R/trade")
    out.append(f"  net total    {_fmt_r(win['net_total_r'], 2)}R    "
               f"(gross {_fmt_r(pf['total_r'], 2)}R)")
    out.append(f"  best/worst   {_fmt_r(pf['best_trade_r'])}R / {_fmt_r(pf['worst_trade_r'])}R")
    if pf["best_symbols"]:
        out.append("  movers:      " + ", ".join(f"{s} {v:+.1f}R" for s, v in pf["best_symbols"][:3]))
    out.append("\nNet R includes fees. Read-only over the journal; not financial advice.")
    return "\n".join(out)
