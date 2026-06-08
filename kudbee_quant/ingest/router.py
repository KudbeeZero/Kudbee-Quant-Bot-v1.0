"""Source router: load OHLCV for a spec like ``binance:BTCUSDT`` or ``yahoo:SPY``.

A spec is ``"<source>:<symbol>"``. Bare symbols default to Binance for
backward compatibility. This lets one universe mix crypto (hourly) and
equities/commodities (daily) so the validation harness sees uncorrelated
assets.
"""
from __future__ import annotations

import pandas as pd

from .binance import BinanceClient
from .yahoo import YahooClient


def parse_spec(spec: str) -> tuple[str, str]:
    """Split ``source:symbol`` into (source, symbol); default source=binance.

    Symbols may legitimately contain a colon (e.g. Yahoo ``GC=F``) but not a
    source prefix collision, so we split only on the first colon and only
    treat a known source name as a prefix.
    """
    if ":" in spec:
        head, rest = spec.split(":", 1)
        if head.strip().lower() in {"binance", "yahoo"}:
            return head.strip().lower(), rest.strip()
    return "binance", spec.strip()


def load_ohlcv(
    spec: str,
    interval: str = "1h",
    limit: int = 4000,
    binance: BinanceClient | None = None,
    yahoo: YahooClient | None = None,
) -> pd.DataFrame:
    """Load an OHLCV frame for a spec, routing to the right source.

    ``interval`` applies to both sources so cross-asset tests are apples-to-
    apples. Intraday Yahoo data is capped at ~730 days, so hourly requests
    use a 2y range; daily requests use 5y.
    """
    source, symbol = parse_spec(spec)
    if source == "binance":
        return (binance or BinanceClient()).klines(symbol, interval=interval, limit=limit)
    if source == "yahoo":
        range_ = "2y" if interval.endswith(("m", "h")) else "5y"
        return (yahoo or YahooClient()).history(symbol, interval=interval, range_=range_, limit=limit)
    raise ValueError(f"unknown data source {source!r} (use 'binance' or 'yahoo')")
