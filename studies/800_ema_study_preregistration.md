# 800-EMA Gate Study — Pre-Registration

Date committed: 2026-06-26
Status: PRE-REGISTERED — written before any results viewed. Do not run the
backtest until this commit is on `main`.

## ADAPTATION NOTE (factual; thresholds unchanged)

The originating prompt referenced an "FX pair population" fetched via yfinance.
This repository's validated population is **crypto top-10 on 1h** (BTCUSDT…DOTUSDT
— `kudbee_quant.universe.TOP_10_CRYPTO`), sourced from Binance; there is no FX
population to test, and yfinance is not used by the engine. The **800-period EMA
is already computed by `build_levels` as the `ema_800` column**, so no external
fetch is needed (and the prior DXY/VAH studies ran on this same crypto
population). This study therefore tests the 800-EMA hypothesis on the REAL
validated population. **The gate thresholds and accept/reject logic below are
copied verbatim from the prompt and are NOT changed.**

## Hypothesis

On the validated top-10 / 1h crypto signal population, signals where price is
ABOVE the 800-period EMA on the 1h timeframe at the signal candle deliver
statistically higher net-R/trade than signals where price is BELOW the
800-period EMA.

## Null Hypothesis

800-EMA position relative to price at signal time has no statistically
significant effect on net-R/trade outcome.

## Accept Conditions (ALL must be true)

- n >= 30 signals per bucket (above / below)
- bootstrap p < 0.05
- net-R/trade improvement > 0.02R above baseline
- Baseline: the full validated 1h population mean net-R, same geometry (the
  prompt cites ≈0.096R from the §41 ride-3R reference; the gate uses the
  apples-to-apples same-geometry baseline measured in this run, reported
  alongside the §41 figure).

## Reject Conditions (ANY is sufficient)

- Either bucket n < 30
- bootstrap p >= 0.05
- Improvement <= 0.02R

## Method

1. Build the validated top-10/1h signal population
   (`confluence_position(min_pct=0.50, trend_align)` over
   `cycle_backtest.WINDOWS`) — identical to the DXY/VAH studies.
2. For each signal, read the 800-period EMA at the signal candle from the
   `ema_800` column produced by `build_levels` (no external fetch).
3. Classify: `close[t] > ema_800[t]` → ABOVE bucket; `close[t] < ema_800[t]` →
   BELOW bucket. Signals with NaN `ema_800` (warm-up) are excluded.
4. Enumerate each signal's trade with the live bank-half/BE/ride-3R geometry,
   net of maker fees, via the shared resolver (enumerator fidelity-locked to
   `bracket_backtest` — net-R reproduced exactly).
5. Group net-R by bucket.
6. Significance test: one-sided bootstrap `boot_p = P(mean net-R ≤ 0)` per bucket
   (the project's standard gate, §19/§23), plus the ABOVE−baseline delta.
7. Report per bucket: n, mean net-R, win rate, total R, bootstrap p-value, and
   the delta vs baseline.

## Hard Rules

- Results viewed only after this file is committed and merged to `main`.
- No post-hoc hypothesis adjustment.
- No moving the accept threshold after seeing results.
- If REJECTED: the 800-EMA stays inert. No wiring.
- If ACCEPTED: wire as a READ-ONLY log flag first, not as an execution filter,
  in a SEPARATE PR.

## Source Inspiration

Tino Pistou BTCC trade log 06/22–06/27. Observed the 800-EMA acting as a macro
gate on SOLUSDT. Cross-asset methodology transfer requires independent
validation on our own population — this study is that validation.
