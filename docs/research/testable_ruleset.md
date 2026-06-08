# Testable Rule Set — turning Traders Reality teachings into measurable edges

This is the bridge from the research (`tino_traders_reality.md`) to code. It
converts each *belief* into a **mechanically-defined event** with **context
features** and a **measured forward outcome**. The model "gets smarter" not by
believing harder, but by accumulating **conditional base rates** from history
and reporting them honestly — including when an edge is absent.

> Architecture: a **Conditional Event-Study Engine**. For each event type we
> compute P(outcome | context) over real data, with confidence intervals and
> an out-of-sample / multi-asset check (reusing our existing validation
> harness). No claim is trusted until it survives that bar.

Every event is timestamped in **UTC** but classified by **New York local
time** with DST handled, and tagged with a **holiday flag**.

---

## Shared context features (attached to every event)

- `session` ∈ {asian, london, ny, london_ny_overlap, off}
- `killzone` ∈ {asian, london_open, ny_forex, ny_indices, london_close, none}
- `minutes_into_session` (e.g. "3 hours into NY" = 180)
- `day_of_week` (Mon–Sun) and `week_phase` (Mon range / Tue–Thu expansion / …)
- `is_holiday`, `is_thin_liquidity` (late-Dec, pre-holiday half-days)
- `dist_to_daily_open`, `dist_to_weekly_open` (in ATR units)
- `nth_test_of_level` (1st, 2nd, 3rd touch — the user's "second test")
- `pvsra_tier` (climax / above-avg / normal) and `vector_color`
- forward outcome windows: return over next k bars; MFE/MAE; did level X get hit

---

## A. Vector-candle recovery (honoring "it always gets recovered")

**Event:** a vector (climax) candle forms (`pvsra.py` already flags these).
**Zone:** the candle's `[low, high]` box; midpoint = 50% level.
**Outcome to measure (NOT assume):**
1. `recovered_within(N)` — does price re-enter the box within N bars? Build the
   **survival/recovery curve**: fraction recovered at N = 1,5,15,60,240,1440…
   bars, **per timeframe**. This turns "always, eventually" into a real number
   like "62% within 24h on 1h BTC."
2. `reversal_at_partial` — when price penetrates 50–100% of the zone, measure
   forward return vs. a null (random equidistant level). Tests the "50–100%
   reversal" claim.
3. `magnet_test` — is an unrecovered zone reached more often than a random
   level the same distance away? (Edge only exists if yes.)

**Honesty rule:** report the recovery curve and the *base rate of any level
being revisited anyway*. If random levels get "recovered" almost as often, the
vector adds no edge — say so.

---

## B. Daily/weekly open + the "second test" (the user's Tuesday/NY example)

**Levels:** Midnight Open (00:00 ET), prior-day open, Weekly Open (Sun 18:00
ET). (We already compute PDH/PDL/PWH/PWL; add the opens.)
**Event:** price **tests** a level (touch within ε·ATR). Track `nth_test`.
**The exact study the user asked for** — "price tests the daily open for the
second time on a Tuesday, 3 hours into the NY session: up or down, and why?":

```
event   = test of daily_open
filter  = nth_test == 2  AND  day_of_week == Tue  AND  session == ny
          AND 150 <= minutes_into_session <= 210
measure = sign and size of forward return over next {15,30,60,120} min
          + which level got hit first (open reclaim vs. continuation)
```

**Benchmark:** edgeful's measured midnight-open retest base rates (ES ~58–69%,
NQ 73% on Tuesdays, BTC ~64–65%, **Gold ~50/50 → no edge**) are the yardstick.
We reproduce these on our own data before trusting any finer slice.

**Honesty rule:** conditioning on (2nd test × Tuesday × NY × 3h-in) slices the
data thin — guard against **multiple-comparisons / overfitting**: require a
minimum sample size, report the CI, and validate out-of-sample. A 73% that
rests on 30 Tuesdays is not 73%.

---

## C. Liquidity sweeps & day-of-week structure

**Sweep event** (already in `context/mm_cycle.py`): price pierces PDH/PDL/
PWH/PWL/Asian-range then closes back through. **Measure** forward return after
a sweep, conditioned on session/killzone.
**Weekly-extreme study:** does the weekly high/low actually form Tue/Wed more
than chance? **Measure** the day-of-week distribution of weekly extremes per
instrument. (Testable; sources never proved it.)
**Asian-range-sweep:** does London sweeping the Asian range precede a
directional move? Measure.

---

## D. Premium-window focus (where we actually trade)

Per the user's directive — **few, high-probability trades in peak-liquidity
windows.** Restrict live signals to the **London–NY overlap (08:00–11:00 ET)**
and the **London open killzone (02:00–05:00 ET)**, *only if* the event-study
base rates in those windows beat the all-hours base rate with statistical
significance. Size by **fractional Kelly off the measured conditional edge**
(already in `backtest/sizing.py`), capped, with the holiday filter forcing
flat.

---

## E. What "learning from the past" means here (no black box)

The engine maintains a table: `(event_type, context_bucket) -> {n, win_rate,
mean_fwd_return, CI, oos_win_rate}`. As more history accrues, estimates
tighten. "Smarter and smarter" = **more data → narrower confidence intervals
and pruning of buckets that don't beat the null** — not a model that grows
more confident on the same evidence. Every bucket carries its sample size and
out-of-sample number so we never mistake noise for a clue.

---

## Build order

1. **Add open levels** (midnight ET, weekly Sun-18:00-ET) to `context`.
2. **Event-study engine** `kudbee_quant/events/`: event detectors + the
   conditional base-rate table with CIs.
3. **Recovery-curve study (A)** — the flagship "does it get recovered" answer.
4. **Daily-open second-test study (B)** — the user's exact question, with
   multiple-comparisons guards.
5. Wire significant, OOS-surviving buckets into a strategy; validate with the
   existing correlation-adjusted multi-asset harness before any capital.

**Stay humble:** the prior from everything we've measured so far is that most
of these buckets will *not* beat the null. That's the expected, healthy
outcome. The win is finding the few that do — and knowing the difference.

---

## First measured results (BTCUSDT, 1h, 4000 bars)

The engine is built and the two flagship studies have run. Both returned the
honest verdict, not the hoped-for one.

### Vector-candle recovery — the magnet thesis fails the null

First pass used a loose definition (price re-enters the candle box) and showed
**100% recovery within 1 bar** — but that is an **artifact**: adjacent crypto
candles overlap, so the next bar is trivially "in the box." Price continuity,
not a magnet.

Corrected to the meaningful definition (price must **leave** the zone, then
**return**), with a random equal-width zone as the null:

| horizon (bars) | vector recovered | random-zone null | edge |
|---|---|---|---|
| 5 | 13.9% | 23.2% | **-9.3%** |
| 15 | 46.3% | 51.4% | -5.1% |
| 60 | 77.5% | 75.1% | +2.4% |
| 240 | 87.6% | 87.4% | +0.2% |
| 1440 | 92.1% | 93.1% | -0.9% |

**Vectors are NOT special magnets.** Price returns to a vector zone at almost
exactly the rate it returns to any random nearby zone (~92% vs ~93% over 60
days). "Always gets recovered" is true only in the trivial sense that price
wanders back to most nearby levels eventually — the vector adds **no edge over
a coin-flip level**, and is actually *slower* to recover at short horizons.

### Daily-open "second test" — the Tuesday/NY question

The exact bucket requested (2nd test of daily open, Tuesday, NY session):
**n = 6, win rate 50%, 95% CI [19%, 81%] → noise.** Across all buckets,
**none** reached the minimum sample, none survived Benjamini–Hochberg FDR, and
win rates swung 14%–78% purely from small-sample variance. Cherry-picking
"Monday London 2nd test = 77.8%!" (n = 9) would be self-deception.

Honest answer: **with 4000 hours we cannot answer this — far too few events.**
Resolving it needs years of data (and likely a more liquid, less 24/7
instrument). This is the engine working: it refuses to manufacture an edge
from noise.
