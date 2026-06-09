"""Single source of truth for the VALIDATED strategy parameters.

These numbers (docs/MEMORY.md §1) were repeated in 10+ files — api.py, paper.py,
the scripts, ml/labels.py, the harness — which meant a change had to be made in
many places and could silently drift. Import them from here instead.

    from kudbee_quant.config.validated_defaults import VALIDATED_BASELINE, STOP_ATR
"""
from __future__ import annotations

# The validated, walk-forward-tested configuration.
MIN_PCT = 0.50            # confluence threshold (fraction of factors aligned)
TARGET_R = 3.0            # take-profit in R
STOP_ATR = 1.5            # stop distance = STOP_ATR * ATR (= 1R)
RETRACE_ATR = 0.25        # limit entry on a 0.25-ATR maker retrace
MAX_BARS = 24             # time-stop horizon (bars)
ENTRY_WINDOW = 6          # bars allowed for the limit retrace to fill
FEE_PCT = 0.0004          # round-trip MAKER cost assumption (fraction of price).
                          # MEASURED on live BTCC fills (MEMORY §25): TAKER = 0.00045
                          # per side (0.0009 round-trip = 2.25x this). Maker rate not
                          # yet confirmed from a limit fill; use 0.0009 for taker legs.
INTERVAL = "1h"           # core timeframe
TREND_FILTER = True       # HTF 800-EMA trend alignment (tested edge booster, §16)

# Per-VENUE round-trip cost (fraction of price), for NET-of-fee journal scoring
# (MEMORY §26). Crypto perps still pay the MEASURED §25 taker; the zero-fee TradFi
# promo venue pays nothing while it lasts. This is the conservative, honest split:
# crypto net = gross − taker, TradFi net = gross.
TAKER_FEE_PCT = 0.0009    # crypto round-trip TAKER — MEASURED on live BTCC fills (§25)
TRADFI_FEE_PCT = 0.0      # zero-fee TradFi promo venue (§26); a forward-test window,
                          # NOT a permanent assumption — revisit when the promo ends.
VENUE_FEE_PCT = {"crypto": TAKER_FEE_PCT, "tradfi": TRADFI_FEE_PCT}

# Convenience bundles for the two common call shapes.
VALIDATED_BASELINE = {
    "min_pct": MIN_PCT, "target_r": TARGET_R, "stop_atr": STOP_ATR,
    "retrace_atr": RETRACE_ATR, "interval": INTERVAL,
}
BRACKET_KW = {            # kwargs for backtest.bracket.bracket_backtest
    "stop_atr": STOP_ATR, "target_r": TARGET_R, "max_bars": MAX_BARS,
    "limit_retrace_atr": RETRACE_ATR, "entry_window": ENTRY_WINDOW, "fee_pct": FEE_PCT,
}
