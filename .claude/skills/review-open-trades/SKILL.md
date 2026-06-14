---
name: review-open-trades
description: Detailed report of every currently OPEN/pending trade — live mark, unrealized PnL (R/%/USD), MFE/MAE since entry, TP1/TP2/stop touches and distances, time-in-trade, a health label, and a plain-English summary, plus a portfolio block (open count, total unrealized, winners/losers, open risk, closest-to-stop/TP, warnings). Use when the user asks "how are my open trades / positions doing", "show open trades", "review open positions". Works for paper and live records.
---

# /review-open-trades — live view of the open book

Run the CLI command (it reads `data/journal.json` and marks each open/pending
bracket against the latest bar via the shared `RouterClient`):

```bash
python -m kudbee_quant.cli review-open-trades
```

- Add `--json` for graph-ready structured output (per-trade dicts + a portfolio
  block) instead of the text table.
- Implementation: `kudbee_quant/review.py:open_trades_report` +
  `kudbee_quant/journal/excursion.py` (MFE/MAE). No journal writes — read-only.

Health labels are coarse and honest: `near stop` / `near TP` / `stale` /
`warning` / `healthy` / `pending` (unfilled limit). USD PnL only shows for trades
that carry a `position_size_usd`; otherwise R and % are the truth and USD is `n/a`.

After reporting, summarize the riskiest position (closest to stop) and anything
flagged in `warnings`. Not financial advice.
