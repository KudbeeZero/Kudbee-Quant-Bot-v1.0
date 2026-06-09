"""Per-venue fee model for scoring the journal NET of costs (MEMORY §26).

The journal records outcomes in R (risk multiples), GROSS of fees. The validated
strategy's edge is cost-sensitive (§1/§25): near the cost line, fees ARE the
difference between + and -. The §26 zero-fee TradFi promo makes those venues free,
so to SEE that advantage we must score crypto and TradFi each net of their own fee.

Venue is read authoritatively from the symbol SPEC (the same routing signal the
paper loop uses): a ``yahoo:`` spec is TradFi (0-fee promo); anything else routes
to Binance crypto (still pays). This works for bot AND human trades regardless of
the ``setup`` label's cosmetic ``_tradfi`` suffix.
"""
from __future__ import annotations

from ..config.validated_defaults import CRYPTO_FEE_ROUNDTRIP, TRADFI_FEE_ROUNDTRIP
from ..ingest.router import parse_spec


def round_trip_fee_pct(symbol: str) -> float:
    """Round-trip fee fraction for a symbol's VENUE.

    TradFi (``yahoo:``) rides the §26 0-fee promo → 0. Crypto (Binance, the
    default) pays the assumed maker round-trip (config constant).
    """
    source, _ = parse_spec(symbol)
    return TRADFI_FEE_ROUNDTRIP if source != "binance" else CRYPTO_FEE_ROUNDTRIP


def fee_in_r(symbol: str, entry: float | None, stop: float | None) -> float:
    """Convert a venue's round-trip fee into R (risk multiples) for a bracket.

    R is risk-normalised: 1R = the entry→stop distance ``|entry - stop|``. A fee
    of ``f`` (fraction of notional, charged ~entry price per side, round-trip)
    therefore costs ``f * entry / |entry - stop|`` in R. Returns 0.0 when the
    risk width is unknown (non-bracket predictions) — we can't charge what we
    can't size, so such trades are scored net == gross.
    """
    if entry is None or stop is None:
        return 0.0
    risk = abs(entry - stop)
    if risk <= 0:
        return 0.0
    return round_trip_fee_pct(symbol) * abs(entry) / risk
