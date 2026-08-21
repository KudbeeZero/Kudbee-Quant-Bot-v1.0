"""Symbol normalization — one canonical form everywhere user input is parsed.

The owner types things like ``btc``, ``Btc``, ``BTC-USD`` into Telegram; the engine
and the data stores key on the Binance spot pair ``BTCUSDT``. Centralizing the
mapping here means every command (and any future caller) agrees on one canonical
symbol, so a loose ``/levels btc`` resolves instead of silently returning "no data".
"""
from __future__ import annotations

from kudbee_quant.universe import TOP_10_CRYPTO

# Bare tickers we accept as shorthand (case-insensitive) -> canonical Binance pair.
_TICKER_MAP = {}
for _sym in TOP_10_CRYPTO:
    # "BTCUSDT" -> "BTC"
    if _sym.endswith("USDT"):
        _TICKER_MAP[_sym[: -len("USDT")]] = _sym
# A few common aliases the owner might type.
_TICKER_MAP.update({
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT",
    "XRP": "XRPUSDT", "ADA": "ADAUSDT", "DOGE": "DOGEUSDT", "DOG": "DOGEUSDT",
    "AVAX": "AVAXUSDT", "LINK": "LINKUSDT", "MATIC": "MATICUSDT", "POL": "MATICUSDT",
    "LTC": "LTCUSDT", "DOT": "DOTUSDT", "TRX": "TRXUSDT", "TON": "TONUSDT",
})


def normalize_symbol(raw: str) -> str | None:
    """Return the canonical ``XXXUSDT`` pair for loose user input, or ``None``.

    Accepts already-canonical pairs (``BTCUSDT``), bare tickers (``btc``), and
    common quote-suffixed forms (``BTC-USD``, ``btc/usdt``). Returns ``None`` for
    anything that doesn't map, so callers can reply "unknown symbol" instead of
    querying the store with a malformed key.
    """
    if not raw:
        return None
    s = raw.strip().upper()
    # Already canonical?
    if s in TOP_10_CRYPTO:
        return s
    # Strip a trailing quote suffix: BTC-USD, BTC/USDT, BTCUSDT, BTC_USDT.
    for sep in ("-", "/", "_"):
        if sep in s:
            s = s.split(sep)[0]
    if s.endswith("USDT"):
        s = s[: -len("USDT")]
    if s.endswith("USD"):
        s = s[: -len("USD")]
    return _TICKER_MAP.get(s)
