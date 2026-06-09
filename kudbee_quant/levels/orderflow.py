"""Order-flow / perpetuals data (Vol 6 sec 3) — genuinely non-price information.

Funding rate is the cleanest independent signal: it reflects crowded positioning
in the perpetuals market, not price action. The thesis (ICT/derivatives): extreme
funding is CONTRARIAN — when longs are crowded (high positive funding), price
tends to flush; when shorts are crowded (negative funding), price tends to
squeeze up. We fetch funding from OKX (Binance/Bybit futures are geo-blocked from
this region) and expose a contrarian funding signal.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
import requests

_OKX = "https://www.okx.com/api/v5/public/funding-rate-history"
_HDRS = {"User-Agent": "Mozilla/5.0"}


def _okx_inst(symbol: str) -> str:
    """BTCUSDT -> BTC-USDT-SWAP."""
    s = symbol.upper()
    if s.endswith("USDT"):
        return f"{s[:-4]}-USDT-SWAP"
    raise ValueError(f"cannot map {symbol!r} to an OKX swap instId")


def fetch_funding(symbol: str, pages: int = 7, session: requests.Session | None = None) -> pd.DataFrame:
    """Funding-rate history for ``symbol`` (paged back ~pages*100*8h). [timestamp, funding_rate]."""
    s = session or requests.Session()
    inst = _okx_inst(symbol)
    rows: list[dict] = []
    after = None
    for _ in range(pages):
        params = {"instId": inst, "limit": 100}
        if after:
            params["after"] = after
        r = s.get(_OKX, params=params, headers=_HDRS, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            break
        rows += data
        after = data[-1]["fundingTime"]
        time.sleep(0.2)
    if not rows:
        raise RuntimeError(f"no funding data for {symbol}")
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms", utc=True)
    df["funding_rate"] = df["fundingRate"].astype(float)
    return (df[["timestamp", "funding_rate"]].drop_duplicates("timestamp")
            .sort_values("timestamp").reset_index(drop=True))


def add_funding(df: pd.DataFrame, funding: pd.DataFrame, window: int = 30,
                z_thresh: float = 1.0) -> pd.DataFrame:
    """Merge last-known funding onto bars and add a contrarian funding vote.

    funding_z = (funding - rolling mean) / rolling std over ``window`` funding
    points; ``funding_vote`` = -sign(z) when |z| >= z_thresh (fade crowding),
    else 0. Causal: each bar sees only the most recent published funding.
    """
    f = funding.copy().sort_values("timestamp")
    f["funding_z"] = ((f["funding_rate"] - f["funding_rate"].rolling(window, min_periods=window // 2).mean())
                      / f["funding_rate"].rolling(window, min_periods=window // 2).std())
    f["funding_vote"] = np.where(f["funding_z"] >= z_thresh, -1.0,
                                 np.where(f["funding_z"] <= -z_thresh, 1.0, 0.0))
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True).astype("datetime64[ns, UTC]")
    f["timestamp"] = f["timestamp"].astype("datetime64[ns, UTC]")
    merged = pd.merge_asof(out.sort_values("timestamp"),
                           f[["timestamp", "funding_rate", "funding_z", "funding_vote"]],
                           on="timestamp", direction="backward")
    for c in ["funding_rate", "funding_z", "funding_vote"]:
        merged[c] = merged[c].fillna(0.0)
    return merged
