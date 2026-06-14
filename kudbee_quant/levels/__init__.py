"""Reference-level construction and range statistics.

Builds the rich set of levels traders watch for confluence — average daily/
weekly/monthly ranges and their projections, period opens, session highs/lows,
the Brinks box, psychological round numbers, and prior-period extremes — so we
can measure (not assume) how price actually reacts around them.

All averages use *prior completed* periods (no lookahead). Session running
highs/lows are shifted one bar so a level is known before the bar that tests
it.
"""

from .builder import build_levels, range_stats, LEVEL_COLUMNS
from .delta import add_taker_delta, DELTA_FEATURE_COLUMNS

__all__ = ["build_levels", "range_stats", "LEVEL_COLUMNS",
           "add_taker_delta", "DELTA_FEATURE_COLUMNS"]
