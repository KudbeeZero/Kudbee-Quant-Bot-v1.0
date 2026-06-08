"""Market-maker cycle context — Traders Reality regime layer.

PVSRA tells you *where* volume showed up. This module tells you *where price
is in the market-maker cycle* when it shows up — which is what separates a
climax that matters from noise. It computes the structural context Tino's
methodology leans on:

  - sessions:  Asian / London / New York windows (UTC) + the Asian-range box
  - levels:    previous day & week highs/lows (PDH/PDL/PWH/PWL) as liquidity
  - sweeps:    stop-hunt detection (price takes a level then rejects)
  - cycle:     day-of-week phase of the weekly MM template

HONEST CAVEAT: session windows are fixed UTC approximations; real session
opens shift with DST. The weekly "cycle phase" is a heuristic label, not a
law. Everything here is context to be *validated*, never obeyed.
"""

from .mm_cycle import (
    SessionWindows,
    add_mm_context,
    detect_sweeps,
    label_sessions,
    reference_levels,
    weekly_cycle_phase,
)

__all__ = [
    "SessionWindows",
    "add_mm_context",
    "detect_sweeps",
    "label_sessions",
    "reference_levels",
    "weekly_cycle_phase",
]
