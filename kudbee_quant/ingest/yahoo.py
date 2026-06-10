"""Yahoo Finance ingestion — equities, ETFs, indices, commodities, FX.

Free, no API key, via the public v8 chart JSON endpoint. This exists to
break the correlation wall: validating only on crypto majors (median rho
~0.8) is barely one independent test. Yahoo gives genuinely uncorrelated
assets (S&P via SPY, gold via GLD, oil via USO, bonds via TLT) with real
volume so the same PVSRA/MM pipeline applies.

Symbols are plain Yahoo tickers: SPY, QQQ, GLD, TLT, USO, ^GSPC, EURUSD=X,
GC=F (gold futures), CL=F (crude futures).

(We previously tried Stooq's CSV endpoint; it is now behind a JavaScript
proof-of-work anti-bot challenge and not reliably usable from a server.)
"""
from __future__ import annotations

import pandas as pd
import requests

from .cache import DataCache
from .validation import validate_ohlcv

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Yahoo's dataGranularity -> bar duration in seconds (for spotting the
# synthetic trailing "tick row" — see _parse).
_GRANULARITY_S = {
    "1m": 60, "2m": 120, "5m": 300, "15m": 900, "30m": 1800,
    "60m": 3600, "90m": 5400, "1h": 3600,
    "1d": 86_400, "5d": 432_000, "1wk": 604_800, "1mo": 2_592_000,
}


class YahooClient:
    def __init__(self, cache: DataCache | None = None, session: requests.Session | None = None):
        self.cache = cache or DataCache()
        self.session = session or requests.Session()

    def history(
        self,
        symbol: str,
        interval: str = "1d",
        range_: str = "5y",
        limit: int | None = None,
        cache_ttl: float = 86_400.0,
    ) -> pd.DataFrame:
        """Fetch OHLCV for ``symbol``; return the most recent ``limit`` rows.

        Same schema as BinanceClient.klines: timestamp (UTC), open, high,
        low, close, volume. ``interval`` (1d/1h/...) and ``range_`` (1mo/5y/
        max) follow Yahoo's chart API.
        """
        key = f"yahoo:{symbol}:{interval}:{range_}"
        cached = self.cache.get(key, ttl_seconds=cache_ttl)
        if cached is None:
            resp = self.session.get(
                _BASE + symbol,
                params={"interval": interval, "range": range_},
                headers=_HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
            cached = validate_ohlcv(self._parse(resp.json(), symbol), symbol=symbol)
            self.cache.put(key, cached)
        return cached.tail(limit).reset_index(drop=True) if limit else cached

    @staticmethod
    def _parse(payload: dict, symbol: str) -> pd.DataFrame:
        chart = payload.get("chart", {})
        if chart.get("error"):
            raise RuntimeError(f"Yahoo error for {symbol!r}: {chart['error']}")
        results = chart.get("result")
        if not results:
            raise RuntimeError(f"Yahoo returned no data for {symbol!r}")
        res = results[0]
        ts = res.get("timestamp")
        quote = res.get("indicators", {}).get("quote", [{}])[0]
        if not ts or not quote:
            raise RuntimeError(f"Yahoo returned no usable series for {symbol!r}")
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(ts, unit="s", utc=True),
                "open": quote.get("open"),
                "high": quote.get("high"),
                "low": quote.get("low"),
                "close": quote.get("close"),
                "volume": quote.get("volume"),
            }
        )
        # Yahoo emits nulls on non-trading gaps; drop rows without a close.
        df = df.dropna(subset=["close"]).reset_index(drop=True)
        df["volume"] = df["volume"].fillna(0.0).astype(float)
        # While the market is open Yahoo appends a synthetic "tick row": a
        # last-quote pseudo-bar (o=h=l=c=last) timestamped at the last TRADE
        # time, not on the interval grid. It is not a bar — it duplicates the
        # in-progress bar and would flow into levels/ATR/fill checks (§29).
        # Detect it by sub-interval spacing from the previous bar and drop it.
        gran = _GRANULARITY_S.get(res.get("meta", {}).get("dataGranularity"))
        if gran and len(df) >= 2:
            last_gap = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[-2]).total_seconds()
            if last_gap < gran:
                df = df.iloc[:-1].reset_index(drop=True)
        return df
