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
    pvsra_mm_positions,
    pvsra_positions,
    run_backtest,
    walk_forward,
)
from .context import add_mm_context
from .ingest import BinanceClient, PolymarketClient
from .signals import pvsra_vector_candles
from .validation import validate_universe

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


def _strategy_fn(name: str, long_only: bool):
    if name == "pvsra":
        return lambda d: pvsra_positions(d, allow_short=not long_only)
    if name == "pvsra_mm":
        return lambda d: pvsra_mm_positions(d, allow_short=not long_only)
    raise ValueError(f"unknown strategy {name!r}")


def _context(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    ctx = add_mm_context(df)
    cols = ["timestamp", "close", "session", "cycle_phase", "swept_low", "swept_high"]
    print(ctx[cols].tail(args.rows).to_string(index=False))
    print("\nsession distribution:\n" + ctx["session"].value_counts().to_string())
    print(f"\nbullish sweeps: {int(ctx['swept_low'].sum())}   bearish sweeps: {int(ctx['swept_high'].sum())}")


def _backtest(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    config = BacktestConfig(
        periods_per_year=_PERIODS_PER_YEAR.get(args.interval, 8_760),
        allow_short=not args.long_only,
    )
    strat = _strategy_fn(args.strategy, args.long_only)
    positions = strat(df)
    result = run_backtest(df, positions, config)
    m = result.metrics

    print(f"{args.strategy} backtest — {args.symbol} {args.interval} ({m.n_bars} bars)")
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
        wf = walk_forward(df, strat, config=config)
        print("WALK-FORWARD  (overfitting check; OOS is what counts)")
        print(f"  IS Sharpe   {wf.in_sample.sharpe:.2f}")
        print(f"  OOS Sharpe  {wf.out_of_sample.sharpe:.2f}    decay {wf.sharpe_decay:+.2f}")
        print(f"  OOS total return {wf.out_of_sample.total_return:+.2%} over {wf.n_folds} folds")

    print("\nNote: one backtest is a single draw. The Monte Carlo band and the")
    print("OOS column matter more than the headline number. Not financial advice.")


def _validate(args) -> None:
    config = BacktestConfig(
        periods_per_year=_PERIODS_PER_YEAR.get(args.interval, 8_760),
        allow_short=not args.long_only,
    )
    strat = _strategy_fn(args.strategy, args.long_only)
    report = validate_universe(
        args.symbols, strat, interval=args.interval, limit=args.limit,
        config=config, mc_paths=args.paths,
    )

    print(f"Universe validation — {args.strategy} on {len(report.assets)} assets "
          f"({args.interval}, {args.limit} bars each)")
    print("=" * 78)
    hdr = f"{'symbol':<10}{'OOS Sharpe':>11}{'OOS ret':>10}{'OOS P(profit)':>15}{'IS-OOS gap':>12}{'maxDD':>9}"
    print(hdr)
    print("-" * 78)
    for a in report.assets:
        flag = "ok " if a.profitable_oos else "XX "
        print(f"{a.symbol:<10}{a.oos_sharpe:>11.2f}{a.oos_return:>9.1%}{a.oos_prob_profit:>14.0%}"
              f"{a.is_oos_gap:>+12.2f}{a.max_drawdown:>9.1%}  {flag}")
    print("-" * 78)
    print(f"profitable OOS: {report.frac_profitable_oos:.0%}   "
          f"median OOS Sharpe: {report.median_oos_sharpe:.2f}   "
          f"median |IS-OOS gap|: {report.median_abs_is_oos_gap:.2f}")
    print(f"cross-asset corr: {report.median_cross_corr:.2f}   "
          f"effective independent assets: {report.effective_n:.1f} of {len(report.assets)}")
    print(f"\nVERDICT: {report.verdict}")
    for note in report.notes:
        print(f"  - {note}")
    print("\nNot financial advice. OOS results are the honest column; the "
          "whole-sample numbers flatter every strategy.")


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

    c = sub.add_parser("context", help="show market-maker cycle context")
    c.add_argument("symbol")
    c.add_argument("--interval", default="1h")
    c.add_argument("--limit", type=int, default=500)
    c.add_argument("--rows", type=int, default=15)
    c.set_defaults(func=_context)

    b = sub.add_parser("backtest", help="backtest a strategy + risk analysis")
    b.add_argument("symbol")
    b.add_argument("--strategy", choices=["pvsra", "pvsra_mm"], default="pvsra_mm",
                   help="pvsra = naive; pvsra_mm = PVSRA + MM-cycle context filter")
    b.add_argument("--interval", default="1h")
    b.add_argument("--limit", type=int, default=1000)
    b.add_argument("--paths", type=int, default=5000)
    b.add_argument("--long-only", action="store_true", help="disable short positions")
    b.add_argument("--walkforward", action="store_true", help="run walk-forward OOS check")
    b.set_defaults(func=_backtest)

    v2 = sub.add_parser("validate", help="validate a strategy across many assets (OOS)")
    v2.add_argument("symbols", nargs="+", help="e.g. BTCUSDT ETHUSDT SOLUSDT")
    v2.add_argument("--strategy", choices=["pvsra", "pvsra_mm"], default="pvsra_mm")
    v2.add_argument("--interval", default="1h")
    v2.add_argument("--limit", type=int, default=4000)
    v2.add_argument("--paths", type=int, default=2000)
    v2.add_argument("--long-only", action="store_true")
    v2.set_defaults(func=_validate)

    p = sub.add_parser("polymarkets", help="list Polymarket markets")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_polymarkets)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
