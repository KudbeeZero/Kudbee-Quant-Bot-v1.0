"""Order-execution layer — PAPER today, LIVE gated + stubbed.

The repo has always been paper/research only (no exchange order placement). This
package is the *foundation* for execution without crossing the money line yet:

  * :class:`PaperExecutor` — fully functional; turns a signal bracket into a journal
    trade (the same record the hourly paper loop already produces), stamped
    ``mode="paper"``.
  * :class:`LiveExecutor` — a STUB. It calls the runtime guard
    (``require_live_enabled``) and then raises ``NotImplementedError``. Real order
    placement (ccxt / authenticated Binance REST, fills, balances, order-id mapping)
    is a deliberate FOLLOW-UP PR, after the paper book proves out forward.

Safety: live execution is double-gated (``TRADING_MODE=live`` +
``ENABLE_LIVE_EXECUTION=true``) and there are no credentials in this package.
"""
from __future__ import annotations

from .base import Executor, ExecutionResult, STRATEGY_VERSION
from .paper import PaperExecutor
from .live import LiveExecutor, build_executor

__all__ = [
    "Executor", "ExecutionResult", "STRATEGY_VERSION",
    "PaperExecutor", "LiveExecutor", "build_executor",
]
