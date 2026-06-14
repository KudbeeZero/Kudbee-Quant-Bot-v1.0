"""Runtime trading-mode + risk-control config, read from the environment.

SAFETY CONTRACT (the whole point of this module):
  * Default mode is PAPER and live execution is DISABLED. You have to *opt in*
    twice — set ``TRADING_MODE=live`` AND ``ENABLE_LIVE_EXECUTION=true`` — before
    any real order can be placed. ``require_live_enabled()`` is the single choke
    point that enforces it; the live executor calls it before touching an exchange.
  * NO secrets live here. Exchange API keys are read only inside the (future) live
    executor, only from env, and are never hardcoded or logged. This module reads
    non-secret knobs (mode, caps, exchange name) only.

Env vars (all optional; safe defaults shown):
    TRADING_MODE=paper|live          (default: paper)
    ENABLE_LIVE_EXECUTION=false      (default: false)
    MAX_CONCURRENT_POSITIONS=10      (default: 10)
    MAX_POSITION_SIZE_USD=100        (default: 100)
    MAX_DAILY_LOSS_USD=250           (default: 250)
    EXCHANGE_NAME=binance            (default: binance)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

_TRUE = {"1", "true", "yes", "on"}
VALID_MODES = {"paper", "live"}


class LiveExecutionBlocked(RuntimeError):
    """Raised when live order placement is attempted without BOTH opt-in flags."""


def _env_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    return default if raw is None else raw.strip().lower() in _TRUE


def _env_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as e:
        raise ValueError(f"{name} must be a number, got {raw!r}") from e


def _env_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from e


@dataclass(frozen=True)
class RuntimeConfig:
    trading_mode: str               # "paper" | "live"
    enable_live_execution: bool
    max_concurrent_positions: int
    max_position_size_usd: float
    max_daily_loss_usd: float
    exchange_name: str

    @property
    def is_live(self) -> bool:
        """True ONLY when both opt-ins are set — the real-money switch."""
        return self.trading_mode == "live" and self.enable_live_execution

    def as_dict(self) -> dict:
        return {
            "trading_mode": self.trading_mode,
            "enable_live_execution": self.enable_live_execution,
            "is_live": self.is_live,
            "max_concurrent_positions": self.max_concurrent_positions,
            "max_position_size_usd": self.max_position_size_usd,
            "max_daily_loss_usd": self.max_daily_loss_usd,
            "exchange_name": self.exchange_name,
        }


def load_runtime_config(env: Mapping[str, str] | None = None) -> RuntimeConfig:
    """Build a :class:`RuntimeConfig` from ``env`` (defaults to ``os.environ``).

    Fails safe: an unknown ``TRADING_MODE`` raises rather than silently going live.
    """
    env = os.environ if env is None else env
    mode = env.get("TRADING_MODE", "paper").strip().lower() or "paper"
    if mode not in VALID_MODES:
        raise ValueError(f"TRADING_MODE must be one of {sorted(VALID_MODES)}, got {mode!r}")
    return RuntimeConfig(
        trading_mode=mode,
        enable_live_execution=_env_bool(env, "ENABLE_LIVE_EXECUTION", False),
        max_concurrent_positions=_env_int(env, "MAX_CONCURRENT_POSITIONS", 10),
        max_position_size_usd=_env_float(env, "MAX_POSITION_SIZE_USD", 100.0),
        max_daily_loss_usd=_env_float(env, "MAX_DAILY_LOSS_USD", 250.0),
        exchange_name=env.get("EXCHANGE_NAME", "binance").strip().lower() or "binance",
    )


def require_live_enabled(cfg: RuntimeConfig | None = None) -> RuntimeConfig:
    """The single guard before any real order. Returns the config if live is fully
    enabled; otherwise raises :class:`LiveExecutionBlocked`. Default config => raise.
    """
    cfg = cfg or load_runtime_config()
    if not cfg.is_live:
        raise LiveExecutionBlocked(
            "live execution is DISABLED — set TRADING_MODE=live and "
            "ENABLE_LIVE_EXECUTION=true to enable real orders "
            f"(currently mode={cfg.trading_mode!r}, "
            f"enable_live_execution={cfg.enable_live_execution})"
        )
    return cfg
