"""Minimal CLI to exercise the foundation.

Examples:
    python -m kudbee_quant.cli klines BTCUSDT --interval 5m --limit 300
    python -m kudbee_quant.cli vectors BTCUSDT --interval 1h --limit 500
    python -m kudbee_quant.cli polymarkets --limit 20
"""
from __future__ import annotations

import argparse

from .backtest import (
    BacktestConfig,
    monte_carlo,
    pvsra_positions,
    run_backtest,
    walk_forward,
)
from .ingest import BinanceClient, PolymarketClient
from .signals import pvsra_vector_candles

# Bars per year per Binance interval, for honest annualization.
_PERIODS_PER_YEAR = {
    "1m": 525_600, "3m": 175_200, "5m": 105_120, "15m": 35_040,
    "30m": 17_520, "1h": 8_760, "2h": 4_380, "4h": 2_190,
    "6h": 1_460, "8h": 1_095, "12h": 730, "1d": 365,
}


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


def _backtest(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    config = BacktestConfig(
        periods_per_year=_PERIODS_PER_YEAR.get(args.interval, 8_760),
        allow_short=not args.long_only,
    )
    positions = pvsra_positions(df, allow_short=not args.long_only)
    result = run_backtest(df, positions, config)
    m = result.metrics

    print(f"PVSRA backtest — {args.symbol} {args.interval} ({m.n_bars} bars)")
    print("-" * 52)
    print("RETURN")
    print(f"  total return    {m.total_return:+.2%}")
    print(f"  CAGR            {m.cagr:+.2%}")
    print(f"  Sharpe (ann.)   {m.sharpe:.2f}")
    print(f"  Sortino (ann.)  {m.sortino:.2f}")
    print(f"  win rate        {m.win_rate:.1%}    exposure {m.exposure:.1%}")
    print("RISK  (reported as loudly as return)")
    print(f"  max drawdown    {m.max_drawdown:.2%}")
    print(f"  ann. volatility {m.ann_volatility:.2%}")
    print(f"  VaR 95% / bar   {m.var_95:.2%}")
    print(f"  CVaR 95% / bar  {m.cvar_95:.2%}")
    print(f"  Calmar          {m.calmar:.2f}")

    mc = monte_carlo(result.returns, n_paths=args.paths, block_size=24)
    print("MONTE CARLO  (bootstrap, the panel screenshots omit)")
    print(f"  final return  p05/p50/p95   {mc.final_return_p05:+.1%} / {mc.final_return_p50:+.1%} / {mc.final_return_p95:+.1%}")
    print(f"  worst drawdown p50/p95-tail {mc.max_drawdown_p50:.1%} / {mc.max_drawdown_p95:.1%}")
    print(f"  risk of ruin (<-50%)        {mc.risk_of_ruin:.1%}")
    print(f"  prob. profitable            {mc.prob_profit:.1%}")

    if args.walkforward:
        wf = walk_forward(df, lambda d: pvsra_positions(d, allow_short=not args.long_only), config=config)
        print("WALK-FORWARD  (overfitting check; OOS is what counts)")
        print(f"  IS Sharpe   {wf.in_sample.sharpe:.2f}")
        print(f"  OOS Sharpe  {wf.out_of_sample.sharpe:.2f}    decay {wf.sharpe_decay:+.2f}")
        print(f"  OOS total return {wf.out_of_sample.total_return:+.2%} over {wf.n_folds} folds")

    print("\nNote: one backtest is a single draw. The Monte Carlo band and the")
    print("OOS column matter more than the headline number. Not financial advice.")


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

    b = sub.add_parser("backtest", help="backtest the PVSRA strategy + risk analysis")
    b.add_argument("symbol")
    b.add_argument("--interval", default="1h")
    b.add_argument("--limit", type=int, default=1000)
    b.add_argument("--paths", type=int, default=5000)
    b.add_argument("--long-only", action="store_true", help="disable short positions")
    b.add_argument("--walkforward", action="store_true", help="run walk-forward OOS check")
    b.set_defaults(func=_backtest)

    p = sub.add_parser("polymarkets", help="list Polymarket markets")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_polymarkets)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
