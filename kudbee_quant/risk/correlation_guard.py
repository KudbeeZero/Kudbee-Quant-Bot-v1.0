"""Correlation guard — don't stack highly-correlated same-direction positions.

A long BTC + long ETH pair at 0.9 correlation is not two independent bets; it's one
bet at double size. This guard blocks a NEW entry when it is highly correlated (Pearson
over the last ``lookback`` closes) with an already-open position in the SAME direction.
Opposite-direction overlap is allowed (it's a hedge, not a concentration).

FAIL-OPEN: any fetch/parse/shape failure -> ``(False, None)`` (a feed hiccup must never
block every entry). Returns ``(True, peer_symbol)`` on the first peer over threshold.
"""
from __future__ import annotations

import numpy as np


def _open_same_direction(open_predictions, direction) -> list[str]:
    """Symbols of OPEN/PENDING bracket positions in the same direction."""
    out = []
    for p in open_predictions or []:
        if getattr(p, "status", None) not in ("open", "pending"):
            continue
        if getattr(p, "kind", None) != "bracket":
            continue
        d = getattr(p, "direction", 0.0) or 0.0
        sym = getattr(p, "symbol", None)
        if sym and d != 0 and (d > 0) == (direction > 0):
            out.append(sym)
    return out


class CorrelationGuard:
    def __init__(self, threshold: float = 0.80, lookback: int = 20):
        self.threshold = float(threshold)
        self.lookback = int(lookback)

    def _closes(self, client, symbol, interval) -> np.ndarray:
        df = client.klines(symbol, interval=interval, limit=self.lookback + 5)
        return df["close"].astype(float).to_numpy()[-self.lookback:]

    def is_correlated(self, proposed_symbol, proposed_direction, open_predictions,
                      client, interval: str = "1h") -> tuple[bool, str | None]:
        """``(True, peer)`` if ``proposed_symbol`` correlates > ``threshold`` with any
        same-direction open position; ``(False, None)`` otherwise / on any failure."""
        try:
            peers = [s for s in _open_same_direction(open_predictions, proposed_direction)
                     if s.upper() != str(proposed_symbol).upper()]
            if not peers:
                return (False, None)
            base = self._closes(client, proposed_symbol, interval)
            if len(base) < self.lookback:
                return (False, None)
            for sym in dict.fromkeys(peers):          # de-dup, keep order
                other = self._closes(client, sym, interval)
                if len(other) < self.lookback:
                    continue
                corr = float(np.corrcoef(base, other)[0, 1])
                if corr == corr and corr > self.threshold:   # corr==corr drops NaN
                    return (True, sym)
            return (False, None)
        except Exception:
            return (False, None)
