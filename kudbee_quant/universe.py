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

# Broader liquid-major candidate pool for the OPT-IN dynamic volume universe
# (kudbee_quant.universe_rank). The static TOP_10 above is the validated/forward
# universe; this pool is only the set we RANK BY VOLUME when explicitly asked —
# nothing here changes the validated book. Unavailable tickers are skipped at
# rank time (the ranker fetches each and drops any that error).
#
# Expanded 2026-06-22 to ~40 liquid USDT pairs so the volume-ranker can answer the
# owner's "scan the top 30-40 most-liquid pairs" question. Whether trading that
# wider universe actually ADDS edge (vs. bleeding like the §48 top-100 tail) is a
# backtest question, answered by scripts/validate_volume_universe.py — this pool is
# only the candidate set, still OFF the validated forward book.
CRYPTO_CANDIDATES = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
    "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT", "BCHUSDT", "TRXUSDT", "NEARUSDT",
    "ATOMUSDT", "UNIUSDT", "FILUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT",
    "SUIUSDT", "TIAUSDT", "LDOUSDT", "ETCUSDT", "XLMUSDT", "HBARUSDT", "ICPUSDT",
    "VETUSDT", "ALGOUSDT", "AAVEUSDT", "MKRUSDT", "RUNEUSDT", "SANDUSDT", "MANAUSDT",
    "AXSUSDT", "EGLDUSDT", "GRTUSDT", "FLOWUSDT", "SEIUSDT", "PEPEUSDT", "SHIBUSDT",
]
