"""Multi-timeframe (MTF) confluence agreement (Vol 10 sec 7).

Vol 10 reports higher win rates when the signal agrees across timeframes
(64.7% at 2 TFs, 65-72% at 3 TFs). Unlike adding a confluence FACTOR (all of
which diluted — the set is saturated), requiring higher-timeframe AGREEMENT is
a different kind of filter: the same confluence read must line up on the higher
timeframe. Causal: each 1h bar sees only the last CLOSED higher-timeframe
confluence direction.
"""
from __future__ import annotations

import pandas as pd


def htf_confluence(symbol: str, htf: str = "4h", limit: int = 1200, client=None) -> pd.DataFrame:
    """Higher-timeframe confluence direction/percentage for ``symbol``."""
    from ..confluence.stack import confluence_score
    from ..ingest import BinanceClient
    from .builder import build_levels
    f = build_levels((client or BinanceClient()).klines(symbol, interval=htf, limit=limit))
    sc = confluence_score(f)
    return (sc[["timestamp", "direction", "confluence_pct"]]
            .rename(columns={"direction": "htf_dir", "confluence_pct": "htf_pct"}))


def add_htf_agreement(df: pd.DataFrame, htf: pd.DataFrame) -> pd.DataFrame:
    """Merge the last-CLOSED higher-timeframe confluence onto the lower-TF bars.

    Shifts the HTF read by one bar so a bar never sees an unfinished HTF candle
    (no lookahead), then forward-fills onto the lower timeframe by timestamp.
    """
    out = df.copy()
    h = htf.copy()
    # Use the PREVIOUS closed HTF bar's read (shift) -> strictly causal.
    h["htf_dir"] = h["htf_dir"].shift(1)
    h["htf_pct"] = h["htf_pct"].shift(1)
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True).astype("datetime64[ns, UTC]")
    h["timestamp"] = pd.to_datetime(h["timestamp"], utc=True).astype("datetime64[ns, UTC]")
    merged = pd.merge_asof(out.sort_values("timestamp"), h.sort_values("timestamp"),
                           on="timestamp", direction="backward")
    merged[["htf_dir", "htf_pct"]] = merged[["htf_dir", "htf_pct"]].fillna(0.0)
    return merged
