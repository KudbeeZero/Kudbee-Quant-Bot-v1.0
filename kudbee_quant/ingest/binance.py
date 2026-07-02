"""Binance spot OHLCV ingestion via the public REST API.

No API key required for public klines. Rate-limited and cached. We page
backwards through history so you can pull arbitrarily long windows.
"""
from __future__ import annotations

import time
import warnings

import pandas as pd
import requests

from .cache import DataCache
from .validation import validate_ohlcv

# Endpoint order matters and is a DATA-HONESTY concern, not just availability:
#   api.binance.com          — canonical Binance global order book
#   data-api.binance.vision  — the PUBLIC MIRROR of that SAME book (geo-exempt; the
#                              usual path from cloud regions where .com returns 451)
#   api.binance.us           — a SEPARATE EXCHANGE with a DIFFERENT book: different
#                              liquidity, different prints, a different symbol universe.
# The first two share a book (safe to interchange); binance.us does NOT. It stays in
# the chain as a genuine last resort (some regions can reach only it), but a fetch that
# falls through to it is TAGGED and WARNED so its prices can never be silently mislabeled
# as global-Binance data (the E2 finding, docs/audits/security-review-2026-07-02.md).
_SAME_BOOK_BASES = (
    "https://api.binance.com",
    "https://data-api.binance.vision",
)
_DIFFERENT_BOOK_BASES = (
    "https://api.binance.us",
)
_BASES = _SAME_BOOK_BASES + _DIFFERENT_BOOK_BASES
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
        # Per-fetch venue set. NOTE: instance state — one client is single-threaded per
        # fetch (every caller builds its own BinanceClient/RouterClient), so this is not
        # shared across concurrent fetches. Do not share one client across threads.
        self._fetch_venues: set[str] = set()

    @staticmethod
    def _warn_cross_venue(venues, symbol: str) -> None:
        """Warn (loudly, non-silently) when a frame's data came from a different-book
        venue. Silence was the E2 bug; this runs on BOTH the fetch path and every cache
        HIT (via the tag persisted in the cache meta) so reuse can't launder the origin."""
        venues = list(venues or [])
        different = [v for v in venues if v in _DIFFERENT_BOOK_BASES]
        same = [v for v in venues if v in _SAME_BOOK_BASES]
        if different and same:
            warnings.warn(
                f"[binance] {symbol}: history MIXES a different-book venue "
                f"({different}) with the global book ({same}) — prices are NOT "
                f"comparable across venues. Treat this frame as suspect.", stacklevel=2)
            print(f"  !! DATA-HONESTY: {symbol} mixed venues {venues}")
        elif different:
            warnings.warn(
                f"[binance] {symbol}: served from {different} — a SEPARATE exchange "
                f"with different prices, not global Binance. Global endpoints were "
                f"unreachable. Frame tagged source_venues={venues}.", stacklevel=2)
            print(f"  !! DATA-HONESTY: {symbol} served from different-book {different}")

    def _tag_venue(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Stamp the frame with the venue(s) it came from and warn on a different-book
        fallback. The tag is persisted through the cache (see cache.py) so a later cache
        hit can re-warn — the guarantee holds on reuse, not just the live fetch."""
        venues = sorted(self._fetch_venues)
        df.attrs["source_venues"] = venues
        self._warn_cross_venue(venues, symbol)
        return df

    def _get_klines(self, params: dict) -> list:
        """Try each base URL until one answers; surface the last error honestly.

        Records every host that answers in ``self._fetch_venues`` so the caller can
        tag the frame — a different-book fallback (binance.us) must never be silently
        mislabeled as global-Binance data.
        """
        last_exc: Exception | None = None
        for base in self.bases:
            try:
                resp = self.session.get(base + _KLINES, params=params, timeout=15)
                resp.raise_for_status()
                self._fetch_venues.add(base)
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
            self._warn_cross_venue(cached.attrs.get("source_venues"), symbol)
            return cached

        self._fetch_venues = set()
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

        rows = self._drop_forming_bar(rows)   # signals read CLOSED bars only
        df = self._tag_venue(validate_ohlcv(self._to_frame(rows), symbol=symbol), symbol)
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

        # Cache key: when end is open-ended (now), snap the key to the last CLOSED
        # bar boundary. Otherwise the raw millisecond `now` changes the key every
        # call, so the disk cache is never reused and the dir grows unbounded — the
        # opposite of the "reused for free" docstring. The fetch window is unchanged;
        # only the key is stabilized to the current bar.
        key_e = e_ms if end is not None else (e_ms // step) * step
        key = f"binance-range:{symbol}:{interval}:{s_ms}:{key_e}"
        cached = self.cache.get(key, ttl_seconds=cache_ttl)
        if cached is not None:
            self._warn_cross_venue(cached.attrs.get("source_venues"), symbol)
            return cached

        self._fetch_venues = set()
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

        rows = self._drop_forming_bar(rows)   # no-op for a past window; drops a
        df = self._tag_venue(  # forming bar for end=None
            validate_ohlcv(self._to_frame(rows), symbol=symbol), symbol)
        self.cache.put(key, df)
        return df

    @staticmethod
    def _drop_forming_bar(rows: list[list], now_ms: int | None = None) -> list[list]:
        """Drop a still-forming final candle so signals read only CLOSED bars.

        Binance ``/klines`` returns the currently-forming candle as its last
        element; its OHLCV is provisional and mutates until the bar closes. The
        hourly scan fires minutes into a bar, so ``.iloc[-1]`` would otherwise be a
        half-formed candle. A bar is closed only once ``now`` passes its
        ``close_time`` (``_COLUMNS`` index 6 = last ms of the bar). Mirrors the
        tick-row drop in ``yahoo.py`` so the two ingest paths agree. A no-op for
        historical windows (their last bar is already closed) — backtest frames are
        byte-identical. ``now_ms`` is injectable for deterministic tests.
        """
        if not rows:
            return rows
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        if int(rows[-1][6]) >= now_ms:   # close_time still in the future -> forming
            return rows[:-1]
        return rows

    @staticmethod
    def _to_frame(rows: list[list]) -> pd.DataFrame:
        df = pd.DataFrame(rows, columns=_COLUMNS)
        if df.empty:
            return df
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        # taker_buy_base/quote are the AGGRESSIVE-BUY share of each bar's volume
        # (Binance reports them per kline). Kept so downstream can derive bar
        # delta / CVD without a second data source; see levels/delta.py.
        num_cols = ["open", "high", "low", "close", "volume", "quote_volume",
                    "trades", "taker_buy_base", "taker_buy_quote"]
        df[num_cols] = df[num_cols].astype(float)
        keep = ["timestamp", "open", "high", "low", "close", "volume",
                "quote_volume", "trades", "taker_buy_base", "taker_buy_quote"]
        return df[keep].reset_index(drop=True)
