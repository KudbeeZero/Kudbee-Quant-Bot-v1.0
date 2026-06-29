"""Signal generators. Each signal is a measurable hypothesis, never a promise."""

from .pvsra import VectorCandleConfig, pvsra_vector_candles

__all__ = ["VectorCandleConfig", "pvsra_vector_candles"]
from .dxy_regime import dxy_regime, compute_dxy, RISK_ON, RISK_OFF, NEUTRAL  # noqa: E402,F401
