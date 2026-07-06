# Execution head-to-head: maker-retrace vs market vs hybrid (OOS, net of fees)

**Task (2026-06-15, offline):** the live maker retrace fills only ~81% of 1h signals
(median 1.6h late) and *may* be anti-selecting — filling the reversals and skipping
the immediate runners. Test whether entering at the signal with a **market order**
beats it. Decisive metric: **net-of-fees OOS expectancy per timeframe.**

Full machine-readable results: [`data/execution_backtest_results.json`](../data/execution_backtest_results.json).
Reproduce: `PYTHONPATH=. python scripts/execution_backtest.py`. Core logic +
tests: `kudbee_quant/backtest/execution_modes.py`, `tests/test_execution_modes.py`.

> **No live change is recommended.** This is research. The live path
> (`bracket.py`/`resolver.py`) was **not** touched.

---

## Method (what was held constant, what varied)

- **Signal = the real production signal:** `confluence_position(min_pct=0.50,
  trend_align=True)` (`kudbee_quant/confluence/stack.py`) — the 800-EMA HTF filter
  the live paper scan applies via `trend_filter` in `kudbee_quant/paper/paper.py`.
- **Geometry held constant** (validated defaults, MEMORY §1): stop `1.5·ATR` (=1R),
  target `3R`, `max_bars=24`, retrace `0.25·ATR`, `entry_window=6`.
- **Three entry modes** (all no-lookahead; signal decided at bar T's close):
  - **A — maker_retrace (CURRENT live):** limit at `close[T] − dir·0.25·ATR`, fills
    only if price retraces within 6 bars, else the signal is **cancelled**. Maker in.
  - **B — market:** fill at the **OPEN of bar T+1** (you cannot fill at the signal
    price itself). Taker in.
  - **C — hybrid:** limit rests for 1 bar (T+1); if unfilled, cancel and chase with a
    market order at the OPEN of T+2. Maker if filled, taker if chased.
- **Fees — per-leg, measured (MEMORY §25):** taker `0.00045/side`, maker
  `0.0002/side`. **Exits costed by type:** stop / time-stop = taker (market out);
  target = maker (resting limit). (`A_legacycost` below re-costs A round-trip-maker —
  the current backtest's more optimistic assumption — for reference.)
- **Data:** 5m klines (public Binance mirror) per symbol×window + a 50-day warmup
  prefix, **resampled** to 15m and 1h so all timeframes share identical source bars
  and windows. Signals before the window start are warmup-only and excluded.
- **Universe:** the walk-forward-validated majors. Coins not yet listed in an early
  window return no data and are skipped (logged).
- **OOS windows (UTC):** `2018_chop` 2018-05-01…2018-10-01 (5 symbols available),
  `2022_chop` 2022-05-01…2022-10-01 (10), `recent` 2026-01-01…2026-06-01 (10).
- **Significance:** per-trade bootstrap `p = P(mean net R ≤ 0)`, 5000 resamples.

---

## STEP 2 — pooled net-of-fees results (all windows)

| TF | Variant | n | fill | win% | **expectancy** | total R | PF | maxDD | bootstrap p |
|----|---------|---|------|------|----------------|---------|----|-------|-------------|
| **5m** | **A maker_retrace** | 40534 | 85% | 32.8% | **−0.0999R** | −4050 | 0.86 | −4054 | 1.000 |
| 5m | B market | 43807 | 100% | 30.9% | −0.2037R | −8923 | 0.75 | −8929 | 1.000 |
| 5m | C hybrid | 42899 | 100% | 30.9% | −0.1723R | −7393 | 0.78 | −7397 | 1.000 |
| **15m** | **A maker_retrace** | 13234 | 86% | 34.9% | **+0.0014R** | +19 | 1.00 | −254 | 0.451 |
| 15m | B market | 14274 | 100% | 32.1% | −0.0961R | −1372 | 0.87 | −1373 | 1.000 |
| 15m | C hybrid | 13989 | 100% | 32.6% | −0.0718R | −1004 | 0.90 | −1030 | 1.000 |
| **1h** | **A maker_retrace** | 3267 | 86% | 37.2% | **+0.1265R** | +413 | 1.20 | −31 | **0.000** |
| 1h | B market | 3505 | 100% | 35.2% | +0.0545R | +191 | 1.08 | −79 | 0.020 |
| 1h | C hybrid | 3391 | 100% | 35.2% | +0.0646R | +219 | 1.10 | −48 | 0.009 |

**Maker (A) beats market (B) by ~+0.07 to +0.10R per trade on every timeframe**
(5m +0.104R, 15m +0.098R, 1h +0.072R). Hybrid (C) lands between the two — it captures
some maker fills but pays taker on the chases, so it never beats pure maker.

## STEP 2 — does it survive the chop regimes? (per-window expectancy, R)

| TF | variant | 2018_chop | 2022_chop | recent |
|----|---------|-----------|-----------|--------|
| 5m | A / B | −0.030 / −0.120 | −0.051 / −0.142 | −0.180 / −0.302 |
| 15m | A / B | +0.051 / −0.038 | +0.011 / −0.066 | −0.031 / −0.152 |
| 1h | A / B | +0.249 / +0.196 | +0.087 / +0.034 | +0.109 / +0.014 |

**A beats B in all 9 cells.** The maker advantage is regime-robust; it does not flip
in either chop window.

---

## STEP 3 — adverse-selection test (the key one)

Every signal the maker retrace **cancelled** (never filled), re-resolved as a market
entry. Pooled, all windows:

| TF | n cancels | win% | expectancy | total R | p |
|----|-----------|------|------------|---------|---|
| 5m | 6924 | 67.2% | **+1.098R** | +7600 | 0.000 |
| 15m | 2113 | 67.6% | **+1.111R** | +2348 | 0.000 |
| 1h | 539 | 69.9% | **+1.217R** | +656 | 0.000 |

**The cancels are net winners — strongly, in every regime.** Directionally this
**confirms the anti-selection hypothesis**: the ~14-15% of signals the retrace throws
away are disproportionately the *immediate runners* (a long signal is "cancelled"
precisely when price never pulled back 0.25·ATR — i.e. it ran up immediately). The
retrace is structurally filling the pullbacks/reversals and skipping the runners.

### …but this does NOT mean "switch to market entry." Two honest caveats:

1. **You can't isolate the cancels in real time.** The tradeable way to capture them
   is to take *every* signal at market — and that is exactly variant **B**, which is
   **worse** than the maker retrace on every timeframe. Taking the runners at market
   also means taking all the reversals at a worse price plus a taker fee, and the
   reversal cost outweighs the runner capture.
2. **The +1.1R figure is upward-biased by selection conditioning.** "Cancelled" is
   defined by *no 0.25·ATR pullback in 6 bars*, which is correlated with not being
   stopped out early (the stop sits 1.5·ATR away). Conditioning on early
   non-retracement partly pre-selects paths that hold up. So treat +1.1R as a
   *diagnostic that the cancels lean to runners*, **not** as harvestable edge.

The real takeaway: the anti-selection is **real but not captured by blanket market
entry**. Capturing it would need a *smarter* entry that chases only the signals likely
to run (e.g. shorten `entry_window`, or chase only in strong-trend / high-momentum
regimes). That is a **future research item**, not a live change.

---

## STEP 4 — VERDICT (plain language)

**The current execution — the 0.25-ATR maker retrace — wins net-of-fees OOS on every
timeframe.** Market-at-signal is the worst execution everywhere; hybrid is in between.

- **1h:** maker **+0.1265R/trade** (p=0.000) vs market +0.0545R (p=0.020). Maker wins
  by **+0.072R/trade** and survives both chop windows (2018 +0.249, 2022 +0.087,
  recent +0.109). **This is the winning execution; the corrected, honestly-costed
  number is +0.1265R/trade** (or +0.1397R under the legacy round-trip-maker costing).
  Lower than the MEMORY §1 headline (~+0.19-0.24R) because (a) two of three windows are
  chop/bear and (b) the per-leg model now charges *taker* on stops — more conservative.
- **15m:** maker ≈ breakeven (+0.0014R, p=0.45 — **not** significant) but still clearly
  beats market (−0.0961R). 15m is marginal; maker is the least-bad and the only
  non-negative option.
- **5m:** **all three lose.** Market does **not** rescue 5m — it makes it *worse*
  (−0.204R vs maker −0.100R). The §37 "5m is fee-poisoned" verdict stands and is
  reinforced: changing execution does not save 5m. (Hypothesis tested, not assumed.)

**Does market entry win? No — on no timeframe, in no regime.** The premise that the
retrace's 19% miss rate is costing edge is *half right*: those misses ARE the runners
(anti-selection confirmed), but blanket market entry loses more on the reversals than
it gains on the runners. The maker retrace's better fill price is worth more than the
runners it forgoes.

### Recommended config / code change

**None to the live path.** Keep the maker retrace (`limit_retrace_atr=0.25`,
`entry_window=6`, maker in) exactly as is — it is the validated winner here too.

If/when the user wants to chase the *captured* anti-selection edge (NOT yet — needs its
own validation), the candidate is a **selective chase**, not blanket market entry:
e.g. in `bracket_backtest`, after the retrace cancels, optionally market-fill at the
next open **only** when a momentum/trend gate is hot. The harness to test that already
exists (`execution_modes.run_variant` + the adverse-selection seam). **Forward-test
before any live change.**
