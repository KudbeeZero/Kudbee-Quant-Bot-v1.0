"""Source router: load OHLCV for a spec like ``binance:BTCUSDT`` or ``yahoo:SPY``.

A spec is ``"<source>:<symbol>"``. Bare symbols default to Binance for
backward compatibility. This lets one universe mix crypto (hourly) and
equities/commodities (daily) so the validation harness sees uncorrelated
assets.
"""
from __future__ import annotations

import re

import pandas as pd

from .binance import BinanceClient
from .yahoo import YahooClient

# Security: only these sources are allowed, and a symbol must match this
# conservative charset. Symbols are interpolated into outbound request URLs,
# so an unvalidated symbol is an SSRF / query-injection vector (e.g.
# "../../evil" or "BTC&endpoint=..."). Whitelist + regex closes that door.
_ALLOWED_SOURCES = {"binance", "yahoo"}
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._=^-]{1,20}$")


def _validate_symbol(symbol: str) -> str:
    if not _SYMBOL_RE.match(symbol):
        raise ValueError(
            f"invalid symbol {symbol!r}: must be 1-20 chars of [A-Za-z0-9._=^-]"
        )
    return symbol


def parse_spec(spec: str) -> tuple[str, str]:
    """Split ``source:symbol`` into (source, symbol); default source=binance.

    Symbols may legitimately contain a colon (e.g. Yahoo ``GC=F``) but not a
    source prefix collision, so we split only on the first colon and only
    treat a known source name as a prefix. The symbol is validated against a
    strict charset to prevent URL injection / SSRF.
    """
    if ":" in spec:
        head, rest = spec.split(":", 1)
        if head.strip().lower() in _ALLOWED_SOURCES:
            return head.strip().lower(), _validate_symbol(rest.strip())
    return "binance", _validate_symbol(spec.strip())


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


class RouterClient:
    """A ``klines()``-compatible client that routes by symbol SPEC.

    Exposes the same ``.klines(symbol, interval, limit)`` surface as
    ``BinanceClient`` but dispatches each symbol through :func:`load_ohlcv`:
    bare / ``binance:`` symbols hit Binance, ``yahoo:`` specs hit Yahoo. This
    lets the journal and the paper loop carry a MIXED crypto + TradFi universe
    behind one client, so resolving a ``yahoo:GC=F`` trade fetches from Yahoo
    (not Binance). Bare crypto symbols keep working unchanged, so it is a
    drop-in default. Underlying clients are reused to share their caches.
    """

    def __init__(self, binance: BinanceClient | None = None, yahoo: YahooClient | None = None):
        self.binance = binance or BinanceClient()
        self.yahoo = yahoo or YahooClient()

    def klines(self, symbol: str, interval: str = "1h", limit: int = 1000) -> pd.DataFrame:
        return load_ohlcv(symbol, interval=interval, limit=limit,
                          binance=self.binance, yahoo=self.yahoo)
