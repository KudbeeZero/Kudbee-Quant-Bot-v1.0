"""Multi-asset / multi-period validation — the edge prover (or killer).

A strategy that works on one asset over one window is an anecdote. This
package runs a strategy across a *universe* of assets, scores each one on
its OUT-OF-SAMPLE behaviour, and renders a deliberately conservative
verdict. The goal is not to confirm an edge — it is to try hard to *break*
it, and only report robustness when it refuses to break.
"""

from .universe import (
    AssetReport,
    UniverseReport,
    validate_frames,
    validate_universe,
)

__all__ = [
    "AssetReport",
    "UniverseReport",
    "validate_frames",
    "validate_universe",
]
