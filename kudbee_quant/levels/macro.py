"""Macro cross-asset bias for crypto (Vol 4 sec 3) — genuinely new information.

Unlike price patterns, this is independent data: the dollar (DXY, inverse to
BTC), S&P futures (ES, positive), and VIX (inverse). We compute a single
risk-on/off macro vote and merge it onto a crypto frame as last-known value
(causal). Risk-ON (ES up, DXY down, VIX down) = bullish-crypto bias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..ingest import YahooClient

# symbol -> sign of its effect on BTC (+1 positive correlation, -1 inverse)
MACRO_SYMBOLS = {"DX-Y.NYB": -1, "ES=F": +1, "^VIX": -1}


def fetch_macro_votes(interval: str = "1h", limit: int = 4000,
                      client: YahooClient | None = None) -> pd.DataFrame:
    """Return a [timestamp, macro_vote] frame; macro_vote in {-1,0,+1}."""
    client = client or YahooClient()
    merged: pd.DataFrame | None = None
    contrib = []
    for sym, effect in MACRO_SYMBOLS.items():
        df = client.history(sym, interval=interval, range_="2y", limit=limit)[["timestamp", "close"]]
        col = sym.replace("=", "").replace("^", "").replace(".", "").replace("-", "")
        df = df.rename(columns={"close": col}).sort_values("timestamp")
        # trend signal: above its own 50-EMA, oriented by its effect on BTC.
        ema = df[col].ewm(span=50, adjust=False).mean()
        df[f"sig_{col}"] = np.where(df[col] > ema, effect, -effect)
        contrib.append(f"sig_{col}")
        merged = df[["timestamp", f"sig_{col}"]] if merged is None else \
            pd.merge_asof(merged, df[["timestamp", f"sig_{col}"]], on="timestamp", direction="backward")
    merged["macro_vote"] = np.sign(merged[contrib].sum(axis=1))
    return merged[["timestamp", "macro_vote"]].dropna()


def add_macro_bias(df: pd.DataFrame, macro_votes: pd.DataFrame) -> pd.DataFrame:
    """Merge the last-known macro_vote onto a (crypto) frame by timestamp."""
    out = df.copy()
    mv = macro_votes.copy()
    # Normalize timestamp resolution (Binance ms vs Yahoo s) for merge_asof.
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True).astype("datetime64[ns, UTC]")
    mv["timestamp"] = pd.to_datetime(mv["timestamp"], utc=True).astype("datetime64[ns, UTC]")
    out = out.sort_values("timestamp")
    merged = pd.merge_asof(out, mv.sort_values("timestamp"),
                           on="timestamp", direction="backward")
    merged["macro_vote"] = merged["macro_vote"].fillna(0.0)
    return merged
