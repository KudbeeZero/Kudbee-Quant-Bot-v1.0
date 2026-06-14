"""Paper executor — records a signal bracket as a journal trade (no real order).

This is the functional default. It writes the SAME ``Prediction`` record the hourly
paper loop produces, stamped ``mode="paper"`` + the strategy version, and enforces a
``max_concurrent_positions`` cap so a 100-symbol scan can't open an unbounded book.
"""
from __future__ import annotations

from ..journal import Prediction, TradeJournal
from .base import STRATEGY_VERSION, ExecutionResult


class PaperExecutor:
    mode = "paper"

    def __init__(self, journal: TradeJournal | None = None,
                 max_concurrent_positions: int | None = None):
        self.journal = journal or TradeJournal()
        self.max_concurrent_positions = max_concurrent_positions

    def _open_count(self) -> int:
        return sum(1 for p in self.journal.predictions
                   if p.status in ("open", "pending"))

    def submit(self, prediction: Prediction) -> ExecutionResult:
        if (self.max_concurrent_positions is not None
                and self._open_count() >= self.max_concurrent_positions):
            return ExecutionResult(
                accepted=False, mode=self.mode, prediction=None,
                reason=(f"max_concurrent_positions={self.max_concurrent_positions} "
                        "reached; signal skipped"),
            )
        prediction.mode = "paper"
        if prediction.strategy_version is None:
            prediction.strategy_version = STRATEGY_VERSION
        self.journal.add(prediction)
        return ExecutionResult(accepted=True, mode=self.mode, prediction=prediction,
                               reason="paper trade recorded")
