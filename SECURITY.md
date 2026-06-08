# Security

Kudbee Quant ingests untrusted data from public APIs and is intended to one
day place real orders. Security is treated as a first-class concern, not an
afterthought. This document describes the threat model and the controls in
place.

## Threat model

| Asset | Threat | Control |
|---|---|---|
| Outbound HTTP requests | SSRF / URL & query injection via a hostile symbol or source spec | Source **whitelist** + strict symbol **regex** (`ingest/router.py`) |
| Local filesystem (cache) | Path traversal / write outside cache root via crafted cache key | Keys **SHA-256 hashed** to filenames + resolved-path **containment check** (`ingest/cache.py`) |
| Backtest integrity | Malformed/hostile market data silently corrupting results | **Schema + bounds validation** at the ingestion boundary (`ingest/validation.py`) |
| Broker / API credentials (future live trading) | Secret leakage via logs, commits, or repr | Env-only loader + **`SecretStr`** that never reveals its value except on explicit `.reveal()` (`config/secrets.py`); secrets git-ignored |
| Network | Hanging requests, oversized responses | Timeouts on every request; bounded retries with backoff |
| Self-deception (statistical) | Overfitting / multiple-comparisons producing false "edges" | Wilson CIs, minimum-sample gates, **Benjamini–Hochberg FDR**, null-model comparison, out-of-sample validation (`events/study.py`, `validation/`) |

## Controls in detail

- **Input validation (`ingest/validation.py`).** Every OHLCV frame is checked
  before use: required columns, tz-aware UTC timestamps that are unique and
  sorted, finite prices > 0, volume ≥ 0, and `high ≥ max(open,close)`,
  `low ≤ min(open,close)`. Bad rows are dropped or rejected; empty results
  raise rather than producing silent garbage.

- **Symbol / source whitelisting (`ingest/router.py`).** Only `binance` and
  `yahoo` sources are accepted. Symbols must match `^[A-Za-z0-9._=^-]{1,20}$`,
  so a value like `../../evil` or `BTC&endpoint=...` cannot be interpolated
  into a request URL.

- **Cache path safety (`ingest/cache.py`).** Cache keys are hashed to fixed
  hex filenames; the resolved data/meta paths are verified to live inside the
  cache root. No attacker-controlled key can escape the directory.

- **Secrets (`config/secrets.py`).** No secret is ever hardcoded or committed.
  `get_secret` reads only from the environment and wraps values in
  `SecretStr`, whose `repr`/`str` render `***`. `.env`, `*.key`, `*.pem`, and
  `secrets.json` are git-ignored. Live trading must use least-privilege,
  read-only-where-possible API keys.

## Reporting

This is a private research project. If you find a security issue, do not open
a public issue with exploit details — contact the maintainer directly.

## Dependency integrity

Dependencies are listed in `requirements.txt`. For a hardened install, pin and
verify hashes:

```bash
pip install --require-hashes -r requirements.lock   # generate with pip-compile --generate-hashes
```
