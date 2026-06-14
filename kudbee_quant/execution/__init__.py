"""Order-execution layer — PAPER today, LIVE gated + stubbed.

The repo has always been paper/research only (no exchange order placement). This
package is the *foundation* for execution without crossing the money line yet:

  * :class:`PaperExecutor` — fully functional; turns a signal bracket into a journal
    trade (the same record the hourly paper loop already produces), stamped
    ``mode="paper"``.
  * :class:`LiveExecutor` — places REAL maker-only limit orders behind the double
    gate (``require_live_enabled``): kill-switch + sizing + a ``LIMIT_MAKER`` rest
    at the retrace entry, journaled as a live pending limit with its venue
    order-id. Fills are polled from the exchange (not inferred from bars).

Safety: live execution is double-gated (``TRADING_MODE=live`` +
``ENABLE_LIVE_EXECUTION=true``); credentials are read from the environment only,
inside :class:`~kudbee_quant.execution.exchange.BinanceBrokerClient`, never here.
"""
from __future__ import annotations

from .base import Executor, ExecutionResult, STRATEGY_VERSION
from .paper import PaperExecutor
from .exchange import (
    BinanceBrokerClient, ExchangeClient, OrderError, OrderResult,
    BUY, SELL, FILLED, NEW, PARTIAL, CANCELED, REJECTED,
)
from .killswitch import DailyLossLimitReached, check_daily_loss, realized_loss_usd_today
from .live import LiveExecutor, build_executor

__all__ = [
    "Executor", "ExecutionResult", "STRATEGY_VERSION",
    "PaperExecutor", "LiveExecutor", "build_executor",
    "ExchangeClient", "BinanceBrokerClient", "OrderResult", "OrderError",
    "BUY", "SELL", "FILLED", "NEW", "PARTIAL", "CANCELED", "REJECTED",
    "DailyLossLimitReached", "check_daily_loss", "realized_loss_usd_today",
]
