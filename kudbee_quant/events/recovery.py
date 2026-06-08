"""Vector-candle recovery study — the honest answer to 'does it get recovered?'

Tino's claim: every vector candle eventually gets revisited. As stated that's
unfalsifiable (no time bound). We make it testable: for each vector candle,
how many bars until price RE-ENTERS the candle's price box, and what fraction
are recovered within N bars (the survival curve) — compared to a NULL model
(an equal-width zone placed at the same distance but a random direction). The
vector only carries information if its recovery rate beats the null.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .detectors import detect_vector_events


NEVER_EXITED = -2  # price never left the zone within the horizon (excluded)
NOT_RECOVERED = -1  # price left but did not return within the horizon


def _bars_to_recover(high: np.ndarray, low: np.ndarray, start: int,
                     zlow: float, zhigh: float, horizon: int) -> int:
    """Bars from ``start`` until price LEAVES [zlow, zhigh] then RETURNS.

    Requiring an exit first removes the trivial artifact that adjacent candles
    overlap (so the next bar is already 'in the box'). This measures the real
    claim: an abandoned zone getting revisited. Returns bars-from-start to the
    return, or NOT_RECOVERED / NEVER_EXITED sentinels.
    """
    end = min(start + horizon, len(high) - 1)
    exited = False
    for j in range(start + 1, end + 1):
        if not exited:
            if low[j] > zhigh or high[j] < zlow:  # fully outside the zone
                exited = True
            continue
        if high[j] >= zlow and low[j] <= zhigh:    # returned into the zone
            return j - start
    return NOT_RECOVERED if exited else NEVER_EXITED


@dataclass(frozen=True)
class RecoveryResult:
    n_vectors: int
    horizons: list[int]
    recovered_frac: dict[int, float]      # P(recovered within horizon) for vectors
    null_frac: dict[int, float]           # same for random equal-width zones
    median_bars_to_recover: float         # over those that recovered within max horizon

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame({
            "horizon": self.horizons,
            "vector_recovered": [self.recovered_frac[h] for h in self.horizons],
            "null_recovered": [self.null_frac[h] for h in self.horizons],
            "edge_vs_null": [self.recovered_frac[h] - self.null_frac[h] for h in self.horizons],
        })


def recovery_curve(
    df: pd.DataFrame,
    horizons=(1, 5, 15, 60, 240, 1440),
    seed: int = 42,
) -> RecoveryResult:
    """Compute the vector recovery survival curve and a random-zone null.

    ``df`` must already carry vector columns (build_features). The null places,
    for each vector, an equal-width zone at the same distance from the entry
    close but offset by a random signed amount, and measures its recovery —
    isolating how much of "it gets recovered" is just price wandering back to
    any nearby level.
    """
    ev = detect_vector_events(df).reset_index(drop=True)
    high = ev["high"].to_numpy()
    low = ev["low"].to_numpy()
    close = ev["close"].to_numpy()
    idx = np.where(ev["is_vector"].to_numpy())[0]
    max_h = max(horizons)
    rng = np.random.default_rng(seed)

    rec_bars = []
    horizon_hits = {h: 0 for h in horizons}
    null_horizon_hits = {h: 0 for h in horizons}
    counted = 0  # vectors that actually exited their zone (valid recovery tests)

    for t in idx:
        if t >= len(high) - 1:
            continue
        zlow, zhigh = low[t], high[t]
        width = zhigh - zlow
        b = _bars_to_recover(high, low, t, zlow, zhigh, max_h)
        if b == NEVER_EXITED:
            continue  # price never left the zone in-horizon; not a recovery test
        counted += 1
        rec_bars.append(b)
        for h in horizons:
            if 0 < b <= h:
                horizon_hits[h] += 1

        # Null: equal-width zone shifted by +/- (0.5..2.0) widths in a random dir.
        shift = rng.choice([-1, 1]) * rng.uniform(0.5, 2.0) * (width if width > 0 else close[t] * 0.001)
        nb = _bars_to_recover(high, low, t, zlow + shift, zhigh + shift, max_h)
        for h in horizons:
            if 0 < nb <= h:
                null_horizon_hits[h] += 1

    n = max(counted, 1)
    recovered_within_max = [b for b in rec_bars if 0 < b <= max_h]
    return RecoveryResult(
        n_vectors=counted,
        horizons=list(horizons),
        recovered_frac={h: horizon_hits[h] / n for h in horizons},
        null_frac={h: null_horizon_hits[h] / n for h in horizons},
        median_bars_to_recover=float(np.median(recovered_within_max)) if recovered_within_max else float("nan"),
    )
