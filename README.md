# Kudbee Quant

An **honest** quantitative trading research toolkit for crypto and prediction
markets — built as the deliberate inverse of the viral "AI trading terminal"
screenshots. No fake Sharpe ratios, no "low risk / huge return" promises. Every
signal is a hypothesis to be *measured*; risk is reported as loudly as return.

This repository is one unit:

| Path | What it is |
|---|---|
| `kudbee_quant/` | The Python engine (ingestion, signals, backtest, confluence, paper loop, API) |
| `research/` | The Traders Reality / ICT / BTMM research corpus (Vols 1–10) |
| `docs/research/` | Honest findings & the testable rule set (what survived the null) |
| `*.html`, `assets/`, `blog/` | The static marketing/education website (Cloudflare Pages) |
| `kudbee_quant/api.py` | FastAPI backend that serves the website's Live Signals page |

## The validated strategy (what survived honest testing)

After testing the whole PVSRA/BTMM/ICT corpus, **adding confluence factors did
not help** (the 10-factor set is saturated). The edge came from **execution and
R:R**, validated walk-forward across crypto + equities + gold:

> **1h timeframe · ≥50% confluence · 3R target · LIMIT entry on a 0.25-ATR
> retrace (maker) · both directions · sized small.**

Honest caveats: it's a *modest*, regime-dependent edge (stronger in trends,
short-led in downtrends), execution-gated (needs maker fills), with real
drawdowns. Forward/paper testing is the final proof — which the paper loop now
accumulates. See `docs/research/testable_ruleset.md` and `docs/PHILOSOPHY.md`.

## Quick start (engine)

```bash
pip install -r requirements.txt
python -m pytest tests/ -q

python -m kudbee_quant.cli vectors BTCUSDT --interval 1h
python -m kudbee_quant.cli confluence-stack SOLUSDT --interval 1h
python -m kudbee_quant.cli bracket-sweep BTCUSDT ETHUSDT SOLUSDT
python -m kudbee_quant.cli paper-scan BTCUSDT ETHUSDT SOLUSDT   # logs validated 3R limit trades
python -m kudbee_quant.cli journal-check                        # resolve them
python -m kudbee_quant.cli journal-score                        # forward R expectancy
```

## Run it as one unit (site + API)

```bash
# 1) backend API (serves live signals to the site)
uvicorn kudbee_quant.api:app --port 8000
# 2) static site (any static server; production is Cloudflare Pages). The site
#    calls /api/* which the Pages Function functions/api/[[path]].js proxies to
#    the FastAPI backend on Fly.io (see docs/HOSTING.md). Open live-signals.html.
```

## Honesty layer

No hardcoded performance numbers. Paper-trading by default. Lookahead self-audit
on every signal. Realistic, timeframe-aware costs. Multiple-comparisons control.
Walk-forward + uncorrelated-asset validation. When something doesn't beat the
null, the docs say so.

> Not financial advice. Markets do not offer high return at low risk. This tool
> exists to measure edge honestly — including discovering when there isn't any.
