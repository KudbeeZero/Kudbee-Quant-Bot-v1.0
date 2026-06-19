"""Tier-2 (read-only) maker-fill feasibility — the §42 make-or-break, from data we have.

The leverage/BE candidate's whole edge rests on getting MAKER fills at ~0 fee
(docs/research/leverage_be_forward_test.md, Tier 2). Tier 1 had to *assume* that.
But the live paper engine ALREADY enters with a maker-retrace LIMIT and the journal
already records whether each signal's limit FILLED or was CANCELLED (expired). So the
core Tier-2 question — *what fraction of signals actually get a maker fill?* — is
answerable now, offline, with zero new infrastructure and zero risk.

This does NOT place orders, touch the engine, or write the journal. It reads
`data/journal.json`, segments entries into FILLED vs CANCELLED (vs still-PENDING),
and reports the maker entry fill rate overall and by venue / timeframe / market class,
plus time-to-fill — then checks it against the pre-registered Tier-2 kill (fill < 60%).

HONEST SCOPE (read before quoting): this measures the ENTRY maker fill (the bot's
0.25-ATR retrace limit). It does NOT prove the BE/stop EXIT fills as a maker — a
stop-to-BE that triggers is typically a taker exit on crypto; only the zero-fee TradFi
venue is fee-free on BOTH sides. And historical paper fills are not a guarantee of
real-exchange fills at micro size. So a pass here de-risks §42 substantially but is
evidence, not proof.

Run:  PYTHONPATH=. python scripts/leverage_be_tier2_fills.py
"""
from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime

import numpy as np

from kudbee_quant.journal.journal import DEFAULT_PATH, Prediction, venue_of

KILL_FILL_RATE = 0.60   # pre-registered Tier-2 kill (matches the design doc + shadow)
MAJORS = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
          "AVAXUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT", "DOTUSDT", "TRXUSDT", "MATICUSDT"}

# An entry is FILLED if its limit was hit (filled_at set / reached a bracket outcome);
# CANCELLED if the limit expired unfilled; PENDING if still waiting to fill.
_FILLED = ("hit", "miss", "open")
_UNFILLED = ("cancelled",)
_PENDING = ("pending",)


def _is_filled(p: Prediction) -> bool:
    # Status is authoritative: a "cancelled" entry never filled, even if a stale
    # filled_at lingers from an earlier partial/re-fill attempt (else it would be
    # double-counted as BOTH filled and cancelled and corrupt the fill rate).
    return p.status in _FILLED


def market_class(sym: str) -> str:
    if sym.lower().startswith("yahoo:"):
        return "tradfi (zero-fee)"
    return "crypto major" if sym in MAJORS else "crypto alt"


def _hours_to_fill(p: Prediction) -> float | None:
    if not p.filled_at or not p.created_at:
        return None
    try:
        dt = (datetime.fromisoformat(p.filled_at) - datetime.fromisoformat(p.created_at))
        return dt.total_seconds() / 3600.0
    except Exception:
        return None


def _rate(filled: int, cancelled: int) -> float:
    decided = filled + cancelled
    return filled / decided if decided else float("nan")


def _segment(preds):
    """(filled, cancelled, pending) counts for an iterable of bracket Predictions."""
    f = sum(1 for p in preds if _is_filled(p))
    c = sum(1 for p in preds if p.status in _UNFILLED)
    pend = sum(1 for p in preds if p.status in _PENDING)
    return f, c, pend


def _line(label, preds):
    f, c, pend = _segment(preds)
    r = _rate(f, c)
    bar = "" if r != r else ("#" * int(round(r * 30))).ljust(30)
    rtxt = "n/a" if r != r else f"{100*r:5.1f}%"
    print(f"    {label:<26} fill {rtxt}  [{bar}]  filled {f:>4}  cancelled {c:>3}  pending {pend:>3}")
    return r


def main(argv):
    trades = [Prediction(**d) for d in __import__("json").loads(DEFAULT_PATH.read_text())]
    br = [p for p in trades if p.kind == "bracket"]

    print("=" * 78)
    print("TIER-2 (READ-ONLY) — MAKER ENTRY FILL FEASIBILITY  ·  the §42 make-or-break")
    print("=" * 78)
    print("Source: the live paper engine already enters with a 0.25-ATR maker-retrace")
    print("LIMIT; the journal records FILLED vs CANCELLED. No orders placed, no writes.\n")

    f, c, pend = _segment(br)
    overall = _rate(f, c)
    print(f"[1] Overall maker entry fill rate (of DECIDED entries = filled + cancelled):")
    print(f"      {100*overall:.1f}%   ({f} filled / {f + c} decided; {c} cancelled, {pend} still pending)")
    print(f"      Status mix: {dict(Counter(p.status for p in br))}")

    print(f"\n[2] By venue (the leverage rule targets the zero-fee/maker venue):")
    by_venue = {}
    for v in ("tradfi", "crypto"):
        sub = [p for p in br if venue_of(p) == v]
        by_venue[v] = _line(v, sub)

    print(f"\n[3] By market class:")
    for cls in ("tradfi (zero-fee)", "crypto major", "crypto alt"):
        _line(cls, [p for p in br if market_class(p.symbol) == cls])

    print(f"\n[4] By timeframe:")
    for tf in sorted({p.timeframe for p in br}):
        _line(tf, [p for p in br if p.timeframe == tf])

    # time-to-fill
    htf = [h for h in (_hours_to_fill(p) for p in br if _is_filled(p)) if h is not None and h >= 0]
    if htf:
        a = np.array(htf)
        print(f"\n[5] Time-to-fill among filled entries (hours): "
              f"median {np.median(a):.2f}  p75 {np.percentile(a,75):.2f}  p90 {np.percentile(a,90):.2f}")

    # pre-registered verdict
    print("\n" + "-" * 78)
    if overall != overall:
        verdict = "INCONCLUSIVE (no decided entries)"
    elif overall >= KILL_FILL_RATE:
        verdict = (f"PASS — {100*overall:.1f}% >= {100*KILL_FILL_RATE:.0f}% kill line. "
                   "Maker ENTRY fills are achievable; §42's entry leg is de-risked.")
    else:
        verdict = (f"KILL — {100*overall:.1f}% < {100*KILL_FILL_RATE:.0f}%. "
                   "Maker entries don't fill often enough; the edge can't be harvested.")
    print(f"VERDICT (pre-registered fill kill = {100*KILL_FILL_RATE:.0f}%): {verdict}")
    print("-" * 78)
    print("HONEST SCOPE — this is the ENTRY maker fill only. The BE/stop EXIT is typically a")
    print("TAKER on crypto (only the zero-fee TradFi venue is fee-free both sides), and paper")
    print("fills are not a guarantee of real-exchange fills at micro size. Evidence, not proof.")
    print("Not financial advice. Read-only analysis — no orders, no engine/journal changes.")


if __name__ == "__main__":
    main(sys.argv[1:])
