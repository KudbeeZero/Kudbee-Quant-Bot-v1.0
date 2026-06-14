---
name: review-trade-history
description: Detailed historical performance report over CLOSED trades — per-trade detail (realized PnL R/%/USD, MFE/MAE, TP1/TP2/stop touched+filled, exit reason, duration) and portfolio analytics (win/loss rate, avg win/loss, profit factor, expectancy, best/worst, per-symbol and per-hour, TP1/TP2/stop hit rates, avg MFE/MAE, equity curve). Supports filters. Use when the user asks "how did my trades do", "show trade history", "what's my track record / win rate / expectancy". Works for paper and live records.
---

# /review-trade-history — measured track record

Run the CLI command (reads `data/journal.json`; honest, no cherry-picking):

```bash
python -m kudbee_quant.cli review-trade-history
```

Filters (combine freely):
- `--symbol BTCUSDT` — one symbol
- `--from 2026-06-01 --to 2026-06-13` — ISO date/time range
- `--mode paper|live` — execution mode
- `--status closed|open|all|hit|miss|cancelled` — default `closed`
- `--timeframe 1h`
- `--no-excursion` — skip MFE/MAE backfill (faster, fully offline; TP/stop hit
  rates and MFE/MAE then show `n/a`)
- `--json` — graph-ready output (trades + portfolio + `equity_curve`)

Implementation: `kudbee_quant/review.py:trade_history_report`. R is the native
unit; USD only appears when a trade carries `position_size_usd`. The equity curve
and per-trade `duration_hours` in `--json` are the inputs for drawdown / duration
charts. Read-only — no journal writes. Not financial advice.
