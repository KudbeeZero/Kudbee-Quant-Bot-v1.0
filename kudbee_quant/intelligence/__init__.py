"""TR Level Intelligence — persistence layer for build_levels() output.

A NON-CRITICAL side-channel: after each paper-scan it records the full TR level
grid (one row per date+symbol+timeframe) and tracks unrecovered PVSRA climax
candles as price magnets, all in a Cloudflare D1 database. It NEVER touches the
trading logic, the backtest harness, or live signals — every write is wrapped in
try/except at the call site so a D1 failure can never block a scan or an alert.

Modules:
  d1_client       — thin Cloudflare D1 REST client (read/write).
  level_recorder  — persists the last bar's TR levels to `daily_levels`.
  vector_tracker  — upserts climax candles + tracks recovery in `unrecovered_vectors`.
"""
