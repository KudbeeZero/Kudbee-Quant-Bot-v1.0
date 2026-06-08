# Kudbee Quant Bot

An **honest** quantitative trading research toolkit for crypto and
prediction markets.

We are deliberately building the inverse of the viral "AI trading terminal"
screenshots. No hardcoded PnL, no fake Sharpe ratios, no "low risk / huge
return" promises. Our edge is *radical honesty about uncertainty*: every
signal is a hypothesis to be measured, and risk is reported as loudly as
return. See [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md).

## What's here (v0.1)

- **Ingestion** (`kudbee_quant.ingest`)
  - `BinanceClient` — public spot OHLCV, cached, auto-paging history.
  - `PolymarketClient` — prediction-market metadata + CLOB prices.
- **Signals** (`kudbee_quant.signals`)
  - `pvsra_vector_candles` — Traders Reality (Tino) PVSRA vector candles,
    Python port. Pine Script version in
    [`pinescript/pvsra_vector_candles.pine`](pinescript/pvsra_vector_candles.pine).

## Quick start

```bash
pip install -r requirements.txt

python -m kudbee_quant.cli klines BTCUSDT --interval 5m --limit 300
python -m kudbee_quant.cli vectors BTCUSDT --interval 1h --limit 500
python -m kudbee_quant.cli polymarkets --limit 20
```

## Tests

```bash
python -m pytest tests/ -q
```

## Roadmap

Backtester, Monte-Carlo risk engine, walk-forward validation, MM-cycle
context, correlation graph, orchestrator pipeline, and a dashboard where
every number carries a confidence interval. Tracked in the philosophy doc.

> Nothing here is financial advice. Markets do not offer high return at low
> risk. This tool exists to help you measure edge honestly — including
> discovering when there isn't any.
