"""Scenario battery + sweep — the alpha search engine.

We can't find alpha by believing harder; we find it by enumerating many
concrete, mechanical hypotheses from the hybrid theory / vector candles and
testing them ALL with the same rigor (out-of-sample Sharpe across assets),
then surfacing any survivor. Most will be nulls — that's expected. The job is
to catch the few that aren't, and not fool ourselves about the rest.
"""

from .audit import audit_all, lookahead_audit
from .btmm import BTMM_SCENARIOS
from .ict import ICT_SCENARIOS
from .library import SCENARIOS as _BASE_SCENARIOS
from .library import hold
from .sweep import run_sweep

# Full registry = original battery + precise BTMM/PVSRA + ICT/Vol1-3 setups.
SCENARIOS = {**_BASE_SCENARIOS, **BTMM_SCENARIOS, **ICT_SCENARIOS}

__all__ = ["SCENARIOS", "BTMM_SCENARIOS", "hold", "run_sweep", "audit_all", "lookahead_audit"]
