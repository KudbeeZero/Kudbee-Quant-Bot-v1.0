"""Executor interface shared by the paper and (future) live paths."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..journal import Prediction

# Bumped when the validated bracket logic changes (so each trade record is
# attributable to a strategy revision). The numbers themselves live in
# config/validated_defaults.py (§1) — this is just a label.
STRATEGY_VERSION = "confluence_r_v1"


@dataclass
class ExecutionResult:
    """Outcome of submitting one signal to an executor."""
    accepted: bool
    mode: str                       # "paper" | "live"
    prediction: Prediction | None   # the journaled trade, if accepted
    reason: str = ""                # why rejected / informational note


class Executor(Protocol):
    """Anything that can turn a signal bracket into a recorded order."""

    mode: str

    def submit(self, prediction: Prediction) -> ExecutionResult:
        """Record/place the order represented by ``prediction``."""
        ...
