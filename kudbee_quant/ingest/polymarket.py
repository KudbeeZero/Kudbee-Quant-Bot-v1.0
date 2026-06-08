"""Polymarket prediction-market ingestion.

Two public APIs are used:
  - Gamma  (https://gamma-api.polymarket.com)  -> market metadata, discovery
  - CLOB   (https://clob.polymarket.com)        -> order-book prices

Polymarket prices are probabilities in [0, 1]. We surface them as-is; a
0.81 "P(up)" is a *market-implied* probability, not a guarantee — which is
exactly the honest framing the flashy dashboards drop.
"""
from __future__ import annotations

import pandas as pd
import requests

from .cache import DataCache

_GAMMA = "https://gamma-api.polymarket.com"
_CLOB = "https://clob.polymarket.com"


class PolymarketClient:
    def __init__(self, cache: DataCache | None = None, session: requests.Session | None = None):
        self.cache = cache or DataCache()
        self.session = session or requests.Session()

    def markets(self, limit: int = 100, active: bool = True, cache_ttl: float = 600.0) -> pd.DataFrame:
        """List markets with their metadata and outcome token ids."""
        key = f"polymarket:markets:{limit}:{active}"
        cached = self.cache.get(key, ttl_seconds=cache_ttl)
        if cached is not None:
            return cached

        params = {"limit": limit, "active": str(active).lower(), "closed": "false"}
        resp = self.session.get(f"{_GAMMA}/markets", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        records = [
            {
                "id": m.get("id"),
                "question": m.get("question"),
                "slug": m.get("slug"),
                "active": m.get("active"),
                "volume": float(m.get("volume") or 0.0),
                "liquidity": float(m.get("liquidity") or 0.0),
                "outcomes": m.get("outcomes"),
                "clob_token_ids": m.get("clobTokenIds"),
                "end_date": m.get("endDate"),
            }
            for m in data
        ]
        df = pd.DataFrame.from_records(records)
        self.cache.put(key, df)
        return df

    def price(self, token_id: str, side: str = "buy") -> float:
        """Current CLOB price (market-implied probability) for an outcome token."""
        resp = self.session.get(
            f"{_CLOB}/price", params={"token_id": token_id, "side": side}, timeout=15
        )
        resp.raise_for_status()
        return float(resp.json()["price"])
