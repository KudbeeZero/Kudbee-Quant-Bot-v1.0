"""Backtest comparison: flat TP vs tiered scale-out exits, over one signal series.

Runs the SAME entries through five exit configurations and reports per-config
stats, so the question "does a tiered scale-out keep more of each winner than a
flat TP?" is answered with numbers, not assertion:

  A  flat 1R          (target_r=1.0, no scale-out)
  B  flat 2R
  C  flat 3R
  D  tiered, static   (TP1@1R 40% -> TP2@2R 35% -> ATR-trailed 25% runner, 1R floor)
  E  tiered, dynamic  (D, but TP2 R scaled per-trade by the momentum score)

Entries are taken at the signal bar's close (market) and held identically across
configs, so the ONLY thing that differs is the exit — an apples-to-apples read.
All five reuse the shared ``resolve_bracket`` (the live path's resolver), so the
backtest can't flatter a behaviour the live book wouldn't reproduce.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from ..execution.tiered_exit import TieredExitConfig, resolver_kwargs, dynamic_tp2_r
from ..signals.momentum_score import momentum_score
from ..signals.pvsra import pvsra_vector_candles
from .resolver import resolve_bracket


@dataclass(frozen=True)
class ConfigStats:
    name: str
    n_trades: int
    total_r: float
    expectancy_r: float
    win_rate: float
    profit_factor: float
    max_drawdown_r: float
    avg_duration_bars: float
    calmar: float
    pct_reached_tp2: float            # tiered only (0 for flat configs)
    tiered_exit_efficiency: float     # mean(net_r / MFE_r) over winners
    avg_runner_contribution_r: float  # mean runner-tranche R (tiered only)


def _max_dd_r(net: list[float]) -> float:
    eq = np.cumsum(net) if net else np.array([0.0])
    peak = np.maximum.accumulate(eq)
    return float((eq - peak).min()) if len(eq) else 0.0


def _summarize(name: str, trades: list[dict]) -> ConfigStats:
    net = [t["net"] for t in trades]
    n = len(net)
    if n == 0:
        return ConfigStats(name, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    wins = [r for r in net if r > 0]
    losses = [r for r in net if r < 0]
    total = float(sum(net))
    pf = (sum(wins) / -sum(losses)) if losses else float("inf")
    max_dd = _max_dd_r(net)
    eff_vals = [t["net"] / t["mfe"] for t in trades if t["net"] > 0 and t["mfe"] > 0]
    runner_vals = [t["runner_r"] for t in trades if t["runner_r"] is not None]
    tp2_flags = [t["reached_tp2"] for t in trades]
    return ConfigStats(
        name=name, n_trades=n, total_r=round(total, 4),
        expectancy_r=round(total / n, 4),
        win_rate=round(len(wins) / n, 4),
        profit_factor=round(pf, 4) if pf != float("inf") else float("inf"),
        max_drawdown_r=round(max_dd, 4),
        avg_duration_bars=round(float(np.mean([t["dur"] for t in trades])), 2),
        calmar=round(total / abs(max_dd), 4) if max_dd < 0 else float("inf"),
        pct_reached_tp2=round(float(np.mean(tp2_flags)), 4) if tp2_flags else 0.0,
        tiered_exit_efficiency=round(float(np.mean(eff_vals)), 4) if eff_vals else 0.0,
        avg_runner_contribution_r=round(float(np.mean(runner_vals)), 4) if runner_vals else 0.0,
    )


def _run_config(df, signal, *, stop_atr, fee_pct, max_bars, target_r,
                tp1_r=None, tp1_frac=0.0, tp2_r=None, tp2_frac=0.0,
                runner_trail_atr=None, runner_floor_r=1.0, runner_max_bars=None,
                dyn_cfg: TieredExitConfig | None = None) -> list[dict]:
    high = df["high"].to_numpy(); low = df["low"].to_numpy()
    close = df["close"].to_numpy(); atr = df["atr"].to_numpy()
    sig = signal.to_numpy() if hasattr(signal, "to_numpy") else np.asarray(signal)
    n = len(close)
    out_trades: list[dict] = []
    busy_until = 0
    for t in range(n - 1):
        d = sig[t]
        if d == 0 or t < busy_until:
            continue
        atr_t = float(atr[t])
        if not np.isfinite(atr_t) or atr_t <= 0:
            continue
        entry = float(close[t]); sd = stop_atr * atr_t
        stop = entry - d * sd
        # per-trade TP2 (dynamic) when configured
        tp2_r_eff = tp2_r
        if dyn_cfg is not None and tp2_r is not None:
            ms = momentum_score(df, t, d, since_idx=t, sd=sd)
            tp2_r_eff = dynamic_tp2_r(ms, dyn_cfg)
        tp1 = entry + d * sd * tp1_r if tp1_r else None
        tp2 = entry + d * sd * tp2_r_eff if tp2_r_eff else None
        target = entry + d * sd * target_r
        end = min(t + max_bars, n - 1)
        h = high[t + 1:end + 1]; l = low[t + 1:end + 1]; c = close[t + 1:end + 1]
        out = resolve_bracket(
            d, entry, stop, target, sd, target_r, h, l, c, force_close_at_end=True,
            tp1=tp1, tp1_r=tp1_r, tp1_frac=tp1_frac, be_after_tp1=True,
            tp2=tp2, tp2_r=tp2_r_eff, tp2_frac=tp2_frac,
            atr_at_entry=atr_t, runner_trail_atr=runner_trail_atr,
            runner_floor_r=runner_floor_r, runner_max_bars=runner_max_bars)
        if out.exit_offset is None:
            continue
        extra_exit = (tp1_frac if tp1_r else 0.0) + (tp2_frac if tp2_r_eff else 0.0)
        cost = fee_pct * entry / sd * (1 + 0.5 * extra_exit)
        net = float(out.outcome_r) - cost
        # MFE in R over the realised holding window (for exit efficiency).
        held = slice(0, out.exit_offset + 1)
        if d > 0:
            mfe = float((h[held].max() - entry) / sd) if len(h[held]) else 0.0
        else:
            mfe = float((entry - l[held].min()) / sd) if len(l[held]) else 0.0
        out_trades.append({
            "net": net, "dur": out.exit_offset + 1,
            "reached_tp2": out.tp2_offset is not None,
            "runner_r": (float(out.runner_r) if out.runner_r is not None else None),
            "mfe": mfe,
        })
        busy_until = t + 1 + out.exit_offset
    return out_trades


def compare_exit_configs(df: pd.DataFrame, signal: pd.Series, *,
                         stop_atr: float = 1.5, fee_pct: float = 0.0009,
                         max_bars: int = 48,
                         config: TieredExitConfig | None = None) -> dict:
    """Run configs A-E over one (df, signal) and return ``{name: ConfigStats}``
    plus a flat ``table`` list and the bar count used."""
    cfg = config or TieredExitConfig()
    runs = run_all_configs(df, signal, stop_atr=stop_atr, fee_pct=fee_pct,
                           max_bars=max_bars, config=cfg)
    stats = {name: _summarize(name, trades) for name, trades in runs.items()}
    return {
        "n_bars": int(len(df)),
        "stop_atr": stop_atr, "fee_pct": fee_pct, "max_bars": max_bars,
        "configs": {name: asdict(s) for name, s in stats.items()},
        "table": [asdict(s) for s in stats.values()],
    }


def run_all_configs(df: pd.DataFrame, signal: pd.Series, *, stop_atr: float = 1.5,
                    fee_pct: float = 0.0009, max_bars: int = 48,
                    config: TieredExitConfig | None = None) -> dict:
    """Return ``{config_name: [trade dicts]}`` for A-E over one (df, signal).
    Callers can concatenate these lists across symbols, then ``_summarize`` each."""
    cfg = config or TieredExitConfig()
    if "is_climax" not in df.columns:
        df = pvsra_vector_candles(df)
    tk = resolver_kwargs(cfg)
    return {
        "A_flat_1R": _run_config(df, signal, stop_atr=stop_atr, fee_pct=fee_pct,
                                 max_bars=max_bars, target_r=1.0),
        "B_flat_2R": _run_config(df, signal, stop_atr=stop_atr, fee_pct=fee_pct,
                                 max_bars=max_bars, target_r=2.0),
        "C_flat_3R": _run_config(df, signal, stop_atr=stop_atr, fee_pct=fee_pct,
                                 max_bars=max_bars, target_r=3.0),
        "D_tiered_static": _run_config(
            df, signal, stop_atr=stop_atr, fee_pct=fee_pct, max_bars=max_bars,
            target_r=tk["target_r"], tp1_r=tk["tp1_r"], tp1_frac=tk["tp1_frac"],
            tp2_r=tk["tp2_r"], tp2_frac=tk["tp2_frac"],
            runner_trail_atr=tk["runner_trail_atr"], runner_floor_r=tk["runner_floor_r"],
            runner_max_bars=tk["runner_max_bars"]),
        "E_tiered_dynamic": _run_config(
            df, signal, stop_atr=stop_atr, fee_pct=fee_pct, max_bars=max_bars,
            target_r=tk["target_r"], tp1_r=tk["tp1_r"], tp1_frac=tk["tp1_frac"],
            tp2_r=tk["tp2_r"], tp2_frac=tk["tp2_frac"],
            runner_trail_atr=tk["runner_trail_atr"], runner_floor_r=tk["runner_floor_r"],
            runner_max_bars=tk["runner_max_bars"], dyn_cfg=cfg),
    }


def summarize_runs(runs: dict, n_bars: int, *, stop_atr: float, fee_pct: float,
                   max_bars: int) -> dict:
    """Summarise ``{name: [trades]}`` (already aggregated) into the result dict."""
    stats = {name: _summarize(name, trades) for name, trades in runs.items()}
    return {
        "n_bars": int(n_bars), "stop_atr": stop_atr, "fee_pct": fee_pct,
        "max_bars": max_bars,
        "configs": {name: asdict(s) for name, s in stats.items()},
        "table": [asdict(s) for s in stats.values()],
    }


def format_table(result: dict) -> str:
    """Render the comparison as a fixed-width text table."""
    cols = [("name", 18), ("n_trades", 9), ("total_r", 10), ("expectancy_r", 13),
            ("win_rate", 9), ("profit_factor", 14), ("max_drawdown_r", 15),
            ("avg_duration_bars", 18), ("calmar", 9), ("pct_reached_tp2", 16),
            ("tiered_exit_efficiency", 23), ("avg_runner_contribution_r", 26)]
    head = "".join(f"{k:>{w}}" for k, w in cols)
    lines = [f"Tiered exit comparison — {result['n_bars']} bars, "
             f"stop_atr={result['stop_atr']}, fee_pct={result['fee_pct']}, max_bars={result['max_bars']}",
             head, "-" * len(head)]
    for row in result["table"]:
        lines.append("".join(f"{row[k]!s:>{w}}" for k, w in cols))
    return "\n".join(lines)
