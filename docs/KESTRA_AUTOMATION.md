# Kestra automation (a PLAN — Kestra is not installed here)

> **Honest status:** Kestra is **NOT installed or stood up** in this repo. There is
> no Kestra runtime, no `docker-compose`, no Kestra client dependency. The flow
> YAMLs under `flows/` are a **documented, syntax-validated scaffold** for *if/when*
> a Kestra runtime is introduced. The **proven, actually-running automation is
> GitHub Actions** (`.github/workflows/paper-trade.yml`, hourly + `ci.yml`).

## Why both exist

The hourly GitHub Action already does the proven paper loop and commits the
journal. These Kestra flows mirror that intent in Kestra's model so the
orchestration is portable later. They do **not** replace the GitHub Actions today.

## The flows (`flows/*.yaml`)

| Flow | Schedule | Does | Writes? |
|---|---|---|---|
| `hourly_top100_scan` | `5 * * * *` | top-100 1h scan + journal-check | journal |
| `paper_trade_cycle` | `5 * * * *` | scan → resolve → score | journal |
| `open_trades_review` | every 8h | `review-open-trades --json` | read-only |
| `daily_trade_history` | daily 00:15 | `review-trade-history --json` | read-only |
| `health_check` | every 15m | import + universe load + **assert not live** | read-only |

## Safety by default

- Every flow pins `TRADING_MODE=paper` (and `ENABLE_LIVE_EXECUTION=false` where it
  matters). No flow can enable live execution — enforced by
  `tests/test_kestra_flows.py::test_flow_never_enables_live`.
- **Idempotency / no duplicate orders:** each flow sets `concurrency.limit: 1` so a
  rerun or overlap can't double-process, and the journal already de-dupes one open
  trade per `(symbol, timeframe)`. The review/health flows are read-only, so reruns
  are inherently safe.
- **Retries + failure logging:** each task has a `retry` block; each flow has an
  `errors` listener that logs a clear failure message.

## How to actually run them (future)

1. Stand up a Kestra instance (e.g. `docker run` / `docker-compose` per Kestra
   docs) with Python + this repo available to the worker.
2. Import the `flows/*.yaml` (UI upload or `kestra flow namespace update`).
3. Provide non-secret env (`TRADING_MODE=paper`); never put secrets in the flow.
4. Enable triggers. Validate first with `flows/health_check.yaml`.

## Validation now

`tests/test_kestra_flows.py` parses every flow (valid YAML, required `id` /
`namespace` / `tasks`, each task has `id` + `type`) and asserts none enable live.
That's the only guarantee made today — syntax + safety, not a running pipeline.
