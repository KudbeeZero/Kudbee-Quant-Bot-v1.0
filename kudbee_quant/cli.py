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
from .ingest import BinanceClient, PolymarketClient, load_ohlcv
from .journal import Prediction, TradeJournal
from .levels import build_levels, range_stats
from .scenarios import SCENARIOS, run_bracket_sweep, run_sweep
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


def _universe_rank(args) -> None:
    # OPT-IN dynamic volume universe (§B). Read-only: ranks + prints, never trades.
    from .universe_rank import rank_by_volume
    from .universe import CRYPTO_CANDIDATES
    cands = args.candidates or list(CRYPTO_CANDIDATES)
    ranked = rank_by_volume(cands, interval=args.interval, lookback_bars=args.lookback)
    if not ranked:
        print("No rankable symbols (all candidates failed to fetch?).")
        return
    top = ranked[: args.top_n]
    print(f"Dynamic volume universe — top {len(top)} of {len(ranked)} ranked "
          f"({args.interval}, {args.lookback} bars, by mean USD volume):")
    for i, (sym, qv) in enumerate(top, 1):
        print(f"  {i:2}. {sym:10} {qv:,.0f} USD/bar")
    print("\nUniverse: " + " ".join(s for s, _ in top))


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


def _confluence_stack(args) -> None:
    from .confluence import confluence_directional_study
    df = BinanceClient().klines(args.symbol, interval=args.interval, limit=args.limit)
    feats = build_levels(df)
    table = confluence_directional_study(feats, horizon=args.horizon, min_n=args.min_n)
    print(f"Confluence-stack study — {args.symbol} {args.interval} "
          f"(horizon {args.horizon} bars)")
    print("Does win-rate (forward move in the voted direction) rise with confluence "
          "strength?\n")
    cols = ["strength_bucket", "n", "win_rate", "ci_low", "ci_high",
            "mean_dir_return", "sufficient", "significant_fdr"]
    cols = [c for c in cols if c in table.columns]
    print(table[cols].to_string(index=False, formatters={
        "win_rate": "{:.1%}".format, "ci_low": "{:.0%}".format,
        "ci_high": "{:.0%}".format, "mean_dir_return": "{:+.3%}".format}))
    print("\nHonest read: confluence works ONLY if win_rate climbs monotonically with "
          "strength\nAND the high-strength buckets are 'sufficient' and 'significant_fdr'. "
          "A flat\ncolumn at ~50% = confluence stacking adds nothing. Not financial advice.")


def _validate_r(args) -> None:
    from .confluence.stack import confluence_position
    from .validation import cost_sensitivity, validate_bracket
    pos_fn = lambda d: confluence_position(d, min_strength=args.min_strength)

    cells, summary = validate_bracket(
        args.symbols, pos_fn, interval=args.interval, limit=args.limit,
        n_folds=args.folds, target_r=args.target_r, stop_atr=args.stop_atr, fee_r=args.fee_r)
    print(f"Walk-forward R-validation — confluence (strength>={args.min_strength}), "
          f"{args.target_r}R target, {args.fee_r}R cost")
    print(f"{len(args.symbols)} assets x {args.folds} folds = {summary['n_cells']} cells "
          f"({summary['n_sufficient']} with enough trades)\n")

    # Per-asset x fold expectancy matrix.
    piv = cells.pivot(index="asset", columns="fold", values="expectancy_r")
    print("expectancy (R/trade) by asset x fold:")
    print(piv.to_string(float_format=lambda x: f"{x:+.2f}"))
    print(f"\nfraction of sufficient cells POSITIVE: {summary['frac_positive']:.0%}")
    print(f"median expectancy: {summary['median_expectancy_r']:+.3f} R/trade")
    print(f"cross-asset correlation: {summary['median_cross_corr']:.2f} "
          f"(lower = more independent evidence)")

    print("\ncost sensitivity (median expectancy R/trade by round-trip cost):")
    cs = cost_sensitivity(args.symbols, pos_fn, fees=(0.0, 0.02, 0.05, 0.10),
                          interval=args.interval, limit=args.limit, n_folds=args.folds,
                          target_r=args.target_r, stop_atr=args.stop_atr)
    print(cs.to_string(index=False, formatters={
        "fee_r": "{:.2f}".format, "frac_positive": "{:.0%}".format,
        "median_expectancy_r": "{:+.3f}".format}))
    print("\nHonest read: a real edge is positive across MOST asset x fold cells AND "
          "survives a\nbelievable cost. Correlated assets count as fewer independent tests. "
          "Not financial advice.")


def _bracket_sweep(args) -> None:
    table = run_bracket_sweep(args.symbols, interval=args.interval, limit=args.limit,
                              target_r=args.target_r, stop_atr=args.stop_atr, max_bars=args.max_bars)
    print(f"Bracket sweep — {len(SCENARIOS)} scenarios x {len(args.symbols)} assets "
          f"({args.interval}, stop {args.stop_atr} ATR, target {args.target_r}R, "
          f"max {args.max_bars} bars)")
    print("Ranked by median OUT-OF-SAMPLE expectancy in R (scalper's lens: small loss, "
          "bigger win).\n")
    print(table.to_string(index=False, formatters={
        "median_exp_r": "{:+.3f}".format, "total_r": "{:+.1f}".format,
        "avg_trades": "{:.0f}".format, "median_win_rate": "{:.0%}".format,
        "frac_assets_positive": "{:.0%}".format}))
    if not table.empty:
        best = table.iloc[0]
        be = ("breakeven win rate at {:.0f}R = {:.0%}".format(
            args.target_r, 1.0 / (1.0 + args.target_r)))
        print(f"\nBest: {best['scenario']} (median expectancy {best['median_exp_r']:+.3f} R/trade, "
              f"{best['median_win_rate']:.0%} win). {be}.")
    print("\nHonest read: expectancy in R is the scalper's number. Positive median R across "
          "MOST\nassets, with enough trades, is what counts -- a 40% win rate at 2R is "
          "profitable.\nNot financial advice.")


def _tp_backtest(args) -> None:
    """Single-asset bracket backtest with a 3-leg scale-out (TP1/TP2/target) and
    optional leverage — built for "run THIS management on THIS instrument" (the
    NASDAQ / Tino setup). Same limit-retrace entry the live bot uses, so the fill
    model is honest: it enters on a maker pullback, NOT at market when price tags
    the zone, and only if the retrace comes within the entry window.
    """
    from .backtest.bracket import bracket_backtest
    from .scenarios import SCENARIOS

    if args.scenario not in SCENARIOS:
        raise SystemExit(f"unknown scenario '{args.scenario}'. Options: {sorted(SCENARIOS)}")
    df = build_levels(load_ohlcv(args.symbol, interval=args.interval, limit=args.limit))
    sig = SCENARIOS[args.scenario](df)

    # Optional out-of-sample slice: keep only the LAST oos_frac of history (data the
    # signal never 'saw'). Full-sample (0.0) flatters; OOS is the honest column.
    sample = "full-sample"
    if args.oos_frac > 0:
        import pandas as _pd
        split = int(len(df) * (1 - args.oos_frac))
        df = df.iloc[split:].reset_index(drop=True)
        sig = _pd.Series(sig).iloc[split:].reset_index(drop=True)
        sample = f"OOS (last {args.oos_frac:.0%})"

    tp2_r = args.tp2_r if args.tp2_frac > 0 else None
    result = bracket_backtest(
        df, sig,
        stop_atr=args.stop_atr, target_r=args.target_r, max_bars=args.max_bars,
        fee_pct=args.fee_pct, limit_retrace_atr=args.retrace_atr,
        entry_window=args.entry_window,
        tp1_r=args.tp1_r, tp1_frac=args.tp1_frac, be_after_tp1=not args.no_be,
        tp2_r=tp2_r, tp2_frac=args.tp2_frac, leverage=args.leverage,
    )
    m = result

    legs = f"{args.tp1_frac:.0%} @ {args.tp1_r}R"
    if tp2_r is not None:
        legs += f"  +  {args.tp2_frac:.0%} @ {args.tp2_r}R"
    runner = max(0.0, 1.0 - args.tp1_frac - (args.tp2_frac if tp2_r is not None else 0.0))
    legs += f"  +  {runner:.0%} @ {args.target_r}R (runner)"

    print(f"TP-scale-out backtest — {args.symbol} {args.interval} "
          f"({m.n_trades} trades, scenario '{args.scenario}', {sample})")
    print("-" * 64)
    print(f"  entry      LIMIT retrace {args.retrace_atr} ATR (maker), "
          f"{args.entry_window}-bar fill window  [NOT market-at-zone]")
    print(f"  stop       {args.stop_atr} ATR = 1R   |   leverage {args.leverage}x   "
          f"|   BE after TP1: {not args.no_be}")
    print(f"  scale-out  {legs}")
    print("-" * 64)
    print(f"  trades        {m.n_trades}")
    print(f"  win rate      {m.win_rate:.1%}")
    print(f"  expectancy    {m.expectancy_r:+.3f} R/trade")
    print(f"  total         {m.total_r:+.1f} R")
    print(f"  avg win/loss  {m.avg_win_r:+.2f}R / {m.avg_loss_r:+.2f}R")
    print(f"  profit factor {m.profit_factor:.2f}")
    print(f"  max drawdown  {m.max_drawdown_r:.1f} R")
    be_wr = 1.0 / (1.0 + args.target_r)
    print(f"\nHonest read: R is risk-defined, so the {args.leverage}x leverage scales BOTH "
          f"the total\nand the drawdown by {args.leverage}x — it does not change whether the "
          f"edge is positive.\nThe scale-out caps upside (most size is banked early at "
          f"{args.tp1_r}R) in exchange for a\nhigher hit rate. Breakeven win rate at the "
          f"{args.target_r}R runner ~ {be_wr:.0%}. A single\nasset is one draw, not "
          f"validation. Not financial advice.")


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


def _journal_add(args) -> None:
    j = TradeJournal()
    p = j.add(Prediction(symbol=args.symbol.upper(), kind=args.kind, level=args.level,
                         deadline_days=args.days, setup=args.setup, timeframe=args.timeframe,
                         note=args.note))
    print(f"Logged {p.id}: {p.symbol} {p.kind} {p.level} within {p.deadline_days}d "
          f"[{p.setup}] -> deadline {p.deadline.date()}")


def _ingest_alerts(args) -> None:
    """Drain data/alert_inbox/ (hosted TV alerts) into the repo journal."""
    from .alert_inbox import ingest_inbox
    from .notifications import notify_trades_opened
    j = TradeJournal()
    added = ingest_inbox(j)
    print(f"{len(added)} alert(s) ingested from the inbox.")
    notify_trades_opened(added)   # no-op unless Telegram is configured


def _journal_check(args) -> None:
    from .notifications import notify_trades_resolved
    j = TradeJournal()
    changed = j.check_open()
    if changed:
        for p in changed:
            print(f"  {p.id} {p.symbol} {p.setup}: {p.status.upper()}")
    else:
        print("No predictions resolved this check.")
    notify_trades_resolved(changed)   # no-op unless Telegram is configured
    opens = [p for p in j.predictions if p.status in ("open", "pending")]
    resolved = [p for p in j.predictions if p.status in ("hit", "miss", "cancelled")]
    print(f"\n{len(opens)} open/pending, {len(resolved)} resolved.")


def _journal_list(args) -> None:
    j = TradeJournal()
    if not j.predictions:
        print("Journal empty.")
        return
    for p in j.predictions:
        print(f"  [{p.status:5}] {p.id} {p.symbol:9} {p.kind:11} {p.level:>10.2f}  "
              f"by {p.deadline.date()}  {p.setup}")


def _journal_score(args) -> None:
    j = TradeJournal()
    table = j.scorecard()
    if table.empty:
        print("No resolved predictions yet — score builds as deadlines pass.")
        return
    print("Your measured track record (resolved predictions only):")
    fmt = {"hit_rate": "{:.0%}".format, "expectancy_r": "{:+.3f}".format,
           "total_r": "{:+.1f}".format, "net_expectancy_r": "{:+.3f}".format,
           "net_total_r": "{:+.1f}".format}
    print(table.to_string(index=False, formatters={k: v for k, v in fmt.items() if k in table.columns}))
    print("\nThis is the honest number: hits / total logged, no cherry-picking. For "
          "bracket\n(paper) trades, expectancy_r is the forward edge in R; net_* "
          "subtracts the\nper-venue round-trip fee (§26).")
    venues = {v: r for v, r in j.venue_record().items() if r["n"]}
    if venues:
        print("\nBy venue (gross -> net of fees):")
        for v, r in venues.items():
            print(f"  {v:6} n={r['n']:<3} hit={r['hit_rate']:.0%}  "
                  f"exp {r['expectancy_r']:+.3f}R -> net {r['net_expectancy_r']:+.3f}R  "
                  f"(fee {r['fee_pct_roundtrip']*100:.2f}%/rt = {r['avg_fee_r']:.3f}R/trade)")


def _read_add(args) -> None:
    """Log YOUR discretionary directional read as a defined-risk bracket (scored
    as source='human' so your edge is measured apart from the bot's)."""
    j = TradeJournal()
    d = 1.0 if args.side == "long" else -1.0
    risk = abs(args.entry - args.stop)
    if risk <= 0:
        print("Stop must differ from entry."); return
    target = args.target if args.target is not None else args.entry + d * risk * args.target_r
    tr = abs(target - args.entry) / risk
    p = j.add(Prediction(
        symbol=args.symbol.upper(), kind="bracket", level=args.entry, entry=args.entry,
        stop=args.stop, target=target, direction=d, target_r=tr, deadline_days=args.days,
        timeframe=args.tf, source="human", setup="my_read",
        note=f"Discretionary read: {args.note}" if args.note else "Discretionary read."))
    side = "LONG" if d > 0 else "SHORT"
    print(f"Logged YOUR read {p.id}: {p.symbol} [{args.tf}] {side} entry {p.entry:.4g} "
          f"stop {p.stop:.4g} target {target:.4g} ({tr:.1f}R) by {p.deadline:%Y-%m-%d %H:%M}")
    print("Scored as source='human'. Run `journal-check` to resolve, `journal-score` for the record.")


def _journal_exposure(args) -> None:
    from .exposure import portfolio_exposure, total_gross_risk
    j = TradeJournal()
    book = portfolio_exposure(j.predictions, risk_per_trade=args.risk)
    if not book:
        print("No open/pending risk right now.")
        return
    print(f"Open risk by coin (each trade = {args.risk*100:.1f}% of account, "
          f"cap {args.max_risk*100:.0f}%/coin):\n")
    print(f"  {'symbol':10} {'long':>4} {'short':>5} {'net':>8} {'gross':>7}")
    for ex in book:
        flag = "  ⚠ OVER" if ex.gross_risk > args.max_risk + 1e-9 else ""
        ndir = {1: "long", -1: "short", 0: "flat"}[ex.net_direction]
        print(f"  {ex.symbol:10} {ex.n_long:>4} {ex.n_short:>5} "
              f"{ndir:>4} {ex.net_risk*100:>3.0f}% {ex.gross_risk*100:>5.0f}%{flag}")
    print(f"\nWhole book gross risk: {total_gross_risk(j.predictions, args.risk)*100:.0f}% "
          f"of account. Net = directional exposure; gross = worst case if all lose.")


def _bias_set(args) -> None:
    from .bias import BiasBook
    b = BiasBook().set(args.symbol, args.side, target=args.target, days=args.days, note=args.note)
    print(f"Bias set: {b.symbol} {b.side.upper()}"
          + (f" -> target {b.target}" if b.target else "")
          + f"  (expires {b.expires_at[:16]})")
    print("The bot will now scalp ONLY in this direction on", b.symbol, "while active.")


def _bias_list(args) -> None:
    from .bias import BiasBook
    act = BiasBook().active()
    if not act:
        print("No active biases. The bot uses its own confluence direction.")
        return
    print("Active directional biases (the human read; bot scalps WITH these):")
    for b in act:
        print(f"  {b.symbol:9} {b.side.upper():5}"
              + (f"  target {b.target}" if b.target else "")
              + f"  expires {b.expires_at[:16]}" + (f"  | {b.note}" if b.note else ""))


def _bias_clear(args) -> None:
    from .bias import BiasBook
    print("Cleared." if BiasBook().clear(args.symbol) else "No active bias for that symbol.")


def _tf_survey(args) -> None:
    from .survey import timeframe_survey
    table = timeframe_survey(args.symbol, fee_pct=args.fee_pct)
    print(f"Timeframe survey — {args.symbol} (confluence-R, 3R, 0.25-ATR limit, "
          f"{args.fee_pct*100:.2f}% maker, walk-forward):")
    print(table.to_string(index=False, formatters={
        "atr_pct": lambda x: f"{x*100:.3f}%", "fee_r": "{:.2f}".format,
        "frac_positive": "{:.0%}".format, "median_exp_r": "{:+.3f}".format}))
    print("\nHonest read: 1h is the sweet spot; 2h-4h viable (fewer trades); 15m/30m "
          "weak/negative\n(cost+noise); 7m asset-dependent. Run the STRATEGY on the "
          "positive TFs only. Not advice.")


def _paper_scan(args) -> None:
    from .notifications import notify_trades_opened
    from .paper import paper_scan
    logged = paper_scan(args.symbols, min_pct=args.min_pct, target_r=args.target_r,
                        stop_atr=args.stop_atr, intervals=args.intervals, tp1_r=args.tp1_r,
                        tp1_frac=args.tp1_frac, be_after_tp1=not args.no_be,
                        risk_per_trade=args.risk_per_trade, max_symbol_risk=args.max_symbol_risk,
                        trend_filter=args.trend_filter,
                        long_only=args.long_only, killzone_gate=args.killzone_gate,
                        trailing_atr=args.trailing_atr,
                        clean_trend_stack=args.clean_trend_stack)
    notify_trades_opened(logged)   # no-op unless Telegram is configured
    if not logged:
        print("No confluence-R signals right now (or already in a trade on those symbols).")
    else:
        print(f"Logged {len(logged)} paper trade(s):")
        for p in logged:
            side = "LONG" if p.direction > 0 else "SHORT"
            tp1 = f" TP1 {p.tp1:.4g}" if p.tp1 is not None else ""
            print(f"  {p.id} {p.symbol} [{p.timeframe}] {side} [{p.setup}] entry {p.entry:.4g} "
                  f"stop {p.stop:.4g} target {p.target:.4g} ({p.target_r}R){tp1} "
                  f"by {p.deadline:%Y-%m-%d %H:%M}")
    print("\nRun `journal-check` later to resolve them, `journal-score` for forward R "
          "expectancy.\nThis accumulates a FORWARD record on unseen data. Not financial advice.")


def _vector_scan(args) -> None:
    from .signals.vector_log import scan_and_log
    new = scan_and_log(args.symbols, args.intervals, limit=args.limit,
                       last_only=not args.all)
    if not new:
        print("No new vector (climax) candles since the last scan.")
        return
    print(f"Logged {len(new)} new vector candle(s) to data/vector_log.json:")
    for e in new:
        agree = "agree" if e.agree else "fights"
        print(f"  {e.symbol} [{e.timeframe}] {e.vector} @ {e.close:.4g}  "
              f"at {e.level} ({e.level_dist_atr:+.2f} ATR)  vol x{e.vol_ratio:.1f}  "
              f"conf {e.confluence_pct:.0%} ({agree})  {e.timestamp}")
    print("\nA vector candle marks WHERE volume showed up — a hypothesis, not a "
          "signal. Run `vector-study` to test whether these precede a move.")


def _vector_study(args) -> None:
    from .signals.vector_study import study_symbols, summarize
    rows = study_symbols(args.symbols, args.intervals, limit=args.limit,
                         max_bars=args.max_bars, stop_atr=args.stop_atr,
                         target_r=args.target_r)
    if not rows:
        print("No vector candles found over the requested window.")
        return
    print(f"Vector-candle study — {len(rows)} climax candles, simulated as a "
          f"{args.target_r}R bracket from the close (taker fee in R, NET shown).")
    for by, title in [(("level",), "by chart location (where it formed)"),
                      (("agree",), "by confluence agreement"),
                      (("vector", "timeframe"), "by climax type x timeframe")]:
        print(f"\n== {title} ==")
        t = summarize(rows, by)
        print(t.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nHONEST: market-at-close (taker) entry — the conservative read; the live "
          "system enters on a maker limit-retrace (cheaper). §37: trading 1m/5m is "
          "fee-poisoned. Treat positive buckets as hypotheses to forward-test.")


def _trace_glyphs() -> tuple[str, str, str]:
    """(agree, oppose, neutral) glyphs, ASCII fallback if stdout can't encode."""
    import sys
    try:
        "✓×·".encode(sys.stdout.encoding or "utf-8")
        return "✓", "×", "·"
    except (UnicodeEncodeError, LookupError):
        return "+", "x", "."


def _print_trace(rows: list[dict], events: dict[str, list[str]], ref_dir: float,
                 ref_label: str = "the trade direction") -> None:
    """One row per bar, one cell per factor: agree/oppose/neutral vs ``ref_dir``."""
    from .confluence.trace import FACTOR_SPECS
    ok, no, dot = _trace_glyphs()
    ref = ref_dir if ref_dir != 0 else 1.0
    head = "  ".join(s.short for s in FACTOR_SPECS)
    stamp_w = max((len(str(r["timestamp"])[:16]) for r in rows), default=16)
    print(f"{'':{stamp_w}}  {head} | net  pct")
    for k, row in enumerate(rows):
        cells = []
        votes = {f["key"]: f["vote"] for f in row["factors"]}
        for s in FACTOR_SPECS:
            v = votes.get(s.key)
            if v is None:
                cells.append(" " * len(s.short))
            else:
                g = dot if v == 0 else (ok if v * ref > 0 else no)
                cells.append(f" {g}" + " " * (len(s.short) - 2))
        mark = "  ◄ " + ", ".join(events[str(k)]) if str(k) in events else ""
        pre = " (pre)" if row.get("pre") else ""
        print(f"{str(row['timestamp'])[:16]:{stamp_w}}  {'  '.join(cells)} | "
              f"{row['net_score']:+3d}  {row['confluence_pct']:4.0%}{mark}{pre}")
    print(f"\nkey: {ok} agrees / {no} opposes / {dot} neutral (vs {ref_label}"
          f"{'' if ref_dir != 0 else ', flat -> long'}); "
          "columns: " + ", ".join(f"{s.short.strip()}={s.label}" for s in FACTOR_SPECS))


def _trade_trace(args) -> None:
    """ASCII per-bar factor timeline — replay a journal trade, or live mode."""
    if bool(args.trade_id) == bool(args.symbol):
        print("Provide exactly one of: a trade id, or --symbol SPEC for live mode.")
        return
    if args.symbol:
        from .confluence.trace import factor_trace
        from .ingest import RouterClient
        f = build_levels(RouterClient().klines(args.symbol.upper(),
                                               interval=args.interval, limit=600))
        rows = factor_trace(f, bars=args.bars)
        last = rows[-1]
        side = "LONG" if last["direction"] > 0 else ("SHORT" if last["direction"] < 0 else "FLAT")
        print(f"live {args.symbol.upper()} {args.interval} — last bar {side} "
              f"{last['confluence_pct']:.0%} confluence (net {last['net_score']:+d})\n")
        _print_trace(rows, {}, ref_dir=last["direction"],
                     ref_label="the final bar's direction")
        print("\nHonest read: a directional vote map, not advice; the validated gate is "
              ">=50% confluence WITH the 800-EMA trend.")
    else:
        from .replay import replay_trade
        rep = replay_trade(args.trade_id)
        t = rep["trade"]
        side = "LONG" if t["direction"] > 0 else "SHORT"
        res = (f" -> {t['status'].upper()}"
               + (f" {t['outcome_r']:+g}R" if t["outcome_r"] is not None else ""))
        print(f"trade {t['id']}  {t['symbol']} {t['timeframe']} {side}  "
              f"entry {t['entry']:g}  stop {t['stop']:g}  target {t['target']:g} "
              f"({t['target_r']:g}R){res}\n")
        _print_trace(rep["bars"], rep["events"], ref_dir=t["direction"])
        print(f"\nHonest read: {rep['caveat']}")


def _review_open_trades(args) -> None:
    import json
    from .review import open_trades_report, render_open_text
    rep = open_trades_report()
    print(json.dumps(rep, indent=2, default=str) if args.json else render_open_text(rep))


def _review_trade_history(args) -> None:
    import json
    from .review import render_history_text, trade_history_report
    rep = trade_history_report(
        symbol=args.symbol, date_from=args.date_from, date_to=args.date_to,
        mode=args.mode, status=args.status, timeframe=args.timeframe,
        with_excursion=not args.no_excursion)
    print(json.dumps(rep, indent=2, default=str) if args.json else render_history_text(rep))


def _losing_clusters(args) -> None:
    import json
    from .cluster import losing_cluster_report, render_cluster_text
    rep = losing_cluster_report(min_n=args.min_n, mode=args.mode, fdr_alpha=args.fdr_alpha)
    print(json.dumps(rep, indent=2, default=str) if args.json else render_cluster_text(rep))


def _daily_graph(args) -> None:
    import json
    from pathlib import Path
    from .daily_graph import daily_graph_report, render_daily_svg, render_daily_text
    rep = daily_graph_report(hours=args.hours, end=args.end, mode=args.mode)
    if args.json:
        print(json.dumps(rep, indent=2, default=str))
        return
    print(render_daily_text(rep))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_daily_svg(rep))
        print(f"\nGraph written to {out} ({rep['window']['n_resolved']} trades plotted).")


def _notify_test(args) -> None:
    """Send a one-off Telegram test ping to confirm the wiring + secrets."""
    from .notifications import notify_test, telegram_enabled
    if not telegram_enabled():
        print("Telegram is not configured (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID, "
              "and don't set KUDBEE_TELEGRAM_ENABLED to a false value). Nothing sent.")
        return
    print("Test ping sent." if notify_test() else "Telegram send failed (check token/chat id).")


def _notify_summary(args) -> None:
    """Send the portfolio snapshot to Telegram (used by the hourly Action)."""
    from .notifications import notify_summary, telegram_enabled
    if not telegram_enabled():
        print("Telegram is not configured — no summary sent.")
        return
    only_if_open = getattr(args, "only_if_open", False)
    sent = notify_summary(only_if_open=only_if_open)
    if sent:
        print("Summary sent.")
    elif only_if_open:
        print("No open positions — reminder skipped (silent when flat).")
    else:
        print("Telegram send failed (check token/chat id).")


def _notify_session(args) -> None:
    """Fire a Telegram session-open alert (Asia/London/NY + key levels) if the
    current hour is a session open. Used by the hourly Action; muted if Telegram
    is unconfigured or no session opens this hour."""
    from .notifications import telegram_enabled
    if not telegram_enabled():
        print("Telegram is not configured — no session alert sent.")
        return
    from .notifications.session_alerts import run_session_alerts
    fired = run_session_alerts(verbose=True)
    print(f"Session alert(s) fired: {', '.join(fired)}" if fired
          else "No session open this hour — nothing sent.")


def _notify_scorecard(args) -> None:
    """Send the per-book forward scorecard (KEEP/REVERT/WAIT) to Telegram."""
    from .notifications import telegram_enabled
    if not telegram_enabled():
        print("Telegram is not configured — no scorecard sent.")
        return
    from . import scorecard as sc
    mode = None if args.mode == "all" else args.mode
    ok = sc.notify_scorecard(mode=mode, since=args.since)
    print("Scorecard sent to Telegram." if ok else "Telegram muted/failed — not sent.")


def _scorecard(args) -> None:
    """Forward-validation scorecard: per-book net-of-fee verdicts (KEEP/REVERT/WAIT),
    optionally with toxic-hour and regime breakdowns. Read-only over the journal."""
    from . import scorecard as sc
    mode = None if args.mode == "all" else args.mode
    if args.report is not None:
        sc.write_forward_report(args.report, mode=mode, since=args.since)
        print(f"Wrote forward report -> {args.report}")
    if args.notify:
        ok = sc.notify_scorecard(mode=mode, since=args.since)
        print("Scorecard sent to Telegram." if ok else "Telegram muted/failed — not sent.")
    card = sc.book_scorecard(mode=mode, since=args.since)
    win = f" since {args.since}" if args.since else ""
    print(f"\nForward scorecard ({mode or 'all'} mode{win}, net of fees; "
          f"KEEP/REVERT need >={card['wait_min_n']} trades):")
    if not card["books"]:
        print("  (no resolved trades in this window)")
        return
    print(f"  {'book':14} {'n':>4} {'expR/t':>8} {'win%':>5} {'totalR':>8} {'maxDD':>7}  verdict")
    for b, st in sorted(card["books"].items(), key=lambda kv: kv[1]["expectancy_r"], reverse=True):
        print(f"  {b:14} {st['n']:>4} {st['expectancy_r']:>+8.3f} {st['win_rate']:>5.0%} "
              f"{st['total_r']:>+8.1f} {st['max_drawdown_r']:>7.1f}  {st['verdict']}")
    ov = card["overall"]
    if ov:
        print(f"  {'OVERALL':14} {ov['n']:>4} {ov['expectancy_r']:>+8.3f} {ov['win_rate']:>5.0%} "
              f"{ov['total_r']:>+8.1f} {ov['max_drawdown_r']:>7.1f}")
    if args.by_hour:
        hrs = sc.book_hour_breakdown(mode=mode, since=args.since)
        toxic = ", ".join(f"{h:02d}h" for h in hrs["toxic_hours"]) or "none"
        print(f"\n  Toxic entry hours (UTC, >={hrs['min_n']} trades & net-negative): {toxic}")
    if args.by_regime:
        reg = sc.book_regime_breakdown(mode=mode, since=args.since)
        print("\n  By entry-vol regime (ATR% terciles):")
        for rn in ("low", "mid", "high", "unknown"):
            st = reg["regimes"].get(rn)
            if st:
                print(f"    {rn:8} n={st['n']:>4}  exp {st['expectancy_r']:+.3f}R/t  total {st['total_r']:+.1f}R")


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

    ur = sub.add_parser("universe-rank",
                        help="rank a candidate pool by USD volume (opt-in dynamic universe, §B)")
    ur.add_argument("candidates", nargs="*",
                    help="symbols to rank (default: universe.CRYPTO_CANDIDATES)")
    ur.add_argument("--top-n", type=int, default=10, dest="top_n")
    ur.add_argument("--interval", default="1h")
    ur.add_argument("--lookback", type=int, default=168, help="bars of volume to average")
    ur.set_defaults(func=_universe_rank)

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

    cs = sub.add_parser("confluence-stack", help="test whether stacked confluence wins (OOS)")
    cs.add_argument("symbol")
    cs.add_argument("--interval", default="1h")
    cs.add_argument("--limit", type=int, default=4000)
    cs.add_argument("--horizon", type=int, default=8)
    cs.add_argument("--min-n", type=int, default=50)
    cs.set_defaults(func=_confluence_stack)

    au = sub.add_parser("audit", help="lookahead self-audit of every scenario")
    au.add_argument("symbol")
    au.add_argument("--interval", default="1h")
    au.add_argument("--limit", type=int, default=2000)
    au.add_argument("--checks", type=int, default=60)
    au.set_defaults(func=_audit)

    vr = sub.add_parser("validate-r", help="walk-forward + cost validation of confluence-R")
    vr.add_argument("symbols", nargs="+")
    vr.add_argument("--interval", default="1h")
    vr.add_argument("--limit", type=int, default=4000)
    vr.add_argument("--folds", type=int, default=6)
    vr.add_argument("--min-strength", type=float, default=5.0)
    vr.add_argument("--target-r", type=float, default=2.0)
    vr.add_argument("--stop-atr", type=float, default=1.0)
    vr.add_argument("--fee-r", type=float, default=0.02)
    vr.set_defaults(func=_validate_r)

    bs = sub.add_parser("bracket-sweep", help="rank scenarios by R expectancy (stop/target)")
    bs.add_argument("symbols", nargs="+")
    bs.add_argument("--interval", default="1h")
    bs.add_argument("--limit", type=int, default=4000)
    bs.add_argument("--target-r", type=float, default=2.0)
    bs.add_argument("--stop-atr", type=float, default=1.0)
    bs.add_argument("--max-bars", type=int, default=24)
    bs.set_defaults(func=_bracket_sweep)

    from .config.validated_defaults import (
        STOP_ATR as _STOP_ATR, RETRACE_ATR as _RETRACE_ATR,
        MAX_BARS as _MAX_BARS, ENTRY_WINDOW as _ENTRY_WINDOW, FEE_PCT as _FEE_PCT,
    )
    tb = sub.add_parser("tp-backtest",
                        help="single-asset bracket backtest with 3-leg scale-out + leverage")
    tb.add_argument("symbol", help="e.g. yahoo:QQQ  yahoo:NQ=F  BTCUSDT")
    tb.add_argument("--interval", default="1d")
    tb.add_argument("--limit", type=int, default=400)
    tb.add_argument("--scenario", default="confluence_stack",
                    help="entry-signal scenario (default: confluence_stack)")
    tb.add_argument("--stop-atr", type=float, default=_STOP_ATR)
    tb.add_argument("--retrace-atr", type=float, default=_RETRACE_ATR)
    tb.add_argument("--entry-window", type=int, default=_ENTRY_WINDOW)
    tb.add_argument("--max-bars", type=int, default=_MAX_BARS)
    tb.add_argument("--fee-pct", type=float, default=_FEE_PCT,
                    help="round-trip cost as fraction of price (0 = zero-fee venue)")
    tb.add_argument("--tp1-r", type=float, default=1.5, help="TARGET ONE in R")
    tb.add_argument("--tp1-frac", type=float, default=0.75, help="fraction banked at TP1")
    tb.add_argument("--tp2-r", type=float, default=2.5, help="TARGET TWO in R")
    tb.add_argument("--tp2-frac", type=float, default=0.10,
                    help="fraction banked at TP2 (0 disables the second leg)")
    tb.add_argument("--target-r", type=float, default=2.75, help="final runner target in R")
    tb.add_argument("--leverage", type=float, default=1.25)
    tb.add_argument("--oos-frac", type=float, default=0.0,
                    help="hold out the last fraction as out-of-sample (e.g. 0.3); "
                         "0 = full sample (flatters)")
    tb.add_argument("--no-be", action="store_true",
                    help="do NOT move stop to breakeven after TP1")
    tb.set_defaults(func=_tp_backtest)

    sw = sub.add_parser("sweep", help="test the scenario battery across assets (OOS-ranked)")
    sw.add_argument("symbols", nargs="+", help="e.g. BTCUSDT ETHUSDT SOLUSDT yahoo:SPY")
    sw.add_argument("--interval", default="1h")
    sw.add_argument("--limit", type=int, default=4000)
    sw.add_argument("--hold", type=int, default=12, help="bars to hold each trigger")
    sw.set_defaults(func=_sweep)

    ja = sub.add_parser("journal-add", help="log a chart-read prediction")
    ja.add_argument("symbol")
    ja.add_argument("--kind", required=True,
                    choices=["touch", "reach_above", "reach_below", "stay_below", "stay_above"])
    ja.add_argument("--level", type=float, required=True)
    ja.add_argument("--days", type=float, default=7.0)
    ja.add_argument("--setup", default="")
    ja.add_argument("--timeframe", default="1h")
    ja.add_argument("--note", default="")
    ja.set_defaults(func=_journal_add)

    ia = sub.add_parser("ingest-alerts", help="ingest hosted TV alerts (data/alert_inbox/) into the journal")
    ia.set_defaults(func=_ingest_alerts)
    jc = sub.add_parser("journal-check", help="re-evaluate open predictions vs price")
    jc.set_defaults(func=_journal_check)
    jl = sub.add_parser("journal-list", help="list all predictions")
    jl.set_defaults(func=_journal_list)
    js = sub.add_parser("journal-score", help="your measured hit rate + R by setup")
    js.set_defaults(func=_journal_score)
    ra = sub.add_parser("read-add", help="log YOUR discretionary read (scored apart from the bot)")
    ra.add_argument("symbol")
    ra.add_argument("side", choices=["long", "short"])
    ra.add_argument("--entry", type=float, required=True)
    ra.add_argument("--stop", type=float, required=True)
    ra.add_argument("--target", type=float, default=None, help="explicit target price (else use --target-r)")
    ra.add_argument("--target-r", type=float, default=3.0, help="reward:risk if no explicit target")
    ra.add_argument("--tf", default="1h", help="timeframe label, e.g. 1m 5m 1h")
    ra.add_argument("--days", type=float, default=1.0, help="how long the read has to play out")
    ra.add_argument("--note", default="", help="the confluences/reasoning you saw")
    ra.set_defaults(func=_read_add)

    je = sub.add_parser("journal-exposure", help="combined long+short risk per coin (two-sided guard)")
    je.add_argument("--risk", type=float, default=0.01, help="risk per trade as a fraction (0.01 = 1%)")
    je.add_argument("--max-risk", type=float, default=0.02, help="gross risk cap per coin (0.02 = 2%)")
    je.set_defaults(func=_journal_exposure)

    tfs = sub.add_parser("tf-survey", help="where does the edge live across timeframes?")
    tfs.add_argument("symbol")
    tfs.add_argument("--fee-pct", type=float, default=0.0004, help="round-trip cost fraction (maker)")
    tfs.set_defaults(func=_tf_survey)

    bset = sub.add_parser("bias-set", help="set your directional read (bot scalps WITH it)")
    bset.add_argument("symbol")
    bset.add_argument("side", choices=["long", "short"])
    bset.add_argument("--target", type=float, default=None)
    bset.add_argument("--days", type=float, default=1.0, help="how long the read stays active")
    bset.add_argument("--note", default="", help="the confluences/reasoning you saw")
    bset.set_defaults(func=_bias_set)
    blist = sub.add_parser("bias-list", help="show active directional reads")
    blist.set_defaults(func=_bias_list)
    bclr = sub.add_parser("bias-clear", help="clear a symbol's bias")
    bclr.add_argument("symbol")
    bclr.set_defaults(func=_bias_clear)

    ps = sub.add_parser("paper-scan", help="log live confluence-R signals as paper trades")
    ps.add_argument("symbols", nargs="+", help="e.g. BTCUSDT ETHUSDT SOLUSDT")
    ps.add_argument("--intervals", nargs="+", default=["1h"],
                    help="timeframes to scan, e.g. 5m 15m 1h 2h 4h (1h is the validated core; "
                         "lower TFs are cost-sensitive — forward-test before trusting)")
    ps.add_argument("--min-pct", type=float, default=0.5,
                    help="confluence percentage threshold (0.5 = validated floor)")
    ps.add_argument("--target-r", type=float, default=3.0)
    ps.add_argument("--stop-atr", type=float, default=1.5,
                    help="stop distance in ATR (1.5 = validated)")
    ps.add_argument("--tp1-r", type=float, default=None,
                    help="optional TARGET ONE (partial bank), e.g. 1.5; default off (full target)")
    ps.add_argument("--tp1-frac", type=float, default=0.5,
                    help="fraction banked at TP1 (0.0 = breakeven-only: bank nothing, ride full size to target)")
    ps.add_argument("--no-be", action="store_true",
                    help="do NOT move stop to breakeven after TP1")
    ps.add_argument("--risk-per-trade", type=float, default=0.01,
                    help="risk per trade as a fraction of account (0.01 = 1%)")
    ps.add_argument("--max-symbol-risk", type=float, default=0.02,
                    help="cap on COMBINED long+short risk per coin (0.02 = 2%)")
    ps.add_argument("--trend-filter", action="store_true",
                    help="skip signals that fight the 800-EMA HTF trend (tested: +~0.05R, keeps ~83%)")
    ps.add_argument("--long-only", action="store_true",
                    help="only take LONG signals, skip shorts "
                         "(5m excursion: longs 32%% vs shorts 14%%, n=48 — experimental)")
    ps.add_argument("--killzone-gate", action="store_true",
                    help="only take signals in London/NY/Brinks windows "
                         "(NOT validated for 5m — experimental, default off)")
    ps.add_argument("--trailing-atr", type=float, default=None,
                    help="chandelier trailing stop: trail at this many ATR behind the "
                         "favourable extreme (e.g. 1.5 = 1R at stop_atr 1.5); default off")
    ps.add_argument("--clean-trend-stack", action="store_true", default=False,
                    help="[§C experiment, UNVERIFIED] only trade when 13/50/800-EMA are "
                         "cleanly stacked for 10 bars AND the 13/50 gap is widening")
    ps.set_defaults(func=_paper_scan)

    vs = sub.add_parser("vector-scan",
                        help="log PVSRA vector (climax) candles + where on the chart they formed")
    vs.add_argument("symbols", nargs="+", help="e.g. BTCUSDT ETHUSDT SOLUSDT")
    vs.add_argument("--intervals", nargs="+", default=["5m", "15m", "1h"],
                    help="timeframes to scan for vector candles")
    vs.add_argument("--limit", type=int, default=300, help="bars to fetch per symbol/TF")
    vs.add_argument("--all", action="store_true",
                    help="log EVERY climax in the window (default: only the latest bar)")
    vs.set_defaults(func=_vector_scan)

    vst = sub.add_parser("vector-study",
                         help="do vector (climax) candles precede a move? bucketed by chart location")
    vst.add_argument("symbols", nargs="+", help="e.g. BTCUSDT ETHUSDT SOLUSDT")
    vst.add_argument("--intervals", nargs="+", default=["5m", "15m", "1h"])
    vst.add_argument("--limit", type=int, default=1000, help="bars of history per symbol/TF")
    vst.add_argument("--max-bars", type=int, default=24, help="forward bars to resolve each trade")
    vst.add_argument("--stop-atr", type=float, default=1.0)
    vst.add_argument("--target-r", type=float, default=3.0)
    vst.set_defaults(func=_vector_study)

    rot = sub.add_parser("review-open-trades",
                         help="detailed report of every open/pending trade (+ portfolio)")
    rot.add_argument("--json", action="store_true", help="emit graph-ready JSON instead of text")
    rot.set_defaults(func=_review_open_trades)

    rth = sub.add_parser("review-trade-history",
                         help="historical performance report with filters (+ equity curve)")
    rth.add_argument("--symbol", default=None, help="filter to one symbol, e.g. BTCUSDT")
    rth.add_argument("--from", dest="date_from", default=None, help="ISO date/time lower bound")
    rth.add_argument("--to", dest="date_to", default=None, help="ISO date/time upper bound")
    rth.add_argument("--mode", choices=["paper", "live"], default=None, help="filter by mode")
    rth.add_argument("--status", default="closed",
                     choices=["closed", "open", "all", "hit", "miss", "cancelled"],
                     help="which trades to include (default: closed)")
    rth.add_argument("--timeframe", default=None, help="filter by timeframe, e.g. 1h")
    rth.add_argument("--no-excursion", action="store_true",
                     help="skip MFE/MAE backfill (faster; no network)")
    rth.add_argument("--json", action="store_true", help="emit graph-ready JSON instead of text")
    rth.set_defaults(func=_review_trade_history)

    lc = sub.add_parser("losing-clusters",
                        help="do losing trades CLUSTER (regime mismatch) or is it variance?")
    lc.add_argument("--min-n", type=int, default=20,
                    help="min samples for a bucket to be trusted (default 20)")
    lc.add_argument("--mode", choices=["paper", "live"], default=None, help="filter by mode")
    lc.add_argument("--fdr-alpha", type=float, default=0.10,
                    help="false-discovery-rate target across buckets (default 0.10)")
    lc.add_argument("--json", action="store_true", help="emit graph-ready JSON instead of text")
    lc.set_defaults(func=_losing_clusters)

    dg = sub.add_parser("daily-graph",
                        help="the last 24h of trades as an SVG equity curve + day summary")
    dg.add_argument("--hours", type=float, default=24.0,
                    help="trailing window width in hours (default 24)")
    dg.add_argument("--out", default="data/daily_graph.svg",
                    help="SVG output path (default data/daily_graph.svg); '' to skip the file")
    dg.add_argument("--end", default=None,
                    help="ISO timestamp to anchor the window end (default: now, UTC)")
    dg.add_argument("--mode", choices=["paper", "live"], default=None, help="filter by mode")
    dg.add_argument("--json", action="store_true", help="emit graph-ready JSON instead of text")
    dg.set_defaults(func=_daily_graph)

    p = sub.add_parser("polymarkets", help="list Polymarket markets")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_polymarkets)

    nt = sub.add_parser("notify-test", help="send a Telegram test ping (verify token/chat id)")
    nt.set_defaults(func=_notify_test)
    nsum = sub.add_parser("notify-summary", help="send the portfolio snapshot to Telegram")
    nsum.add_argument("--only-if-open", action="store_true", dest="only_if_open",
                      help="skip sending when there are no open positions (silent when flat)")
    nsum.set_defaults(func=_notify_summary)
    nses = sub.add_parser("notify-session",
                          help="fire a Telegram session-open alert (Asia/London/NY + key levels)")
    nses.set_defaults(func=_notify_session)
    scd = sub.add_parser("scorecard",
                         help="forward-validation scorecard: per-book KEEP/REVERT/WAIT (net of fees)")
    scd.add_argument("--mode", choices=["paper", "live", "all"], default="paper")
    scd.add_argument("--since", default=None,
                     help="only score trades resolved on/after this date (YYYY-MM-DD) — the forward window")
    scd.add_argument("--by-hour", action="store_true", dest="by_hour",
                     help="also show toxic entry-hour breakdown")
    scd.add_argument("--by-regime", action="store_true", dest="by_regime",
                     help="also show expectancy by entry-vol regime")
    scd.add_argument("--report", default=None, metavar="PATH",
                     help="write a markdown forward report to PATH")
    scd.add_argument("--notify", action="store_true", help="also send the scorecard to Telegram")
    scd.set_defaults(func=_scorecard)
    nsc = sub.add_parser("notify-scorecard",
                         help="send the per-book forward scorecard (KEEP/REVERT/WAIT) to Telegram")
    nsc.add_argument("--mode", choices=["paper", "live", "all"], default="paper")
    nsc.add_argument("--since", default=None, help="only score trades resolved on/after this date")
    nsc.set_defaults(func=_notify_scorecard)

    tt = sub.add_parser("trade-trace",
                        help="ASCII per-bar factor timeline for a journal trade (or live --symbol)")
    tt.add_argument("trade_id", nargs="?", default=None,
                    help="journal trade id (8 hex chars) to replay")
    tt.add_argument("--symbol", default=None,
                    help="live mode: trace a symbol spec instead (e.g. BTCUSDT, yahoo:GC=F)")
    tt.add_argument("--interval", default="1h", help="live mode timeframe")
    tt.add_argument("--bars", type=int, default=48, help="live mode: bars of history")
    tt.set_defaults(func=_trade_trace)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
