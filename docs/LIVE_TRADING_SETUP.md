# Live trading setup — paper by default, live gated + MAKER-only

> **Status (be honest):** the live order path now **exists** — `LiveExecutor`
> places real `LIMIT_MAKER` orders behind the double gate — but it has **never
> placed a real order in production** and is unproven live. It is fully unit-tested
> against a fake exchange (no network). The hourly Action still runs the proven
> top-10 **paper** book; wiring live into automation is a separate opt-in decision.
> Default behaviour is unchanged: nothing trades real money without two explicit
> opt-in flags **and** real API keys.

## The two modes

| Mode | Default? | What happens |
|---|---|---|
| **paper** | ✅ yes | Signals become journal trades (`mode="paper"`), resolved against OHLCV. The proven, default path. |
| **live** | no | Double-gated. When fully enabled, `LiveExecutor.submit()` rests a **maker-only limit** at the signal's `entry` and journals it as a live, pending limit with its `exchange_order_id`. Fills are polled from the venue. |

## Required environment variables

Non-secret knobs are read by `kudbee_quant/config/runtime.py`; credentials are read
**only** inside `kudbee_quant/execution/exchange.py` (`BinanceBrokerClient`).

| Var | Default | Meaning |
|---|---|---|
| `TRADING_MODE` | `paper` | `paper` or `live`. |
| `ENABLE_LIVE_EXECUTION` | `false` | Second opt-in. Live needs **both** this `true` **and** `TRADING_MODE=live`. |
| `MAX_CONCURRENT_POSITIONS` | `10` | Cap on simultaneously open trades (enforced by both executors). |
| `MAX_POSITION_SIZE_USD` | `100` | Per-trade USD notional ceiling. The live order is sized `min(requested, this)`. |
| `MAX_DAILY_LOSS_USD` | `250` | Daily realized-loss kill-switch. Checked before every live submit. |
| `EXCHANGE_NAME` | `binance` | Target venue label. |

**Secrets (live only):**

| Var | Meaning |
|---|---|
| `BINANCE_API_KEY` | Exchange API key. **Never committed**; read from env only, never logged. |
| `BINANCE_API_SECRET` | Exchange API secret. Same handling. |
| `BINANCE_TESTNET` | `true` → use the Binance spot **testnet** (`testnet.binance.vision`) — the safe way to smoke-test the real signed path. |

Construction is lazy: a missing key only fails when an authenticated call actually
runs (`OrderError`), so the gated executor can be built before keys are wired. A
submit with no keys is rejected cleanly — it never reaches the network and never
journals a trade.

## How live is gated (the safety contract)

```
require_live_enabled()  ->  passes ONLY if  TRADING_MODE=live AND ENABLE_LIVE_EXECUTION=true
```

- `build_executor()` returns a `PaperExecutor` unless **both** flags are set.
- A `LiveExecutor` cannot even be *constructed* without both flags (`LiveExecutionBlocked`).
- `submit()` re-checks the gate, then runs the kill-switch and sizing **before** any order.
- Tests lock this in: `tests/test_execution.py` + `tests/test_live_execution.py`.

## What a live submit does (in order)

1. **Re-check the gate** (`require_live_enabled`).
2. **Kill-switch** — sum today's (UTC) *realized live* loss; if it has reached
   `MAX_DAILY_LOSS_USD`, refuse all new orders (`kudbee_quant/execution/killswitch.py`).
3. **Concurrency cap** — refuse if `MAX_CONCURRENT_POSITIONS` live trades are open.
4. **Sizing** — notional `= min(prediction.position_size_usd, MAX_POSITION_SIZE_USD)`;
   `qty = notional / entry`.
5. **Rest a MAKER-only limit** at `entry` (Binance `LIMIT_MAKER`). The venue
   **rejects** it rather than filling as a taker if it would cross — this enforces
   MEMORY §25: the edge is the limit-retrace *maker* fill; taker turns it negative.
   There is intentionally **no** market-order path.
6. **Journal** it as `mode="live"`, `status="pending"`, `pending_limit=True`, with
   the `exchange_order_id`.

### Fills come from the venue, not from bars

`LiveExecutor.poll(prediction)` asks the exchange for the order's real status and
stamps `filled_at` from the **exchange clock** when filled (never a candle time —
see the journal's §29 fictitious-fill caveat). `cancel(prediction)` pulls a resting
limit; `reconcile()` sweeps all live open/pending trades. Stop/target *resolution*
still flows through the journal's shared OHLCV resolver, so a live trade and a
backtest never disagree.

## Risk controls

- `MAX_DAILY_LOSS_USD` kill-switch (realized live loss, UTC day).
- `MAX_POSITION_SIZE_USD` per-trade notional cap; `MAX_CONCURRENT_POSITIONS` book cap.
- Maker-only execution (no accidental taker fills).
- `§1` validated defaults and `FEE_PCT` are unchanged by this work.

## Smoke-testing the real path safely

Set `BINANCE_TESTNET=true` with testnet keys and both gate flags, then build the
executor and submit a bracket — it will rest a real `LIMIT_MAKER` on the testnet and
journal a live record you can `poll()`/`cancel()`. No mainnet funds are at risk.

## What's proven vs unproven

- **Proven:** the paper pipeline (signal → journal → resolver → score); the 6-asset
  walk-forward (2 crypto + gold/S&P/bonds/oil, correlation 0.00 — MEMORY §1; the
  top-10 book is the *forward paper* universe, not the validation sample); the live
  order subsystem's *logic* (gate,
  kill-switch, sizing, maker order shaping, venue-clock fills) under hermetic tests.
- **Unproven:** any **real** live fill (never run in production); the top-100 long
  tail forward (§31). Treat both accordingly — start on testnet, tiny size.
