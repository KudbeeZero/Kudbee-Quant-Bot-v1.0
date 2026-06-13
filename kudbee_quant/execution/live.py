"""Live executor — STUB. Double-gated; real order placement is a follow-up PR.

This deliberately does NOT place orders. It exists so the foundation has a real
seam for live execution and a tested guarantee that nothing can trade real money by
accident. Two things must BOTH be true (``require_live_enabled``) for it to get past
the guard at all — and even then it raises ``NotImplementedError`` until the
authenticated exchange client lands.
"""
from __future__ import annotations

from ..config.runtime import RuntimeConfig, load_runtime_config, require_live_enabled
from ..journal import Prediction, TradeJournal
from .base import ExecutionResult
from .paper import PaperExecutor


class LiveExecutor:
    mode = "live"

    def __init__(self, cfg: RuntimeConfig | None = None):
        # Guard at construction: you cannot even instantiate a live executor unless
        # both opt-in flags are set. Raises LiveExecutionBlocked otherwise.
        self.cfg = require_live_enabled(cfg or load_runtime_config())

    def submit(self, prediction: Prediction) -> ExecutionResult:  # pragma: no cover
        # Re-check the guard at submit time, then refuse — no order client yet.
        require_live_enabled(self.cfg)
        raise NotImplementedError(
            "live order placement is not implemented yet — this is the gated stub. "
            "Real fills (authenticated exchange client, order-id mapping, balance "
            "checks) ship in a dedicated follow-up PR once the paper book proves out."
        )


def build_executor(cfg: RuntimeConfig | None = None,
                   journal: TradeJournal | None = None) -> PaperExecutor | LiveExecutor:
    """Pick the executor for the current runtime config. PAPER unless live is fully
    enabled (``TRADING_MODE=live`` + ``ENABLE_LIVE_EXECUTION=true``)."""
    cfg = cfg or load_runtime_config()
    if cfg.is_live:
        return LiveExecutor(cfg)
    return PaperExecutor(journal=journal,
                         max_concurrent_positions=cfg.max_concurrent_positions)
