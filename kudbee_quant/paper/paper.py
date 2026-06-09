"""Paper-trading scan (see package docstring)."""
from __future__ import annotations

from ..confluence.stack import confluence_score
from ..ingest import BinanceClient
from ..journal import Prediction, TradeJournal
from ..levels import build_levels


def paper_scan(
    symbols: list[str],
    min_pct: float = 0.5,
    target_r: float = 2.0,
    stop_atr: float = 1.0,
    interval: str = "1h",
    deadline_days: float = 2.0,
    journal: TradeJournal | None = None,
    client: BinanceClient | None = None,
) -> list[Prediction]:
    """Log a bracket paper trade for each symbol currently signalling.

    Threshold is a confluence PERCENTAGE (``min_pct``, e.g. 0.5 = "half the
    factors aligned" — the validated floor). One open trade per symbol at a
    time. Returns the list of newly-logged predictions (empty if none).
    """
    j = journal or TradeJournal()
    client = client or BinanceClient()
    open_syms = {p.symbol for p in j.predictions
                 if p.status == "open" and p.kind == "bracket"}

    logged = []
    for sym in symbols:
        sym = sym.upper()
        if sym in open_syms:
            continue  # already in a paper trade on this symbol
        f = build_levels(client.klines(sym, interval=interval, limit=600))
        last = confluence_score(f).iloc[-1]
        pct, direction = float(last["confluence_pct"]), float(last["direction"])
        strength = float(last["strength"])
        if pct < min_pct or direction == 0:
            continue
        entry = float(last["close"])
        sd = float(last["atr"]) * stop_atr
        if sd <= 0:
            continue
        stop = entry - direction * sd
        target = entry + direction * sd * target_r
        side = "long" if direction > 0 else "short"
        p = j.add(Prediction(
            symbol=sym, kind="bracket", level=entry, entry=entry, stop=stop,
            target=target, direction=direction, target_r=target_r,
            deadline_days=deadline_days, timeframe=interval,
            setup=f"confluence_r_{int(round(pct*100))}pct",
            note=f"Auto confluence-R {side} scalp: {pct:.0%} confluence "
                 f"(strength {int(strength)}), entry {entry:.4g}, stop {stop:.4g}, "
                 f"target {target:.4g} ({target_r}R).",
        ))
        logged.append(p)
    return logged
