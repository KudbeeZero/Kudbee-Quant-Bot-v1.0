"""Net / gross risk exposure across open trades — the two-sided-trading guard.

You can hold a 1h LONG and a 5m SHORT on the same coin at once (they're keyed by
symbol+timeframe, so they coexist). That's fine — but two independent trades mean
two independent risks, and it's easy to quietly over-expose one coin. This module
tallies open + pending bracket risk per symbol so the engine can warn / block when
the COMBINED risk crosses a ceiling.

Each defined-risk bracket trade risks ~1R = ``risk_per_trade`` of the account
(by design — the stop is the risk). So:
  gross_risk = (n_long + n_short) * risk_per_trade   (worst case: both lose)
  net_risk   = |n_long - n_short| * risk_per_trade   (directional exposure)
We gate on GROSS, because a long and a short on the same coin do NOT truly hedge
— different stops/targets, they can both be wrong.
"""
from __future__ import annotations

from dataclasses import dataclass

from .journal import Prediction


@dataclass(frozen=True)
class SymbolExposure:
    symbol: str
    n_long: int
    n_short: int
    risk_per_trade: float

    @property
    def gross_risk(self) -> float:
        return (self.n_long + self.n_short) * self.risk_per_trade

    @property
    def net_risk(self) -> float:
        return abs(self.n_long - self.n_short) * self.risk_per_trade

    @property
    def net_direction(self) -> int:
        return (self.n_long > self.n_short) - (self.n_long < self.n_short)

    def as_dict(self) -> dict:
        return {"symbol": self.symbol, "n_long": self.n_long, "n_short": self.n_short,
                "gross_risk_pct": round(self.gross_risk * 100, 2),
                "net_risk_pct": round(self.net_risk * 100, 2),
                "net_direction": self.net_direction}


def _open_brackets(predictions: list[Prediction]):
    return [p for p in predictions
            if p.kind == "bracket" and p.status in ("open", "pending")]


def symbol_exposure(predictions: list[Prediction], symbol: str,
                    risk_per_trade: float = 0.01) -> SymbolExposure:
    """Open+pending long/short bracket count for one symbol (all timeframes)."""
    sym = symbol.upper()
    longs = sum(1 for p in _open_brackets(predictions) if p.symbol == sym and p.direction > 0)
    shorts = sum(1 for p in _open_brackets(predictions) if p.symbol == sym and p.direction < 0)
    return SymbolExposure(sym, longs, shorts, risk_per_trade)


def portfolio_exposure(predictions: list[Prediction],
                       risk_per_trade: float = 0.01) -> list[SymbolExposure]:
    """Per-symbol exposure for every symbol that currently has open/pending risk."""
    syms = sorted({p.symbol for p in _open_brackets(predictions)})
    return [symbol_exposure(predictions, s, risk_per_trade) for s in syms]


def would_exceed(predictions: list[Prediction], symbol: str, new_direction: float,
                 risk_per_trade: float = 0.01, max_symbol_risk: float = 0.02) -> bool:
    """Would adding one more trade push this symbol's GROSS risk over the ceiling?"""
    ex = symbol_exposure(predictions, symbol, risk_per_trade)
    return ex.gross_risk + risk_per_trade > max_symbol_risk + 1e-9


def total_gross_risk(predictions: list[Prediction], risk_per_trade: float = 0.01) -> float:
    """Whole-book gross risk as a fraction of the account."""
    return len(_open_brackets(predictions)) * risk_per_trade
