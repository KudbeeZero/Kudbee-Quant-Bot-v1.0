"""Binance spot OHLCV ingestion via the public REST API.

No API key required for public klines. Rate-limited and cached. We page
backwards through history so you can pull arbitrarily long windows.
"""
from __future__ import annotations

import time

import pandas as pd
import requests

from .cache import DataCache
from .validation import validate_ohlcv

# Primary endpoint, then fallbacks. api.binance.com is geo-blocked (HTTP 451)
# from many cloud regions; data-api.binance.vision is the public data mirror
# and is generally exempt, so we try it before giving up.
_BASES = (
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
)
_KLINES = "/api/v3/klines"
_MAX_LIMIT = 1000  # Binance hard cap per request

# Binance interval -> milliseconds, used for paging.
_INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000,
    "6h": 21_600_000, "8h": 28_800_000, "12h": 43_200_000, "1d": 86_400_000,
    "3d": 259_200_000, "1w": 604_800_000,
}

_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def _as_utc(x) -> pd.Timestamp:
    """Parse a date string or (naive/aware) Timestamp to a UTC Timestamp."""
    ts = pd.Timestamp(x)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


class BinanceClient:
    def __init__(
        self,
        cache: DataCache | None = None,
        session: requests.Session | None = None,
        bases: tuple[str, ...] = _BASES,
    ):
        self.cache = cache or DataCache()
        self.session = session or requests.Session()
        self.bases = bases

    def _get_klines(self, params: dict) -> list:
        """Try each base URL until one answers; surface the last error honestly."""
        last_exc: Exception | None = None
        for base in self.bases:
            try:
                resp = self.session.get(base + _KLINES, params=params, timeout=15)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                last_exc = exc  # e.g. 451 geo-block -> fall through to mirror
        raise RuntimeError(
            f"all Binance endpoints failed for {params}; last error: {last_exc}"
        )

    def klines(
        self,
        symbol: str,
        interval: str = "5m",
        limit: int = 500,
        cache_ttl: float = 300.0,
    ) -> pd.DataFrame:
        """Fetch up to ``limit`` most-recent candles for ``symbol``.

        Returns a DataFrame with a timezone-aware ``timestamp`` index column
        plus float OHLCV. ``limit`` may exceed Binance's 1000 cap; we page.
        """
        if interval not in _INTERVAL_MS:
            raise ValueError(f"unsupported interval {interval!r}; pick from {sorted(_INTERVAL_MS)}")

        key = f"binance:{symbol}:{interval}:{limit}"
        cached = self.cache.get(key, ttl_seconds=cache_ttl)
        if cached is not None:
            return cached

        rows: list[list] = []
        end_time: int | None = None
        remaining = limit
        while remaining > 0:
            batch = min(remaining, _MAX_LIMIT)
            params = {"symbol": symbol.upper(), "interval": interval, "limit": batch}
            if end_time is not None:
                params["endTime"] = end_time
            data = self._get_klines(params)
            if not data:
                break
            rows = data + rows  # prepend older data
            end_time = data[0][0] - 1  # step back before the earliest open_time
            remaining -= len(data)
            if len(data) < batch:
                break  # ran out of history
            time.sleep(0.2)  # be polite to the public endpoint

        df = validate_ohlcv(self._to_frame(rows), symbol=symbol)
        self.cache.put(key, df)
        return df

    def klines_range(
        self,
        symbol: str,
        interval: str = "1h",
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
        cache_ttl: float = 7 * 24 * 3600.0,
    ) -> pd.DataFrame:
        """Fetch every candle in the closed window [``start``, ``end``).

        Unlike :meth:`klines` (which pages BACKWARD from now for the most-recent
        ``limit`` bars), this pages FORWARD from ``start`` using Binance's
        ``startTime``/``endTime`` params, so historical windows years in the past
        (e.g. a prior-cycle analog) are reachable. ``start``/``end`` are parsed as
        UTC. Result is validated (gaps/dupes handled by ``validate_ohlcv``) and
        cached on disk with a long TTL — historical bars never change, so a once-
        fetched window is reused for free on later runs.
        """
        if interval not in _INTERVAL_MS:
            raise ValueError(f"unsupported interval {interval!r}; pick from {sorted(_INTERVAL_MS)}")
        if start is None:
            raise ValueError("klines_range requires a start")
        start_ts = _as_utc(start)
        end_ts = _as_utc(end) if end is not None else pd.Timestamp.now(tz="UTC")
        s_ms = int(start_ts.timestamp() * 1000)
        e_ms = int(end_ts.timestamp() * 1000)
        step = _INTERVAL_MS[interval]

        key = f"binance-range:{symbol}:{interval}:{s_ms}:{e_ms}"
        cached = self.cache.get(key, ttl_seconds=cache_ttl)
        if cached is not None:
            return cached

        rows: list[list] = []
        cur = s_ms
        while cur < e_ms:
            params = {"symbol": symbol.upper(), "interval": interval,
                      "startTime": cur, "endTime": e_ms, "limit": _MAX_LIMIT}
            data = self._get_klines(params)
            if not data:
                break
            rows.extend(data)
            cur = data[-1][0] + step  # advance past the last open_time
            if len(data) < _MAX_LIMIT:
                break  # exhausted the window
            time.sleep(0.2)  # be polite to the public endpoint

        df = validate_ohlcv(self._to_frame(rows), symbol=symbol)
        self.cache.put(key, df)
        return df

    @staticmethod
    def _to_frame(rows: list[list]) -> pd.DataFrame:
        df = pd.DataFrame(rows, columns=_COLUMNS)
        if df.empty:
            return df
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        num_cols = ["open", "high", "low", "close", "volume", "quote_volume", "trades"]
        df[num_cols] = df[num_cols].astype(float)
        keep = ["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades"]
        return df[keep].reset_index(drop=True)
