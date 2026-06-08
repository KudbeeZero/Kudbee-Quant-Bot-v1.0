"""Unified, cached market-data ingestion layer.

Sources implemented:
  - Binance spot OHLCV (crypto)
  - Polymarket prediction markets (Gamma + CLOB)

Every record is timestamped at fetch time. Nothing is synthesized; if a
source is unreachable we raise rather than fabricate.
"""

from .binance import BinanceClient
from .polymarket import PolymarketClient

__all__ = ["BinanceClient", "PolymarketClient"]
