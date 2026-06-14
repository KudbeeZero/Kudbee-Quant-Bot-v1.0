"""Per-trade excursion + live price facts, derived from OHLCV.

The journal stores a trade's bracket + outcome, but NOT how far it ran in its
favour (MFE) or against it (MAE) along the way, nor the current mark for an open
trade. Both review reports need those, so this helper re-fetches the bars over the
trade's life (entry -> now/resolved) via the shared ``RouterClient`` and measures:

  * current price / unrealized R / unrealized % (open trades),
  * MFE/MAE in R (best favourable / worst adverse excursion),
  * which levels were TOUCHED (TP1, TP2=target, stop) — distinct from FILLED, which
    the journal already tracks via ``tp1_filled_at`` / ``status``.

It is pure measurement — no journal writes, no strategy logic. R is normalized by
the trade's own stop distance, exactly like the rest of the system.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from ..ingest import RouterClient
from .journal import Prediction


@dataclass
class Excursion:
    n_bars: int                     # completed bars observed over the trade's life
    entered: bool                   # at least one bar since the trade started
    current_price: float | None     # last close in the window
    unrealized_r: float | None      # mark-to-market R from entry (open trades)
    pnl_pct: float | None           # signed % move from entry in the trade's direction
    mfe_r: float                    # max favourable excursion (R), >= 0 typically
    mae_r: float                    # max adverse excursion (R), <= 0 typically
    tp1_touched: bool
    tp2_touched: bool               # `target` is TARGET TWO in the journal model
    stop_touched: bool
    ever_in_profit: bool
    ever_in_loss: bool

    def as_dict(self) -> dict:
        return {
            "n_bars": self.n_bars, "entered": self.entered,
            "current_price": self.current_price, "unrealized_r": self.unrealized_r,
            "pnl_pct": self.pnl_pct, "mfe_r": self.mfe_r, "mae_r": self.mae_r,
            "tp1_touched": self.tp1_touched, "tp2_touched": self.tp2_touched,
            "stop_touched": self.stop_touched, "ever_in_profit": self.ever_in_profit,
            "ever_in_loss": self.ever_in_loss,
        }


def _empty(entered: bool = False) -> Excursion:
    return Excursion(0, entered, None, None, None, 0.0, 0.0,
                     False, False, False, False, False)


def compute_excursion(p: Prediction, client: RouterClient | None = None,
                      limit: int = 1000) -> Excursion:
    """Measure MFE/MAE + current mark for one bracket trade. Non-bracket or
    risk-less predictions return an empty excursion. No network if ``client``
    is injected (tests pass a fake)."""
    if p.kind != "bracket" or p.entry is None or p.stop is None:
        return _empty()
    risk = abs(p.entry - p.stop)
    if risk <= 0:
        return _empty()
    client = client or RouterClient()
    df = client.klines(p.symbol, interval=p.timeframe, limit=limit)
    if df is None or df.empty:
        return _empty()

    ts = pd.to_datetime(df["timestamp"], utc=True)
    # The trade is "live" from its fill (or creation if filled time unknown) until
    # it resolves (or now, for open trades). Bound the window to that span.
    start = datetime.fromisoformat(p.filled_at) if p.filled_at else datetime.fromisoformat(p.created_at)
    mask = ts >= start
    if p.resolved_at:
        mask &= ts <= datetime.fromisoformat(p.resolved_at)
    window = df[mask]
    if window.empty:
        return _empty(entered=False)

    d = p.direction or 1.0
    high = window["high"].to_numpy(dtype=float)
    low = window["low"].to_numpy(dtype=float)
    close = float(window["close"].to_numpy(dtype=float)[-1])

    # Per-bar R at both extremes; best/worst across the window (direction-aware).
    r_high = d * (high - p.entry) / risk
    r_low = d * (low - p.entry) / risk
    mfe_r = float(max(r_high.max(), r_low.max()))
    mae_r = float(min(r_high.min(), r_low.min()))

    unrealized_r = d * (close - p.entry) / risk
    pnl_pct = d * (close - p.entry) / p.entry * 100.0

    if d > 0:
        tp2_touched = bool((high >= p.target).any()) if p.target is not None else False
        tp1_touched = bool((high >= p.tp1).any()) if p.tp1 is not None else False
        stop_touched = bool((low <= p.stop).any())
    else:
        tp2_touched = bool((low <= p.target).any()) if p.target is not None else False
        tp1_touched = bool((low <= p.tp1).any()) if p.tp1 is not None else False
        stop_touched = bool((high >= p.stop).any())

    return Excursion(
        n_bars=int(len(window)), entered=True, current_price=close,
        unrealized_r=float(unrealized_r), pnl_pct=float(pnl_pct),
        mfe_r=mfe_r, mae_r=mae_r,
        tp1_touched=tp1_touched, tp2_touched=tp2_touched, stop_touched=stop_touched,
        ever_in_profit=bool(mfe_r > 0), ever_in_loss=bool(mae_r < 0),
    )
