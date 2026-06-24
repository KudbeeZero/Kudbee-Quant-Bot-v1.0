# _DEADLINE_BARS Decision Log

## Current setting
_DEADLINE_BARS = 24 (1h trades resolve within 24h)
Shipped: PR #96, commit 06bf9af

## What it does
Forces any 1h paper trade to close at market
if it has not hit target or stop within 24 bars.
Aligns live paper window with max_bars=24 from
the 137K-trade backtest that validated the edge.

## Known tension — PR #88
PR #88 research found shorter time-exits hurt
expectancy when tested as max_bars candidates.
That was the in-bracket stop, not the live
resolution deadline. Related but distinct.

Today's live result (2026-06-24): six trades
held longer than 24h and closed at +11.55R
combined. Owner chose to shorten anyway to
match the validated backtest condition.

## Watch signal
If forward _cts/core expectancy drops below
the pre-PR-#96 baseline after 50+ trades,
revisit. Do not revert without data.

## Hard negative
Do NOT re-open deadline as a backtest candidate
without at least 30 forward trades under the
new 24h window first.
