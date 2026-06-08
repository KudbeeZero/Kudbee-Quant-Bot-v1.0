"""Minimal CLI to exercise the foundation.

Examples:
    python -m kudbee_quant.cli klines BTCUSDT --interval 5m --limit 300
    python -m kudbee_quant.cli vectors BTCUSDT --interval 1h --limit 500
    python -m kudbee_quant.cli polymarkets --limit 20
"""
from __future__ import annotations

import argparse

from .ingest import BinanceClient, PolymarketClient
from .signals import pvsra_vector_candles


def _klines(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    print(df.tail(args.rows).to_string(index=False))


def _vectors(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    annotated = pvsra_vector_candles(df)
    cols = ["timestamp", "close", "volume", "vector"]
    print(annotated[cols].tail(args.rows).to_string(index=False))
    counts = annotated["vector"].value_counts()
    print("\nvector distribution:\n" + counts.to_string())


def _polymarkets(args) -> None:
    df = PolymarketClient().markets(limit=args.limit)
    cols = [c for c in ["question", "volume", "liquidity", "end_date"] if c in df.columns]
    print(df[cols].to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(prog="kudbee_quant")
    sub = parser.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("klines", help="fetch Binance OHLCV")
    k.add_argument("symbol")
    k.add_argument("--interval", default="5m")
    k.add_argument("--limit", type=int, default=300)
    k.add_argument("--rows", type=int, default=10)
    k.set_defaults(func=_klines)

    v = sub.add_parser("vectors", help="fetch OHLCV + PVSRA vector candles")
    v.add_argument("symbol")
    v.add_argument("--interval", default="1h")
    v.add_argument("--limit", type=int, default=500)
    v.add_argument("--rows", type=int, default=15)
    v.set_defaults(func=_vectors)

    p = sub.add_parser("polymarkets", help="list Polymarket markets")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_polymarkets)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
