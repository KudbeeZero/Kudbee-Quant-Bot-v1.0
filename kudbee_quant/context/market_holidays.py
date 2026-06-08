"""Market holiday / thin-liquidity flags (lightweight, no dependency).

On bank/public holidays liquidity thins, spreads widen, and momentum methods
break down — so events on these days should be flagged and usually excluded.
We keep a small curated set of major US/UK market closures plus a
late-December thin-liquidity window. This is intentionally not exhaustive;
it covers the days that most distort intraday studies. Extend as needed.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

# Fixed-date major closures (month, day) observed across US/UK markets.
_FIXED = {(1, 1), (12, 25), (12, 26)}  # New Year, Christmas, Boxing Day

# Notable floating US market holidays, enumerated for recent/near years to
# avoid an Easter/observance computation dependency. Extend over time.
_FLOATING = {
    # Thanksgiving (US, 4th Thu Nov) + Good Friday (US markets closed)
    dt.date(2023, 11, 23), dt.date(2024, 11, 28), dt.date(2025, 11, 27), dt.date(2026, 11, 26),
    dt.date(2023, 4, 7), dt.date(2024, 3, 29), dt.date(2025, 4, 18), dt.date(2026, 4, 3),
    # US July 4th observed
    dt.date(2023, 7, 4), dt.date(2024, 7, 4), dt.date(2025, 7, 4), dt.date(2026, 7, 4),
}


def is_holiday(date: dt.date) -> bool:
    return (date.month, date.day) in _FIXED or date in _FLOATING


def is_thin_liquidity(date: dt.date) -> bool:
    """Holidays plus the late-December low-liquidity stretch (Dec 24-31)."""
    return is_holiday(date) or (date.month == 12 and date.day >= 24)


def add_holiday_flags(df: pd.DataFrame, date_col: str = "ny_date") -> pd.DataFrame:
    """Add is_holiday / is_thin_liquidity columns from a date column.

    Falls back to deriving the NY date from ``timestamp`` if ``date_col`` is
    absent.
    """
    out = df.copy()
    if date_col not in out.columns:
        from .calendar import ny_session_date
        out[date_col] = ny_session_date(out["timestamp"])
    dates = pd.Series(out[date_col])
    out["is_holiday"] = dates.map(is_holiday)
    out["is_thin_liquidity"] = dates.map(is_thin_liquidity)
    return out
