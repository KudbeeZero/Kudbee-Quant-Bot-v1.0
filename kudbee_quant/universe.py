"""Single source of truth for the trading universe.

The top-10 crypto majors were hardcoded identically in the paper-trade workflow,
overnight_research.py, meta_eval.py and generate_lab_data.py. Import from here so
there is one list to update.
"""
from __future__ import annotations

# Top-10 crypto majors (Binance), the forward/research universe.
TOP_10_CRYPTO = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
]

# Extended universe: TOP_10 + ZCash. PVSRA fit confirmed via backtest (1h
# long-only: E=+0.329R with limit entry, Sharpe 2.43; orderbook-fill limit
# vs market gives +118% ΔE on 1h). Scanned in paper-trade alongside TOP_10.
EXTENDED_CRYPTO = TOP_10_CRYPTO + ["ZECUSDT"]

# Uncorrelated equities/ETFs (Yahoo) for cross-asset validation (ρ≈0.15 vs BTC).
UNCORRELATED_STOCKS = [
    "yahoo:SPY", "yahoo:AAPL", "yahoo:NVDA", "yahoo:MSFT", "yahoo:TSLA", "yahoo:AMZN",
]
