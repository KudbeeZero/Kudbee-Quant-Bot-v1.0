"""Session risk sizer — scale per-trade risk by the active UTC trading session.

Liquidity (and, historically for this book, edge) clusters in the London/NY hours; the
dead Asian session gets a haircut. Multipliers (UTC; the overlap wins):

  London+NY overlap (13-16) -> 1.50
  NY      (16-21)           -> 1.25
  London  (07-13)           -> 1.25
  Asia    (23-07)           -> 0.75
  other   (21-23)           -> 1.00

Boundaries align with ``context.mm_cycle.SessionWindows`` (london 7-16, ny 13-21,
asian 23-7); the 13-16 intersection is the overlap and takes precedence.

``sized_risk`` clamps the result to ``max_risk`` so a multiplier can never push risk
past the per-trade ceiling. Unparseable timestamps fall back to the neutral 1.0x.
"""
from __future__ import annotations

import pandas as pd

OVERLAP_MULT = 1.5      # London + NY overlap
NY_MULT = 1.25
LONDON_MULT = 1.25
ASIA_MULT = 0.75
OTHER_MULT = 1.0


def session_risk_multiplier(timestamp_utc) -> float:
    """Risk multiplier for the session containing ``timestamp_utc`` (UTC)."""
    if timestamp_utc is None:
        return OTHER_MULT
    try:
        h = int(pd.to_datetime(timestamp_utc, utc=True).hour)
    except (ValueError, TypeError, AttributeError):
        return OTHER_MULT
    if 13 <= h < 16:
        return OVERLAP_MULT
    if 16 <= h < 21:
        return NY_MULT
    if 7 <= h < 13:
        return LONDON_MULT
    if h >= 23 or h < 7:
        return ASIA_MULT
    return OTHER_MULT


def sized_risk(base_risk: float, timestamp_utc, max_risk: float = 0.02) -> float:
    """``base_risk`` scaled by the session multiplier, clamped to ``max_risk``."""
    risk = float(base_risk) * session_risk_multiplier(timestamp_utc)
    return min(risk, float(max_risk))
