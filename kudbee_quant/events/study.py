"""Conditional base-rate table with anti-self-deception statistics.

This is the honesty engine for events. For each (event x context-bucket) it
reports n, the win rate, a Wilson confidence interval, and a p-value against
the null (coin-flip for boolean outcomes). Buckets below a minimum sample are
marked insufficient and never acted on. Across many buckets we control the
false-discovery rate (Benjamini-Hochberg), because slicing data into
Tuesday x NY x 2nd-test x 3h-in spawns many hypotheses and *some* will look
significant by chance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (better than normal at small n)."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _two_sided_binom_p(successes: int, n: int, p0: float = 0.5) -> float:
    """Normal-approx two-sided p-value for a proportion vs p0 (fast, fine for n>~30)."""
    if n == 0:
        return 1.0
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 1.0
    z = (successes / n - p0) / se
    # two-sided normal tail via erfc
    return math.erfc(abs(z) / math.sqrt(2))


def benjamini_hochberg(pvalues: list[float], alpha: float = 0.10) -> list[bool]:
    """Return a reject/keep mask controlling FDR at ``alpha`` (BH procedure)."""
    m = len(pvalues)
    if m == 0:
        return []
    order = np.argsort(pvalues)
    thresh = alpha * (np.arange(1, m + 1) / m)
    sorted_p = np.array(pvalues)[order]
    passed = sorted_p <= thresh
    k = np.max(np.where(passed)[0]) + 1 if passed.any() else 0
    rejected = np.zeros(m, dtype=bool)
    if k > 0:
        rejected[order[:k]] = True
    return rejected.tolist()


@dataclass(frozen=True)
class StudyConfig:
    min_n: int = 30          # below this, a bucket is "insufficient", never trusted
    z: float = 1.96          # 95% CI
    fdr_alpha: float = 0.10  # false-discovery-rate target across buckets


def conditional_table(
    events: pd.DataFrame,
    outcome_col: str,
    group_cols: list[str],
    config: StudyConfig | None = None,
) -> pd.DataFrame:
    """Compute P(outcome | context bucket) with CIs, p-values and FDR control.

    Args:
        events: one row per event, with the context columns and a boolean (or
            0/1) ``outcome_col``.
        outcome_col: boolean/0-1 outcome (e.g. fwd_up_4).
        group_cols: context columns defining the buckets (e.g.
            ['day_of_week', 'session', 'daily_open_nth_test']).

    Returns a DataFrame sorted by sample size with columns: the group cols,
    n, wins, win_rate, ci_low, ci_high, p_value, sufficient (n>=min_n),
    significant_fdr (survives Benjamini-Hochberg among sufficient buckets).
    """
    config = config or StudyConfig()
    df = events.dropna(subset=[outcome_col]).copy()
    df[outcome_col] = df[outcome_col].astype(bool)

    rows = []
    for keys, g in df.groupby(group_cols, dropna=False):
        n = len(g)
        wins = int(g[outcome_col].sum())
        lo, hi = wilson_ci(wins, n, config.z)
        p = _two_sided_binom_p(wins, n, 0.5)
        key_tuple = keys if isinstance(keys, tuple) else (keys,)
        rows.append({**dict(zip(group_cols, key_tuple)),
                     "n": n, "wins": wins, "win_rate": wins / n if n else float("nan"),
                     "ci_low": lo, "ci_high": hi, "p_value": p,
                     "sufficient": n >= config.min_n})

    table = pd.DataFrame(rows)
    if table.empty:
        return table

    table["significant_fdr"] = False
    suff = table["sufficient"]
    if suff.any():
        rejected = benjamini_hochberg(table.loc[suff, "p_value"].tolist(), config.fdr_alpha)
        table.loc[suff, "significant_fdr"] = rejected
    return table.sort_values("n", ascending=False).reset_index(drop=True)
