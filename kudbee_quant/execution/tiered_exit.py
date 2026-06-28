"""Tiered exit — a CONFIG + thin helpers over the shared resolver.

The three-stage exit (bank at TP1, trim at TP2, trail a runner) is implemented
ONCE in ``backtest/resolver.py`` (the source of truth shared by the backtest and
the live/paper journal). This module just bundles the parameters and exposes:

  - :class:`TieredExitConfig`   — the knobs (TP1 40% @1R, TP2 35% @2R, runner 25%
                                  ATR-trailed with a 1R floor, 48-bar cap, dynamic TP2).
  - :func:`dynamic_tp2_r`       — momentum score -> TP2 R multiple.
  - :func:`resolver_kwargs`     — config (+ optional momentum score) -> the kwargs
                                  ``resolve_bracket`` / ``bracket_backtest`` expect.
  - stage helpers (:func:`get_stage`, :func:`current_r`, :func:`unrealized_r_locked`)
    over a light :class:`TieredPosition` view, for live management + tests.

Keeping this a config layer (not a parallel engine) means a tiered paper trade and
a tiered backtest can never disagree about what a trade did.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class TieredExitConfig:
    tp1_r: float = 1.0           # bank tp1_size_pct here, move stop to breakeven
    tp1_size_pct: float = 0.40
    tp2_r: float = 2.0           # bank tp2_size_pct here, runner stop -> 1R floor
    tp2_size_pct: float = 0.35
    runner_pct: float = 0.25     # the remainder — trailed
    runner_trail_atr_mult: float = 1.5
    runner_hard_floor_r: float = 1.0
    max_hold_bars: int = 48
    use_dynamic_tp2: bool = True
    # Dynamic-TP2 thresholds (momentum score -> TP2 R).
    dyn_hi: float = 0.65
    dyn_lo: float = 0.35
    tp2_r_strong: float = 3.0
    tp2_r_weak: float = 1.5
    # Upside cap for the runner in price terms (the runner is otherwise governed by
    # the trail + the bar cap). Kept well beyond TP2 so the trail dominates.
    final_target_r: float = 6.0

    def __post_init__(self):
        total = self.tp1_size_pct + self.tp2_size_pct + self.runner_pct
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"tiered sizes must sum to 1.0 (got {total:.4f}: "
                f"tp1={self.tp1_size_pct}, tp2={self.tp2_size_pct}, runner={self.runner_pct})")


def dynamic_tp2_r(score: float, config: TieredExitConfig) -> float:
    """Map a 0..1 momentum score to the TP2 R multiple."""
    if score > config.dyn_hi:
        return config.tp2_r_strong
    if score < config.dyn_lo:
        return config.tp2_r_weak
    return config.tp2_r


def resolver_kwargs(config: TieredExitConfig, momentum: float | None = None) -> dict:
    """The kwargs ``resolve_bracket``/``bracket_backtest`` need to express this config.

    ``momentum`` (0..1), when given and ``use_dynamic_tp2`` is on, scales TP2.
    Returns a dict with ``target_r`` (the runner upside cap) plus the tp1/tp2/runner
    knobs; the caller supplies entry/stop/df.
    """
    tp2_r = config.tp2_r
    if config.use_dynamic_tp2 and momentum is not None:
        tp2_r = dynamic_tp2_r(momentum, config)
    return {
        "target_r": config.final_target_r,
        "tp1_r": config.tp1_r,
        "tp1_frac": config.tp1_size_pct,
        "be_after_tp1": True,
        "tp2_r": tp2_r,
        "tp2_frac": config.tp2_size_pct,
        "runner_trail_atr": config.runner_trail_atr_mult,
        "runner_floor_r": config.runner_hard_floor_r,
        "runner_max_bars": config.max_hold_bars,
    }


# --- light position view for live management + tests ------------------------

@dataclass
class TieredPosition:
    """Minimal state needed to reason about a tiered trade's stage in R-space."""
    entry: float
    stop: float            # the ORIGINAL 1R stop (entry +/- 1R)
    direction: float       # +1 long / -1 short
    config: TieredExitConfig
    tp1_filled: bool = False
    tp2_filled: bool = False

    @property
    def sd(self) -> float:
        return abs(self.entry - self.stop)


Stage = Literal["entry_to_tp1", "tp1_to_tp2", "runner"]


def get_stage(pos: TieredPosition) -> Stage:
    if not pos.tp1_filled:
        return "entry_to_tp1"
    if not pos.tp2_filled:
        return "tp1_to_tp2"
    return "runner"


def current_r(pos: TieredPosition, price: float) -> float:
    """Mark-to-market R of the position at ``price`` (1R = ``sd``)."""
    if pos.sd <= 0:
        return 0.0
    return pos.direction * (price - pos.entry) / pos.sd


def unrealized_r_locked(pos: TieredPosition) -> float:
    """R that is GUARANTEED given the scale-outs already banked and where the stop
    sits: TP1 banked (its tranche at tp1_r) + breakeven on the rest after TP1, and
    +runner_floor on the runner once TP2 has banked."""
    c = pos.config
    locked = 0.0
    if pos.tp1_filled:
        locked += c.tp1_size_pct * c.tp1_r          # banked at TP1
    if pos.tp2_filled:
        locked += c.tp2_size_pct * c.tp2_r          # banked at TP2
        locked += c.runner_pct * c.runner_hard_floor_r   # runner floor
    return locked
