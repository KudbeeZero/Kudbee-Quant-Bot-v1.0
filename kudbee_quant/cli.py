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
from .confluence import confluence_reaction_study, range_exhaustion_study
from .events import build_features, conditional_table, detect_level_tests, recovery_curve
from .events.outcomes import add_forward_outcomes
from .events.study import StudyConfig
from .ingest import BinanceClient, PolymarketClient
from .levels import build_levels, range_stats
from .scenarios import SCENARIOS, run_sweep
from .scenarios.audit import audit_all
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


def _recovery(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    feats = build_features(df)
    res = recovery_curve(feats)
    print(f"Vector-candle recovery — {args.symbol} {args.interval} "
          f"({res.n_vectors} vectors, {len(feats)} bars)")
    print("-" * 60)
    print(f"{'horizon(bars)':>14}{'vector%':>10}{'null%':>10}{'edge':>10}")
    for _, row in res.to_frame().iterrows():
        print(f"{int(row['horizon']):>14}{row['vector_recovered']:>9.1%}"
              f"{row['null_recovered']:>10.1%}{row['edge_vs_null']:>+10.1%}")
    print(f"\nmedian bars to recovery: {res.median_bars_to_recover:.0f}")
    print("\nHonest read: 'vector%' is how often a vector box is re-entered within N "
          "bars;\n'null%' is a random equal-width zone. Edge exists only where vector "
          "clearly\nbeats null. 'Always recovered' is unfalsifiable; this measures the "
          "bounded\nversion. Not financial advice.")


def _study_open(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    feats = build_features(df)
    feats = detect_level_tests(feats, "daily_open")
    feats = add_forward_outcomes(feats, horizons=(args.horizon,))
    tests = feats[feats["daily_open_test"]].copy()

    table = conditional_table(
        tests, outcome_col=f"fwd_up_{args.horizon}",
        group_cols=["day_of_week", "session", "daily_open_nth_test"],
        config=StudyConfig(min_n=args.min_n),
    )
    print(f"Daily-open test study — {args.symbol} {args.interval} "
          f"({len(tests)} test events of {len(feats)} bars)")
    print(f"outcome: price up {args.horizon} bars after the test\n")
    if table.empty:
        print("No test events found.")
        return
    show = table.head(args.rows)
    cols = ["day_of_week", "session", "daily_open_nth_test", "n", "win_rate",
            "ci_low", "ci_high", "sufficient", "significant_fdr"]
    print(show[cols].to_string(index=False,
          formatters={"win_rate": "{:.1%}".format, "ci_low": "{:.0%}".format,
                      "ci_high": "{:.0%}".format}))
    # Highlight the user's exact bucket: Tuesday (dow=1), NY session, 2nd test.
    target = table[(table["day_of_week"] == 1) & (table["session"] == "ny")
                   & (table["daily_open_nth_test"] == 2)]
    print("\nYour bucket (Tue, NY session, 2nd test of daily open):")
    if target.empty:
        print("  no events matched.")
    else:
        r = target.iloc[0]
        verdict = ("SIGNIFICANT after FDR" if r["significant_fdr"]
                   else "not significant / insufficient — treat as noise")
        print(f"  n={int(r['n'])}  win_rate={r['win_rate']:.1%}  "
              f"95% CI=[{r['ci_low']:.0%}, {r['ci_high']:.0%}]  -> {verdict}")
    print("\nHonest read: buckets below min-n are 'insufficient'; 'significant_fdr' "
          "survives\nmultiple-comparisons control. Most thin slices will NOT — that is "
          "expected.\nNot financial advice.")


def _range_stats(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    s = range_stats(df)
    print(f"Range statistics — {args.symbol} {args.interval}")
    print(f"  ADR (avg daily range, 14d):   {s['adr']:.2f}   over {s['n_days']} days")
    print(f"  AWR (avg weekly range, 8w):   {s['awr']:.2f}   over {s['n_weeks']} weeks")
    print(f"  AMR (avg monthly range, 6m):  {s['amr']:.2f}   over {s['n_months']} months")

    feats = build_levels(df)
    table = range_exhaustion_study(feats, horizon=args.horizon)
    print(f"\nRange exhaustion — forward {args.horizon}-bar range (ATR units) by % of ADR used today:")
    print(table.to_string(index=False, formatters={
        "mean_fwd_range_atr": "{:.2f}".format, "median_fwd_range_atr": "{:.2f}".format}))
    print("\nHonest read: if mean forward range FALLS as % ADR used rises, that supports "
          "range\nexhaustion. Watch the 'sufficient' flag and ATR-normalization. Not financial advice.")


def _confluence(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    feats = build_levels(df)
    table = confluence_reaction_study(feats, horizon=args.horizon, tol_atr=args.tol_atr)
    print(f"Confluence reaction study — {args.symbol} {args.interval} "
          f"(tol={args.tol_atr} ATR, horizon={args.horizon} bars)")
    print("Does stacking more levels at a zone raise the reaction / reversal rate?\n")
    print(table.to_string(index=False, formatters={
        "mean_reaction_atr": "{:.2f}".format, "reversal_rate": "{:.1%}".format,
        "rev_ci_low": "{:.0%}".format, "rev_ci_high": "{:.0%}".format}))
    print("\nHonest read: confluence carries edge ONLY if reaction/reversal rises with score "
          "AND\nthe high-score buckets are 'sufficient'. A flat or noisy column = no edge. "
          "Not financial advice.")


def _levels(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    feats = build_levels(df)
    cols = ["timestamp", "close", "daily_open", "adr_high", "adr_low",
            "pct_adr_used", "asian_high", "asian_low", "round_below", "round_above"]
    cols = [c for c in cols if c in feats.columns]
    print(feats[cols].tail(args.rows).to_string(index=False))


def _audit(args) -> None:
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    table = audit_all(df, SCENARIOS, n_checks=args.checks)
    print(f"Lookahead self-audit — {len(SCENARIOS)} scenarios on {args.symbol} "
          f"{args.interval} ({args.checks} checks each)")
    print("signal[t] from truncated data must equal signal[t] from full data.\n")
    print(table.to_string(index=False, formatters={"leak_rate": "{:.1%}".format}))
    leaks = table[~table["clean"]]
    if leaks.empty:
        print("\nAll scenarios CLEAN — no scenario can see the future. Safe to sweep.")
    else:
        print(f"\nLOOKAHEAD DETECTED in: {', '.join(leaks['scenario'])} — "
              "these results would be fake. Fix before trusting any backtest.")


def _sweep(args) -> None:
    table = run_sweep(args.symbols, interval=args.interval, limit=args.limit, hold_n=args.hold)
    print(f"Scenario sweep — {len(SCENARIOS)} scenarios x {len(args.symbols)} assets "
          f"({args.interval}, hold {args.hold} bars)")
    print("Ranked by median OUT-OF-SAMPLE Sharpe across assets.\n")
    print(table.to_string(index=False, formatters={
        "median_oos_sharpe": "{:+.2f}".format,
        "frac_profitable_oos": "{:.0%}".format,
        "mean_oos_return": "{:+.1%}".format}))
    best = table.iloc[0]
    print(f"\nBest: {best['scenario']} (median OOS Sharpe {best['median_oos_sharpe']:+.2f}, "
          f"profitable OOS on {best['frac_profitable_oos']:.0%} of assets)")
    print("\nHonest read: a scenario is only interesting if median OOS Sharpe is clearly "
          ">0 AND\nit's profitable OOS on most assets. Crypto majors are correlated, so "
          "'most assets'\nis weak evidence — confirm survivors on uncorrelated data before "
          "any capital.\nNot financial advice.")


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
    v2.add_argument("symbols", nargs="+",
                    help="specs, e.g. BTCUSDT ETHUSDT yahoo:SPY yahoo:GLD (mix sources)")
    v2.add_argument("--strategy", choices=["pvsra", "pvsra_mm"], default="pvsra_mm")
    v2.add_argument("--interval", default="1h")
    v2.add_argument("--limit", type=int, default=4000)
    v2.add_argument("--paths", type=int, default=2000)
    v2.add_argument("--long-only", action="store_true")
    v2.set_defaults(func=_validate)

    rc = sub.add_parser("recovery", help="vector-candle recovery curve vs. null")
    rc.add_argument("symbol")
    rc.add_argument("--interval", default="1h")
    rc.add_argument("--limit", type=int, default=4000)
    rc.set_defaults(func=_recovery)

    so = sub.add_parser("study-open", help="daily-open test study (the 2nd-test/Tue/NY question)")
    so.add_argument("symbol")
    so.add_argument("--interval", default="1h")
    so.add_argument("--limit", type=int, default=4000)
    so.add_argument("--horizon", type=int, default=4, help="forward bars for the outcome")
    so.add_argument("--min-n", type=int, default=30)
    so.add_argument("--rows", type=int, default=20)
    so.set_defaults(func=_study_open)

    rs = sub.add_parser("range-stats", help="ADR/AWR/AMR + range-exhaustion study")
    rs.add_argument("symbol")
    rs.add_argument("--interval", default="1h")
    rs.add_argument("--limit", type=int, default=4000)
    rs.add_argument("--horizon", type=int, default=12)
    rs.set_defaults(func=_range_stats)

    cf = sub.add_parser("confluence", help="does confluence raise the reaction? (tested)")
    cf.add_argument("symbol")
    cf.add_argument("--interval", default="1h")
    cf.add_argument("--limit", type=int, default=4000)
    cf.add_argument("--horizon", type=int, default=8)
    cf.add_argument("--tol-atr", type=float, default=0.25)
    cf.set_defaults(func=_confluence)

    lv = sub.add_parser("levels", help="show reference levels for recent bars")
    lv.add_argument("symbol")
    lv.add_argument("--interval", default="1h")
    lv.add_argument("--limit", type=int, default=2000)
    lv.add_argument("--rows", type=int, default=15)
    lv.set_defaults(func=_levels)

    au = sub.add_parser("audit", help="lookahead self-audit of every scenario")
    au.add_argument("symbol")
    au.add_argument("--interval", default="1h")
    au.add_argument("--limit", type=int, default=2000)
    au.add_argument("--checks", type=int, default=60)
    au.set_defaults(func=_audit)

    sw = sub.add_parser("sweep", help="test the scenario battery across assets (OOS-ranked)")
    sw.add_argument("symbols", nargs="+", help="e.g. BTCUSDT ETHUSDT SOLUSDT yahoo:SPY")
    sw.add_argument("--interval", default="1h")
    sw.add_argument("--limit", type=int, default=4000)
    sw.add_argument("--hold", type=int, default=12, help="bars to hold each trigger")
    sw.set_defaults(func=_sweep)

    p = sub.add_parser("polymarkets", help="list Polymarket markets")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_polymarkets)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
