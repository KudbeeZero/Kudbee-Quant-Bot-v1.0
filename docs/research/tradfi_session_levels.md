# TradFi session/RTH handling in `build_levels` — verification findings

Date: 2026-06-10 · Scope: the baton's "verify TradFi `build_levels` session/RTH
handling" (post PR #4). Verified EMPIRICALLY on live Yahoo 1h data (3mo range,
600-bar window — the same fetch the paper bot makes): GC=F, SI=F, CL=F,
EURUSD=X, GBPUSD=X, ^GSPC.

## Verdict: Monday `_tradfi` signals are partly ARTIFACTS; the rest is sound

The NY-date / UTC-date daily groupings assume a 24/7 instrument. CME futures
open Sunday 18:00 ET and FX Sunday ~17:00 ET, so both calendars create a tiny
**Sunday "stub day"** (futures: 6 bars on the NY calendar, 2 bars on the UTC
calendar; FX: 5 and 1). Every daily level derived from "the previous day" is
then computed from that stub on Mondays.

### Confirmed artifacts (real-data, 2026-03→06 window)

1. **Monday floor pivots come from the Sunday stub** — `levels/builder.py:123`
   groups by `ny_date`; Monday's `pivot_pp/r1/s1/r2/s2` derive from the 5-6-bar
   Sunday evening, not Friday's session. Measured error vs Friday-based pivots:
   **0.15–4.0 ATR** (GC=F Mondays: 1.5–2.8 ATR; FX up to 4 ATR). The `v_pivot`
   confluence vote is wrong-leveled every Monday.
2. **Monday PDH/PDL come from a 1-2-bar stub** — `context/mm_cycle.py:95`
   groups by UTC calendar date; the Sunday UTC date holds only the 22:00/23:00
   UTC bars. Monday's `pdh/pdl` ≈ a 1-2-hour range, and `v_sweep` (sweep of
   PDH/PDL) fires against it (EURUSD sweep-vote fire rate: Mon 20.8% vs 11.2%
   rest-of-week).
3. **This flips real trades**: re-scoring with the two stub-fed votes zeroed,
   **40–75% of Monday signals** (≥50% confluence + trend filter) change on/off
   or direction — GC=F 16/40, SI=F 13/39, CL=F 13/26, EURUSD 7/13, GBPUSD 6/8.
   Mondays are ~20% of all signals.
4. **ADR biased low 6–16%** — the Sunday stub range enters the 14-day rolling
   mean (`builder.py:26-31`), tightening `adr_high/adr_low` and overstating
   `pct_adr_used` all week (GC=F −6 to −10%, EURUSD −7 to −16%).
5. **FX: two votes permanently dead** — Yahoo FX 1h has zero volume, so
   session VWAP is NaN (`microstructure.py:23` divides by cumulative volume)
   and PVSRA can never fire a climax. `v_vwap`/`v_vector` are silent 0s →
   max attainable confluence is 8/10, so the 50% gate is effectively stricter
   for FX than for crypto. Calibration skew, not garbage.

### What checks out (no fix needed)

- **Indices (^GSPC/^NDX/^DJI, RTH-only)**: one UTC/NY date per session, no
  stubs — PDH/PDL, pivots, ADR all coherent (ADR = RTH range). `asian_*`,
  `brinks_*` are cleanly NaN → zero votes, no garbage. VWAP/volume fine.
- **`prior_ny_high/low`** skip the stub correctly (no NY-session bars on
  Sunday → Monday maps to Friday's NY session).
- **Weekly open** (first bar on/after Sun 18:00 ET) is exactly the Globex
  weekly open — correct by construction. PWH/PWL weekly grouping unaffected.
- **EMA/ATR/dealing-range** are bar-index rolling — same semantics as crypto
  (index ATR does absorb overnight gaps into stop sizing; noted, accepted).
- **Partial last bar**: Yahoo appends the in-progress bar (misaligned
  timestamp, volume 0); Binance klines do the same, so signaling on
  `iloc[-1]` is cross-venue parity, not a TradFi bug.

## Fix — IMPLEMENTED (same chat, opt-in `trade_dates` flag)

Exchange convention solves artifacts 1-4 in one move: the CME **trade date**
assigns the Sunday-evening session to Monday (Globex day = 18:00 ET → ~17:00
ET next day). `context/calendar.trade_date()` = `(NY wall clock + 6h).date()`
— the day boundary sits at 18:00 ET, the Globex open, and is the identity for
RTH-only instruments. **Not +7h** (a 17:00-ET boundary): tried first, and on
live FX data Yahoo's Friday 17:00 ET close print became a one-bar "Saturday"
trade date, making Monday's PDH−PDL literally zero — a worse artifact than
the one being fixed. Bars in [17:00, 18:00) belong to the closing day.

Threaded as `trade_dates: bool = False` through `build_features` →
`add_mm_context`/`reference_levels` (PDH/PDL) and `build_levels`/`range_stats`
(ny_date → ADR, pivots, session opens, daily_open anchor). OPT-IN only: the
default is bit-identical to the validated crypto path (§1 untouched; full
suite passes unchanged). Wired venue-aware at the three mixed-universe call
sites: `paper/paper.py` (`trade_dates=is_tradfi`),
`validation/bracket_validation.py`, `scenarios/sweep.py` (per-spec
`parse_spec(spec)[0] == "yahoo"`).

Verified on live Yahoo data post-fix (all 6 paper-bot TradFi symbols): no
stub days (futures interior min 17 bars = Friday's real shortened session;
FX 23), Monday PDH−PDL now full-day ranges (GC=F 107.6 vs 23.5; EURUSD
0.0056 vs 0.0007), ^GSPC bit-identical (RTH identity). 7 tests in
`tests/test_tradfi_sessions.py` (synthetic Globex/RTH frames + paper-scan
venue wiring); full suite 179 passed.

Artifact 5 (FX dead vwap/vector votes) is NOT fixed here — it needs either
per-venue `n_factors` or acceptance as a conservative skew; left open.

## Reproduction

Diagnostics live in this doc's history: bars-per-date by day-of-week, ADR
incl/excl stub, pivot stub-vs-Friday error in ATR, and the vote-zeroing signal
delta. All run off `YahooClient.history(sym, '1h', '3mo', limit=600)` +
`build_levels` + `confluence_score`, no mocks.
