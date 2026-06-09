"""Paper-trading loop — forward validation of the confluence-R edge.

Backtesting is backward-looking. This scans the watchlist for the current
confluence-R signal and logs each as a bracket paper trade (entry, 1R stop,
target_r target) into the journal. Re-running journal-check later resolves them
against real price IN R, accumulating a FORWARD track record on data the model
has never seen — the one validation a backtest cannot give.
"""

from .paper import paper_scan

__all__ = ["paper_scan"]
