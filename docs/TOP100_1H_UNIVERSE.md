# Top-100 crypto universe (1h)

## What it is

A configurable trading universe of ~100 crypto symbols, locked to the **1h**
timeframe, in `config/crypto_universe.yaml`. Loaded + validated by
`kudbee_quant/universe_loader.py`.

> **Honest caveat:** this is a **static fallback snapshot**, not a live top-100
> feed, and the long tail beyond the top-10 majors is **UNPROVEN forward** (MEMORY
> §31). The loader is plumbing; membership is not a claim of edge.

## Config format

```yaml
quote: USDT
default_timeframe: "1h"
default_max_position_usd: 100
symbols:
  - {symbol: BTC, max_position_usd: 250, risk_label: major}
  - {symbol: ZIL, risk_label: mid}
  - {symbol: LUNA, enabled: false, notes: "disabled example"}
```

Per-entry fields (only `symbol` required): `enabled` (default true), `pair`
(default `<symbol><quote>`), `timeframe` (must be `1h`), `max_position_usd`,
`risk_label`, `notes`.

## How it loads (and fails safe)

```python
from kudbee_quant.universe_loader import load_universe, universe_specs
load_universe()                 # enabled-only list of UniverseEntry
load_universe(enabled_only=False)
universe_specs()                # ["BTCUSDT", "ETHUSDT", ...] for paper-scan / RouterClient
```

- `enabled: false` rows are **skipped**.
- Tickers normalize to Binance pairs (`BTC` → `BTCUSDT`), validated against the
  router's strict charset (no SSRF).
- **Fails safe** — a missing file, malformed YAML, an invalid/duplicate symbol, a
  non-1h timeframe, or a non-positive size all raise a clear error rather than
  trading garbage. Covered by `tests/test_universe_loader.py`.

## Running a top-100 1h scan

```bash
python -m kudbee_quant.cli paper-scan \
  $(python -c "from kudbee_quant.universe_loader import universe_specs; print(' '.join(universe_specs()))") \
  --intervals 1h --trend-filter
python -m kudbee_quant.cli journal-check
```

## Enabling it in the hourly automation (a USER decision)

The proven hourly Action (`.github/workflows/paper-trade.yml`) deliberately still
scans the **top-10** book. Switching it to the top-100 universe is **opt-in** and
left to you, because it ~10×'s the per-hour API load and floods the (bot-owned)
journal with unproven-symbol trades. To enable, replace the hardcoded crypto
symbol list in that workflow's `paper-scan` step with the `universe_specs()`
substitution above and keep `--intervals 1h`. (The Kestra flow
`flows/hourly_top100_scan.yaml` already encodes this — see `KESTRA_AUTOMATION.md`.)
No 5m — §37 paused the fee-poisoned 5m book.
