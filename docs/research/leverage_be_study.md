# Micro-stake / high-leverage / break-even viability study

**Date:** 2026-06-19 · **Branch:** `claude/trade-data-pull-9ympy0` · **Status:** analysis only,
no live changes. **Reproduce:** `PYTHONPATH=. python scripts/leverage_be_study.py`
(read-only over `data/journal.json`; re-fetches each trade's post-fill bar path).
Per-trade metrics for all 497 trades (MFE/MAE, time-to-each-R-threshold, BE-saved /
BE-cuts-a-winner flags, etc.) are exported to **`docs/research/leverage_be_trades.csv`**
(`--csv` flag).

**Timing note (why the BE trigger must be EARLY):** the favourable move arrives
almost immediately — median time to first green ≈ **0h** (the entry bar), to +0.50R
≈ 0.1h, to +1R ≈ 0.8h. The edge is in the first bar or two, which is exactly why
`first-green` / `+0.10R` triggers beat the later ones — and why most of that "green"
is small noise that lives inside the friction band.

## The question

Forward testing showed a very high share of entries go briefly green before their
final outcome. The idea: enter **tiny stake + high leverage**, move the stop to
**break-even once the trade proves direction**. Does that survive fees, spread,
slippage, funding, and liquidation? Sample: **497 of 498 resolved bracket trades**
have usable bar paths (1 old 5m trade lacked OHLCV reach).

## Headline answer

**The "goes green" observation is real, and break-even management genuinely improves
the raw R — but the edge does NOT survive realistic crypto taker friction, and high
leverage makes it worse, not better.** It is only marginally positive on a
**zero-fee / maker venue at ≤10x**. 25x and 50x are ruin machines.

## The 12 required outputs

1. **Trades analyzed:** 497 with paths (of 498 resolved brackets).
2. **Percent ever green (MFE>0):** **95%** (472/497). Confirmed.
3. **Reached favourable excursion of:** +0.10R **93%**, +0.25R **85%**, +0.50R
   **72%**, +1R **56%**, +2R **35%**, +3R **23%**. (Touches, not fills.)
4. **Best BE trigger by expectancy:** **early and small** — `lock+0.1R@first_green`
   (lock a tiny profit the moment it ticks green) tops every friction column.
   Later triggers (+0.5R/+1R) are *worse* than original — waiting gives the move back.
   BE@+0.25R path-replayed **saved 288 trades** from a deeper loss but **cut 63
   winners** short.
5. **Expectancy before/after fees (best variant):** gross **+0.077R** → low-friction
   **+0.038R** → realistic **−0.219R** → harsh **−0.518R**. The original (no BE) is
   −0.284R gross. So BE adds ~**+0.36R** of gross management edge, but realistic
   friction is ~−0.30R and eats all of it.
6. **By direction:** long gross −0.443R / real −0.760R; **short gross −0.053R / real
   −0.319R**. Short is far less bad (consistent with the §44 regime).
7. **By market (native venue friction):** crypto-major gross −0.253R (real −0.577R),
   crypto-alt −0.323R (real −0.576R), **tradfi/index-metal-oil-fx gross −0.148R
   (zero-fee-net −0.210R, n=41)**. TradFi is the least-bad gross and the only
   low-fee venue, but still negative.
8. **Best leverage after liquidation/friction:** **10x** — only ~1% liquidate, EV
   ≈ flat (−$0.006/trade), risk-of-ruin 0% to 1000 trades. The catch: 10x is "best"
   only because it doesn't *liquidate*; the underlying EV is still ~breakeven-negative.
9. **Min win rate needed (median 0.74% stop, realistic fees):** 1R → **55%** (actual
   touch 56%), 2R → **38%** (actual 35%), 3R → **29%** (actual 23%). The system sits
   at-or-below its own breakeven win rates.
10. **Is 50x viable? NO — fragile/ruinous.** Median worst-adverse move is **1.62%**,
    which *exceeds the 50x liquidation band (1.5%)*, so **55% of trades liquidate**
    regardless of outcome. EV −$0.54/trade; risk-of-ruin **100% by 500 trades**. 25x
    is also bad (12% liquidate, 92% RoR @1000). Only 10x (liq band 9.5%) survives.
11. **Recommended rule candidate (paper only):** `lock+0.1R@first_green` (or
    `@+0.10R`), **≤10x leverage**, on the **zero-fee/maker venue** (TradFi/Yahoo book,
    or maker-only crypto), preferring **short-side** and **wider-stop** setups (tight
    sub-0.5% stops die to friction). Do **not** run this taker-side on crypto, and do
    **not** exceed 10x.
12. **What must be forward-tested next:** (a) can we actually get **maker fills** at
    the break-even/entry (the whole edge depends on ~0% fees — assumption §42); (b)
    real **slippage/spread** on the alt names at micro size; (c) the **short-side**
    skew — is it the §44 flip or genuine; (d) **wider-stop only** variant to dodge the
    friction-amplification; (e) confirm liquidation modelling against a real exchange
    MMR ladder (alts are worse than the flat 0.5% used here).

## Why friction decides it (the mechanism)

Friction is a **price** cost but risk is measured in **R = stop distance**, so
`cost_R = roundtrip% / stop%`. With a median stop of 0.74% and realistic ~0.15%
round-trip, that's **~0.20R of drag every trade** — and on the tightest sub-0.5%
scalps it's 0.3–0.6R. The "95% go green" is true but most of that green is **inside
the friction band**, so it isn't bankable.

## Why high leverage backfires (the mechanism)

Leverage doesn't change the R outcomes — it changes the **liquidation distance**
(≈ 1/L − MMR). The trades' **normal adverse wiggle** (median MAE 1.62%, p90 3.87%)
routinely exceeds the 50x band (1.5%) and often the 25x band (3.5%), so a position
that *would* have come back instead gets **force-closed for the full stake first**.
High leverage converts survivable noise into guaranteed losses.

## Honesty / assumptions

- Intrabar conflicts resolved **adverse-first** → BE/trailing are not over-credited.
- MMR fixed at **0.5%** (real Binance MMR is tier/size dependent; **alts worse**).
- Risk-of-ruin bootstraps observed per-trade $ outcomes (i.i.d.; bankroll 100×stake).
  Real streaks are autocorrelated → treat RoR as an **optimistic floor**.
- "Percent green" / MFE-touch are **touches, not fills**.
- Sample **pools the pre/post VWAP-flip (§44)** regime — descriptive, not causal.
- TradFi n=41 is directional, not conclusive.

*Not financial advice. No live trading changes made.*
