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

# Uncorrelated equities/ETFs (Yahoo) for cross-asset validation (ρ≈0.15 vs BTC).
UNCORRELATED_STOCKS = [
    "yahoo:SPY", "yahoo:AAPL", "yahoo:NVDA", "yahoo:MSFT", "yahoo:TSLA", "yahoo:AMZN",
]
