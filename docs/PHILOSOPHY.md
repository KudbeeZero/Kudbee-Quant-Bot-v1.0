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
- [ ] Market-maker cycle context (weekly templates, session highs/lows)
- [ ] Cross-asset correlation / catalyst graph (the "Mirofish" view)
- [ ] Event-driven backtester (fees, slippage, latency)
- [ ] Risk engine: Monte Carlo, VaR/CVaR, risk-of-ruin, fractional Kelly
- [ ] Walk-forward / out-of-sample validation harness
- [ ] Orchestrator: Scan -> Detect -> Validate -> Size -> Fill -> Settle
- [ ] Paper-trading execution; live opt-in with guards
- [ ] Dashboard UI with confidence intervals on every number
