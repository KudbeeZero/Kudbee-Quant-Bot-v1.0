"""Scenario battery + sweep — the alpha search engine.

We can't find alpha by believing harder; we find it by enumerating many
concrete, mechanical hypotheses from the hybrid theory / vector candles and
testing them ALL with the same rigor (out-of-sample Sharpe across assets),
then surfacing any survivor. Most will be nulls — that's expected. The job is
to catch the few that aren't, and not fool ourselves about the rest.
"""

from .library import SCENARIOS, hold
from .sweep import run_sweep

__all__ = ["SCENARIOS", "hold", "run_sweep"]
