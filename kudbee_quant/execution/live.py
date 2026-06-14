"""Live executor — places REAL maker limit orders behind the double gate.

Replaces the former stub. Reaching any order call still requires BOTH opt-in
flags (``require_live_enabled`` — ``TRADING_MODE=live`` + ``ENABLE_LIVE_EXECUTION=true``);
paper remains the default and ``build_executor`` only ever returns this when live
is fully enabled.

What a live submit does, in order:
  1. re-check the gate;
  2. check the ``MAX_DAILY_LOSS_USD`` kill-switch (today's realized live loss);
  3. honour ``max_concurrent_positions``;
  4. size the position (capped by ``MAX_POSITION_SIZE_USD``);
  5. rest a MAKER-only limit at the signal's ``entry`` (never a market/taker order
     — §25: taker kills the edge);
  6. journal the trade as a LIVE, PENDING limit with its ``exchange_order_id``.

Fills are NOT inferred from bars. ``poll()`` asks the venue for the order's real
status and stamps ``filled_at`` from the exchange clock (§29), and ``cancel()``
pulls a resting limit. ``reconcile()`` sweeps all live open/pending trades.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..config.runtime import RuntimeConfig, load_runtime_config, require_live_enabled
from ..journal import Prediction, TradeJournal
from .base import STRATEGY_VERSION, ExecutionResult
from .exchange import BUY, SELL, BinanceBrokerClient, ExchangeClient, OrderError
from .killswitch import DailyLossLimitReached, check_daily_loss
from .paper import PaperExecutor


class LiveExecutor:
    mode = "live"

    def __init__(self, cfg: RuntimeConfig | None = None,
                 journal: TradeJournal | None = None,
                 exchange: ExchangeClient | None = None):
        # Guard at construction: cannot instantiate unless BOTH opt-ins are set.
        self.cfg = require_live_enabled(cfg or load_runtime_config())
        self.journal = journal or TradeJournal()
        # Built lazily-by-default so the executor can exist before keys are wired;
        # the broker only raises on a missing key when an authenticated call runs.
        self.exchange = exchange or BinanceBrokerClient()

    def _open_count(self) -> int:
        return sum(1 for p in self.journal.predictions
                   if p.mode == "live" and p.status in ("open", "pending"))

    def _reject(self, reason: str) -> ExecutionResult:
        return ExecutionResult(accepted=False, mode=self.mode, prediction=None, reason=reason)

    def submit(self, prediction: Prediction) -> ExecutionResult:
        require_live_enabled(self.cfg)

        if prediction.kind != "bracket" or prediction.entry is None or prediction.stop is None:
            return self._reject("live execution only handles bracket signals with an entry/stop")
        if prediction.direction not in (1.0, -1.0):
            return self._reject(f"bracket direction must be +1/-1, got {prediction.direction}")

        # (2) kill-switch — today's realized live loss vs MAX_DAILY_LOSS_USD.
        try:
            check_daily_loss(self.journal, self.cfg.max_daily_loss_usd)
        except DailyLossLimitReached as e:
            return self._reject(str(e))

        # (3) concurrency cap.
        if self._open_count() >= self.cfg.max_concurrent_positions:
            return self._reject(
                f"max_concurrent_positions={self.cfg.max_concurrent_positions} reached; "
                "live signal skipped")

        # (4) sizing — never exceed the per-position cap.
        requested = prediction.position_size_usd or self.cfg.max_position_size_usd
        size_usd = min(float(requested), self.cfg.max_position_size_usd)
        if size_usd <= 0:
            return self._reject(f"position size must be positive, got {size_usd}")
        qty = size_usd / prediction.entry
        side = BUY if prediction.direction > 0 else SELL

        # (5) rest the maker limit at the retrace entry.
        try:
            order = self.exchange.create_limit_order(
                prediction.symbol, side, qty, prediction.entry)
        except OrderError as e:
            return self._reject(f"exchange rejected order: {e}")

        # (6) journal it as a LIVE, PENDING limit carrying the venue order id.
        prediction.mode = "live"
        if prediction.strategy_version is None:
            prediction.strategy_version = STRATEGY_VERSION
        prediction.position_size_usd = size_usd
        prediction.exchange_order_id = order.order_id
        prediction.pending_limit = True
        prediction.signal_price = prediction.signal_price or prediction.entry
        # A freshly-rested limit is PENDING; mark filled only if the venue already
        # reported a fill (LIMIT_MAKER normally rests, so this is usually pending).
        if order.is_filled:
            prediction.status = "open"
            prediction.filled_at = order.filled_at or datetime.now(timezone.utc).isoformat()
        else:
            prediction.status = "pending"
        self.journal.add(prediction)
        return ExecutionResult(accepted=True, mode=self.mode, prediction=prediction,
                               reason=f"live limit order {order.order_id} resting at {prediction.entry}")

    def poll(self, prediction: Prediction) -> Prediction:
        """Refresh one live trade from the venue. Stamps ``filled_at`` from the
        EXCHANGE clock when filled; flips a cancelled/expired limit to cancelled.
        Persists and returns the (possibly updated) prediction."""
        if prediction.mode != "live" or not prediction.exchange_order_id:
            return prediction
        order = self.exchange.fetch_order(prediction.symbol, prediction.exchange_order_id)
        changed = False
        if order.is_filled and prediction.status == "pending":
            prediction.status = "open"
            prediction.filled_at = order.filled_at or datetime.now(timezone.utc).isoformat()
            changed = True
        elif order.status in ("canceled", "rejected") and prediction.status == "pending":
            prediction.status = "cancelled"
            prediction.reason_closed = f"venue {order.status} (order {order.order_id})"
            changed = True
        if changed:
            self.journal.save()
        return prediction

    def cancel(self, prediction: Prediction) -> Prediction:
        """Pull a resting live limit and mark it cancelled. Persists."""
        if prediction.mode != "live" or not prediction.exchange_order_id:
            return prediction
        self.exchange.cancel_order(prediction.symbol, prediction.exchange_order_id)
        if prediction.status == "pending":
            prediction.status = "cancelled"
            prediction.reason_closed = "cancelled by operator"
            self.journal.save()
        return prediction

    def reconcile(self) -> list[Prediction]:
        """Poll every live open/pending trade against the venue; return those that
        changed state. (Resolution of stop/target still flows through the journal's
        OHLCV path; this only syncs FILLS/cancels that the venue knows and bars
        don't.)"""
        changed = []
        for p in list(self.journal.predictions):
            if p.mode != "live" or p.status not in ("open", "pending"):
                continue
            before = (p.status, p.filled_at)
            self.poll(p)
            if (p.status, p.filled_at) != before:
                changed.append(p)
        return changed


def build_executor(cfg: RuntimeConfig | None = None,
                   journal: TradeJournal | None = None,
                   exchange: ExchangeClient | None = None) -> PaperExecutor | LiveExecutor:
    """Pick the executor for the current runtime config. PAPER unless live is fully
    enabled (``TRADING_MODE=live`` + ``ENABLE_LIVE_EXECUTION=true``)."""
    cfg = cfg or load_runtime_config()
    if cfg.is_live:
        return LiveExecutor(cfg, journal=journal, exchange=exchange)
    return PaperExecutor(journal=journal,
                         max_concurrent_positions=cfg.max_concurrent_positions)
