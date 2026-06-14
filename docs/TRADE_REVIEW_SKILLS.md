# Trade review skills

Two read-only reports over `data/journal.json`, available as CLI commands and as
`/`-skills. They work for both paper and (future) live records. Not financial advice.

## `/review-open-trades`

```bash
python -m kudbee_quant.cli review-open-trades [--json]
```

Per open/pending trade: symbol, timeframe, mode, entry time/price, **current
price**, unrealized PnL (R / % / USD), **MFE/MAE** since entry, TP1/TP2/stop
touched, TP1 filled, distances to TP1/TP2/stop, time-in-trade, a **health label**
(`healthy` / `warning` / `near TP` / `near stop` / `stale` / `pending`), and a
plain-English summary. Portfolio block: open count, total unrealized (R/USD),
winners/losers, total open risk %, closest-to-stop / closest-to-TP, warnings.

- USD only shows when a trade has `position_size_usd`; otherwise R/% are the truth.
- Implementation: `kudbee_quant/review.py:open_trades_report`.

## `/review-trade-history`

```bash
python -m kudbee_quant.cli review-trade-history \
  [--symbol BTCUSDT] [--from ISO] [--to ISO] [--mode paper|live] \
  [--status closed|open|all|hit|miss|cancelled] [--timeframe 1h] \
  [--no-excursion] [--json]
```

Per closed trade: realized PnL (R / % / USD), modeled exit price, MFE/MAE,
ever-in-profit / ever-in-loss, TP1/TP2 touched + filled, stop touched, exit reason,
duration. Portfolio analytics: total trades, win/loss rate, avg win/loss, profit
factor, expectancy, best/worst, most-traded, best/worst symbols, per-symbol,
per-hour, TP1/TP2/stop hit rates, avg MFE/MAE, and an **equity curve**.

- `--no-excursion` skips the MFE/MAE OHLCV backfill (faster, fully offline; those
  fields then show `n/a`).
- Implementation: `kudbee_quant/review.py:trade_history_report`.

## How the fields are computed

- **MFE/MAE + touches + current mark:** `kudbee_quant/journal/excursion.py`
  re-fetches OHLCV over each trade's life via the shared `RouterClient` and walks
  bars (direction-aware, R-normalized by the trade's own stop).
- **Touched vs filled:** *touched* = price reached the level (from OHLCV); *filled*
  = the journal recorded it (`tp1_filled_at`, or `status == "hit"` for the target).
- **TP2 = `target`:** the journal models `tp1` as TARGET ONE and `target` as TARGET
  TWO; the reports follow that.

## Graphing

`--json` emits structured data (snake_case, matching `/api/journal` conventions):
per-trade dicts, a portfolio block, and an `equity_curve` (`cum_r` over time). From
those you can chart equity, drawdown (running peak − `cum_r`), per-symbol bars,
TP/stop hit rates, and the duration distribution (`duration_hours`). No frontend is
added here — this is the data foundation.

## Tests

`tests/test_review.py` covers no-open-trades, profitable/losing opens, TP1
touched-not-filled, near-stop, empty history, the metric math, filters, and
excursion-based hit rates.
