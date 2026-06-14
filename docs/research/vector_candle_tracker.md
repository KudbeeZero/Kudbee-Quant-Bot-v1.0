# Vector-candle tracker — logger + study (phase 1)

**Goal (user, 2026-06-14):** when an actual PVSRA *vector candle* (volume climax)
forms — often starting on a low timeframe — pick it up, check other timeframes for
agreement, and **log where on the chart it formed**, because we may be missing
entries/exits "because of time" (the hourly scan is too slow for fast setups).

This phase ships the **logging + study** half (research-first, no live infra). The
real-time pickup is a follow-on (see "Cadence" below).

## What's here

- **`kudbee_quant/signals/vector_log.py`** — detects PVSRA climax candles (reuses
  `signals/pvsra.py`), tags each with the **chart location** it formed at (nearest
  structural level — daily open / VWAP / pivots / dealing-mid / EMAs — within 0.5
  ATR, else `open_space`) and the **multi-factor confluence snapshot** at that bar
  (`confluence_pct`, direction, and whether the climax *agrees* with confluence).
  `scan_and_log()` appends new events to `data/vector_log.json` (deduped by
  symbol+TF+timestamp) — a NEW research artifact, not the bot journal.
- **`kudbee_quant/signals/vector_study.py`** — for each climax candle, simulates the
  system's own trade (enter at the close in the climax direction, `stop_atr` stop,
  `target_r` bracket) via the **shared `backtest/resolver.resolve_bracket`**, NET of
  the measured taker fee in R, bucketed by location / agreement / climax-type×TF.
- **CLI:** `vector-scan SYMBOLS [--intervals ...]` (log now) and
  `vector-study SYMBOLS [--intervals ...]` (historical analysis).
- Hermetic tests in `tests/test_vector_log.py` (synthetic climax bar, no network).

## Initial finding (5 majors × 5m+1h, ~1,316 climax candles, taker-at-close)

NET of fees, simulated as a 3R bracket from the climax close:

- **Location is the whole story.** Climax candles at **support pivots** are the only
  clearly net-positive bucket — `pivot_s1` n=53, **+0.21R net** (`pivot_s2` +0.08R);
  the **800-EMA** is ~breakeven (+0.01R). Climax candles in **`open_space`** (n=630,
  the biggest bucket) are the worst bleeders (**−0.54R net**). So a vector candle
  *at a level* is a different animal from one *mid-air* — directly answering "at what
  points in the chart these candles matter."
- **Agreement helps:** climax agreeing with confluence is much better than fighting it
  (gross +0.008 vs −0.183).
- **§37 re-confirmed:** 5m climax trades are gross-sometimes-positive but **net deeply
  negative** (bull_climax 5m: gross +0.14 → **net −0.55**, a ~0.7R fee bite). The fee
  is the killer on low TF — the cost side of the "because of time" problem.

### Honest caveats
- This uses a **market-at-close (taker)** entry — the conservative/pessimistic read.
  The live system enters on a **maker limit-retrace** (cheaper, MEMORY §25), which
  would lift several buckets; a maker-entry variant is the obvious next measurement.
- The positive buckets have **small n** (pivot_s1 = 53). Treat as a hypothesis, not an
  edge — and per the `pvsra.py` caveat, a vector candle is "where volume showed up,"
  not proof of direction. §37 still says don't *trade* 1m/5m on fees.

## Cadence — the "because of time" half (follow-on)

Detection is solved; the gap is seeing a low-TF climax in time. Three options:
1. **TradingView alert → existing `/api/alert` inbox (§34)** — lowest effort, truly
   real-time; needs the Render host live (still unprovisioned).
2. **Polling vector-watcher** — a worker that pulls 1m bars every minute, detects fresh
   climaxes, logs + escalates to multi-TF confluence. Robust; needs a persistent host.
3. **`vector-scan` on a tighter Action** — cheapest, but Actions cron is coarse/delayed;
   good for prototyping the log, not real-time.

Recommended path: keep logging + the study accumulating (phase 1), measure the
maker-entry variant and how much edge the hourly delay actually costs, **then** wire
option 1 once the host exists.

## Usage

```bash
python -m kudbee_quant.cli vector-scan BTCUSDT ETHUSDT SOLUSDT --intervals 5m 15m 1h
python -m kudbee_quant.cli vector-study BTCUSDT ETHUSDT SOLUSDT --intervals 5m 1h
```
