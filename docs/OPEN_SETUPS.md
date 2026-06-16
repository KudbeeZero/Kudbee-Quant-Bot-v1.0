# Open Setups — tracking board

> Snapshot taken **2026-06-16 ~17:47 UTC**. The manual tickets below are
> discretionary reads entered by hand; the bot book is the paper engine's live
> positions. Live marks move — regenerate the bot book anytime with
> `python -m kudbee_quant.cli review-open-trades`. Not financial advice.

## Manual setups (hand-entered — $100 risked as full 1R, TP1 1.5R / TP2 2.8926R)

| Sym | Dir | Entry | Stop | 1R | TP1 (1.5R) | TP2 (2.8926R) | Size | Lev | Notes |
|---|---|---|---|---|---|---|---|---|---|
| GOOGL | long | 368.74 | 352.00 | 16.74 (4.5%) | 393.85 | 417.16 | 5.97 sh | ~22x | stop below yesterday's low / daily open |
| HYPE | long | 73.61 | 66.30 | 7.31 (9.9%) | 84.58 | 94.75 | 13.68 | ~10x | wide stop — ran ~10% off daily open (66.88) before entry |
| COMP | long | 17.60 | 17.15 | 0.45 (2.6%) | 18.28 | 18.90 | 222.2 | ~39x | reclaim long *under* VWAP (17.94) & daily open (18.07); fits the rotation thesis |

Payoff per ticket if both targets fill: **+2.196R = +$219.63** (TP1 half +$75, TP2
half +$144.63). After TP1, stop → breakeven (locked +$75 min). Full stop = −$100.

**Awaiting input:**
- **ETH** long 1776.42 — needs a valid stop (the 496.72 quoted was ZEC's, not ETH's).

## Bot open book (paper) — snapshot

**69 open · +29.01R unrealized · 41 up / 17 down · 11 pending · open risk ~69% of account.**

- **Closest to a target:** YAHOO:ZB=F (+2.12R), plus near-TP: YAHOO:NG=F (+3.19R),
  YAHOO:BZ=F (+3.15R), UNIUSDT 5m (+3.32R).
- **Closest to stop / flagged:** TRXUSDT (near stop + warning), ENJUSDT 5m (near
  stop), ANKRUSDT (warning), YAHOO:^GSPC (warning).
- **Biggest unrealized:** WLDUSDT 2h +1.59R (+10.2%) & 4h +1.40R (+10.3%),
  UNIUSDT 5m +3.32R, TONUSDT +1.55R.

Full live table: `python -m kudbee_quant.cli review-open-trades`
(JSON: add `--json`). The hourly paper Action owns `data/journal.json`; this file
is a manual tracker only and is not read by the bot.
