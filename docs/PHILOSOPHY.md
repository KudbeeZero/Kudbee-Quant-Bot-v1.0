# Kudbee Quant — Design Philosophy & Honesty Contract

## Why this project exists

The viral "AI trading terminal" screenshots — Sharpe 4.9, 41,000% APY,
"LIQ RISK 1.7/10 · SAFE", 99.1% success — are **marketing aesthetics, not
track records**. The numbers don't reconcile with each other, the Sharpe
ratios exceed the best fund in history, and "high return + low risk" is the
one thing efficient-ish markets structurally do not hand out.

We are building the **inverse** of that. Our competitive advantage is
*radical honesty about uncertainty*. The flashy tools optimize for looking
right; this one optimizes for being right and surviving when it's wrong.

## The honesty contract (enforced in code)

1. **No hardcoded performance numbers.** If a figure can't be computed from
   real data, it does not render. Ever.
2. **Paper-trading is the default.** Live capital is an explicit, guarded
   opt-in with hard drawdown limits.
3. **Every signal is a hypothesis.** PVSRA vector candles, ML scores,
   correlation reads — all are features to be *measured*, never promises.
4. **Risk is reported as loudly as return.** Max drawdown, risk-of-ruin,
   CVaR, and out-of-sample decay sit next to every PnL figure.
5. **Validation is adversarial.** Walk-forward + Monte Carlo by default.
   We hunt for the reasons a strategy will fail before trusting it.

## The hybrid system (Traders Reality × quant validation)

Tino's Traders Reality methodology (PVSRA / Volume-Spread-Analysis) is a
*discretionary* school: it reads where large players act via volume and
spread climaxes (the "vector candles"). The retail community treats those
reads as certainties.

Our **hybrid** approach keeps the discretionary signal but subjects it to
statistical scrutiny:

    discretionary read (PVSRA vector candles, MM cycle context)
        --> quantified as features
        --> backtested with realistic fees / slippage
        --> walk-forward + Monte Carlo
        --> edge estimate WITH confidence interval and drawdown

The output is not "this is a buy." It is "on this asset and timeframe,
following this vector-candle rule historically produced X edge, with this
drawdown profile and this probability the edge is noise." That honesty is
the product.

## Roadmap (all modules, sequenced)

- [x] Ingestion: Binance OHLCV, Polymarket (crypto + prediction markets)
- [x] Signal: PVSRA vector candles (Pine + Python port)
- [x] Event-driven backtester (fees, slippage, no lookahead)
- [x] Risk engine: Monte Carlo, VaR/CVaR, risk-of-ruin, fractional Kelly
- [x] Walk-forward / out-of-sample validation harness
- [x] Market-maker cycle context (sessions, PDH/PDL/PWH/PWL, sweeps, cycle)
- [ ] Cross-asset correlation / catalyst graph (the "Mirofish" view)
- [ ] Orchestrator: Scan -> Detect -> Validate -> Size -> Fill -> Settle
- [ ] Paper-trading execution; live opt-in with guards
- [ ] Dashboard UI with confidence intervals on every number

## Reality check from the first backtest

The naive PVSRA strategy (long bull-climax / short bear-climax, held as a
regime) on 1000h of BTCUSDT returned **-12.9%**, Sharpe **-2.79**, with only
**~12% probability of profit** in the Monte Carlo band. That is the engine
working: it reported a losing strategy honestly instead of cherry-picking an
equity screenshot. The raw vector-candle read is *not* a strategy on its own
— it needs regime filtering and the MM-cycle context layer. Finding that out
in a backtest, not with real money, is the whole value proposition.

### Adding MM-cycle context (the hybrid step) — and staying skeptical

Filtering PVSRA climaxes by market-maker context (liquidity sweeps,
prev-day levels, London/NY sessions) flipped the same 1000h BTC sample:

| | naive PVSRA | PVSRA + MM context |
|---|---|---|
| total return | -13.3% | +11.3% |
| Sharpe | -2.88 | +2.53 |
| max drawdown | -18.8% | -11.1% |
| MC prob. profit | 10.5% | 79.7% |
| walk-forward OOS Sharpe | n/a | +3.90 |

Encouraging — but the honesty layer requires naming the caveats louder than
the result:

1. **Small sample.** 1000h ≈ 42 days, one asset, one market regime. Not
   enough to trust.
2. **Researcher bias.** The MM filter was designed *knowing* the naive
   version failed. That is a form of overfitting walk-forward can't fully
   detect.
3. **The IS/OOS inversion is a warning, not a win.** In-sample Sharpe was
   **-0.59** while OOS was **+3.90**. A strategy that does far better
   out-of-sample than in-sample is usually exhibiting noise, not robustness.

Conclusion: a hypothesis that survived a first check, **not** a proven edge.
Before any capital, it needs multi-asset, multi-year, truly-unseen testing.
