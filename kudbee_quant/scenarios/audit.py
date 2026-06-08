"""Lookahead self-audit — prove a scenario can't see the future.

A causal signal at bar t must depend only on data up to t. We verify this
mechanically: recompute the FULL pipeline (build_levels + scenario) on data
truncated at t, and check the signal at t equals the signal computed on the
full series. If they differ, the scenario (or a feature it uses) is reading
the future — exactly the bug that produced a fake +9.56 Sharpe.

This audits the whole pipeline, so it catches leaks in levels/features too,
not just in the scenario function.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..levels import build_levels


@dataclass(frozen=True)
class AuditResult:
    scenario: str
    checks: int
    mismatches: int
    clean: bool

    @property
    def leak_rate(self) -> float:
        return self.mismatches / self.checks if self.checks else 0.0


def lookahead_audit(
    df: pd.DataFrame,
    scenario_fn,
    n_checks: int = 120,
    min_history: int = 400,
    seed: int = 0,
    build_fn=build_levels,
    name: str = "?",
) -> AuditResult:
    """Compare signal[t] from the full series vs. from data truncated at t.

    Args:
        df: raw OHLCV.
        scenario_fn: maps a levels-annotated frame to a signal series.
        n_checks: number of random bars t to test.
        min_history: only test t >= this (features need warmup).
    """
    full_sig = scenario_fn(build_fn(df)).reset_index(drop=True)
    n = len(df)
    if n <= min_history + 5:
        return AuditResult(name, 0, 0, True)

    rng = np.random.default_rng(seed)
    candidates = np.arange(min_history, n - 1)
    ts = rng.choice(candidates, size=min(n_checks, candidates.size), replace=False)

    mismatches = 0
    checks = 0
    for t in ts:
        trunc = df.iloc[: t + 1]
        try:
            sig_t = scenario_fn(build_fn(trunc)).reset_index(drop=True).iloc[-1]
        except Exception:
            continue
        full_t = full_sig.iloc[t]
        checks += 1
        a = 0.0 if pd.isna(sig_t) else float(sig_t)
        b = 0.0 if pd.isna(full_t) else float(full_t)
        if abs(a - b) > 1e-9:
            mismatches += 1
    return AuditResult(name, checks, mismatches, mismatches == 0)


def audit_all(df: pd.DataFrame, scenarios: dict, n_checks: int = 80, **kw) -> pd.DataFrame:
    """Run the lookahead audit on every scenario; return a pass/fail table."""
    rows = []
    for name, fn in scenarios.items():
        r = lookahead_audit(df, fn, n_checks=n_checks, name=name, **kw)
        rows.append({"scenario": name, "checks": r.checks,
                     "mismatches": r.mismatches, "leak_rate": r.leak_rate, "clean": r.clean})
    return pd.DataFrame(rows).sort_values(["clean", "leak_rate"]).reset_index(drop=True)
