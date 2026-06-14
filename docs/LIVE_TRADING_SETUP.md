# Live trading setup — paper by default, live gated (and not functional yet)

> **Status (be honest):** This repo is **paper/research**. There is **no working
> live-order path yet** — `LiveExecutor` is a deliberate *stub*. What this document
> describes is the SAFETY SCAFFOLDING and how live execution *will* be enabled once
> the authenticated exchange client ships in a follow-up PR. Nothing here can place
> a real order today.

## The two modes

| Mode | Default? | What happens |
|---|---|---|
| **paper** | ✅ yes | Signals become journal trades (`mode="paper"`), resolved against OHLCV. The proven, only-functional path. |
| **live** | no | Double-gated. Even when fully enabled, `LiveExecutor.submit()` raises `NotImplementedError` — real fills are a future PR. |

## Required environment variables

All optional; safe defaults shown. Read by `kudbee_quant/config/runtime.py`.

| Var | Default | Meaning |
|---|---|---|
| `TRADING_MODE` | `paper` | `paper` or `live`. |
| `ENABLE_LIVE_EXECUTION` | `false` | Second opt-in. Live needs **both** this `true` **and** `TRADING_MODE=live`. |
| `MAX_CONCURRENT_POSITIONS` | `10` | Cap on simultaneously open trades (enforced by `PaperExecutor`). |
| `MAX_POSITION_SIZE_USD` | `100` | Per-trade USD size ceiling (used to record `position_size_usd`). |
| `MAX_DAILY_LOSS_USD` | `250` | Daily loss kill-switch budget (enforced by the future live path). |
| `EXCHANGE_NAME` | `binance` | Target venue label. |

**Secrets:** exchange API keys are **never** read here and **never** committed.
They will be read only inside the future live executor, only from env
(e.g. `EXCHANGE_API_KEY` / `EXCHANGE_API_SECRET`), and never logged. Do not put any
key, secret, or webhook token in code or YAML.

## How live is gated (the safety contract)

```
require_live_enabled()  ->  passes ONLY if  TRADING_MODE=live AND ENABLE_LIVE_EXECUTION=true
```

- `build_executor()` returns a `PaperExecutor` unless **both** flags are set.
- A `LiveExecutor` cannot even be *constructed* without both flags (`LiveExecutionBlocked`).
- Even constructed, `submit()` refuses (`NotImplementedError`) — no order client exists.
- Tests lock this in: `tests/test_execution.py` (live blocked by default, blocked
  with one flag, stub refuses when "enabled").

## Risk controls

- `MAX_CONCURRENT_POSITIONS` bounds the open book (matters for a 100-symbol scan).
- The two-sided per-symbol risk guard (`kudbee_quant/exposure.py`, default 2%/coin)
  still applies to the paper scan.
- `§1` validated defaults and `FEE_PCT` are unchanged by this foundation.

## What's proven vs unproven

- **Proven:** the paper pipeline (signal → journal → resolver → score), top-10
  majors walk-forward (MEMORY §1).
- **Unproven:** the top-100 long tail forward (§31), and live execution (does not
  exist yet). Treat both accordingly.
