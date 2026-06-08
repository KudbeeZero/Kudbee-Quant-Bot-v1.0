"""Position sizing. Fractional Kelly with hard caps — never full Kelly.

Full Kelly maximizes long-run growth but is brutally volatile and assumes
you know your edge exactly (you don't). We expose a *fraction* of Kelly and
cap it, because surviving estimation error matters more than theoretical
optimality.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def kelly_fraction_from_returns(returns: pd.Series) -> float:
    """Continuous Kelly fraction f* = mean / variance of per-trade returns.

    Returns 0.0 when there's no estimable positive edge. This is an estimate
    from a finite sample, so treat it as an upper bound, not truth.
    """
    r = pd.Series(returns).dropna().astype(float)
    if r.size < 2:
        return 0.0
    var = float(r.var(ddof=1))
    if var <= 0:
        return 0.0
    f = float(r.mean()) / var
    return max(0.0, f)


def fractional_kelly(
    returns: pd.Series,
    fraction: float = 0.25,
    cap: float = 1.0,
) -> float:
    """Recommended position fraction = fraction * Kelly, capped.

    Args:
        returns: historical per-trade (or per-bar in-position) returns.
        fraction: how much of full Kelly to use (0.25 = quarter-Kelly).
        cap: maximum fraction of capital to deploy.
    """
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    full = kelly_fraction_from_returns(returns)
    return float(min(cap, fraction * full))
