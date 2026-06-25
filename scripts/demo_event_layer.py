#!/usr/bin/env python3
"""Demo: replay a bouncing open-book through the REAL Telegram event layer.

Reproduces the kind of sequence that used to look like noise in the channel — a
9-position book swinging red and recovering across consecutive hourly reads — and
prints exactly what the channel posts now: per-event pings (approaching stop,
slipped, recovered, warning cleared) plus the "since last read" delta header on
each Live Read.

This calls the same functions the hourly Action uses
(``notifications.events`` + ``notify.format_summary``); only the marks/clock are
synthetic. The R *totals* are illustrative — the event/delta *logic* is shipped
code. Run it yourself:

    python scripts/demo_event_layer.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kudbee_quant.notifications import events as ev          # noqa: E402
from kudbee_quant.notifications.notify import format_summary  # noqa: E402

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT",
        "LINKUSDT", "AVAXUSDT", "MATICUSDT", "XRPUSDT"]

# Four reads: a healthy book goes red (ADA tags its stop), then recovers, then
# lands all-in-profit — the transitions that used to fire NO message.
READS: dict[str, list[tuple[float, str]]] = {
    "13:04": [(1.2, "winning"), (0.9, "healthy"), (0.8, "healthy"), (0.3, "healthy"),
              (0.7, "healthy"), (0.9, "healthy"), (0.66, "healthy"), (0.6, "healthy"),
              (-0.4, "warning")],
    "13:12": [(1.0, "winning"), (0.8, "healthy"), (-0.3, "warning"), (-0.6, "near stop"),
              (0.7, "healthy"), (0.85, "healthy"), (-0.2, "warning"), (0.5, "healthy"),
              (-0.2, "warning")],
    "13:26": [(1.1, "winning"), (0.9, "healthy"), (0.2, "healthy"), (0.1, "healthy"),
              (0.8, "healthy"), (1.0, "winning"), (0.4, "healthy"), (0.6, "healthy"),
              (-0.1, "warning")],
    "13:35": [(1.3, "winning"), (1.0, "winning"), (0.5, "healthy"), (0.4, "healthy"),
              (0.9, "healthy"), (1.1, "winning"), (0.7, "healthy"), (0.75, "healthy"),
              (0.8, "healthy")],
}


def _trade(sym: str, ur: float, health: str) -> dict:
    return {"id": sym, "symbol": sym, "unrealized_r": ur, "health": health,
            "tp1": 1.0, "tp1_filled": False, "tp2_touched": False,
            "stop_touched": health == "near stop", "status": "open"}


def _report(marks: list[tuple[float, str]]) -> dict:
    trades = [_trade(SYMS[i], ur, h) for i, (ur, h) in enumerate(marks)]
    winners = sum(1 for t in trades if t["unrealized_r"] > 0)
    losers = sum(1 for t in trades if t["unrealized_r"] < 0)
    return {
        "trades": trades,
        "portfolio": {
            "total_open": len(trades), "winners_open": winners, "losers_open": losers,
            "total_unrealized_r": round(sum(t["unrealized_r"] for t in trades), 2),
            "total_open_risk_pct": 7.0,
        },
    }


def render() -> str:
    """Return the full demo transcript (also used by the smoke test)."""
    out: list[str] = []
    prev = None
    for ts, marks in READS.items():
        rep = _report(marks)
        curr = ev.snapshot(rep)
        out.append("=" * 60)
        out.append(f"### {ts} UTC — channel posts:")
        out.append("=" * 60)
        for e in ev.diff_events(prev, curr):
            out.append(ev.format_event(e))
            out.append("- - - - -")
        delta = ev.delta_summary(prev, curr) or None
        out.append(format_summary(rep, delta_line=delta))
        out.append("")
        prev = curr
    return "\n".join(out)


if __name__ == "__main__":
    print(render())
