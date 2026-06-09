"""Bracket (stop / target) backtester — measures R, not win-rate.

This models how a scalper actually trades: enter at the signal, place a STOP a
fixed distance away (defined risk = 1R), and a TARGET at an R-multiple of that
risk. Exit when stop or target hits. The metric that matters is EXPECTANCY in R
(average R per trade) and total R — a 40% win rate at 2.5R wins is very
profitable. Win-rate alone is the wrong lens for an asymmetric strategy.

Conservatism: if a bar's range spans both stop and target, we assume the STOP
filled first (worst case), so results are not flattered.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BracketResult:
    n_trades: int
    win_rate: float
    avg_win_r: float
    avg_loss_r: float
    expectancy_r: float      # mean R per trade — the number that matters
    total_r: float
    profit_factor: float
    max_drawdown_r: float
    target_r: float
    trades: list

    def summary(self) -> dict:
        return {"n_trades": self.n_trades, "win_rate": self.win_rate,
                "avg_win_r": self.avg_win_r, "avg_loss_r": self.avg_loss_r,
                "expectancy_r": self.expectancy_r, "total_r": self.total_r,
                "profit_factor": self.profit_factor, "max_drawdown_r": self.max_drawdown_r}


def bracket_backtest(
    df: pd.DataFrame,
    signal: pd.Series,
    stop_atr: float = 1.0,
    target_r: float = 2.0,
    max_bars: int = 24,
    fee_r: float = 0.02,
    allow_overlap: bool = False,
    size: pd.Series | None = None,
    fee_pct: float | None = None,
    limit_retrace_atr: float | None = None,
    entry_window: int = 6,
) -> BracketResult:
    """Run a stop/target bracket backtest from an entry-signal series.

    Args:
        signal: {-1,0,+1} entry triggers (long/flat/short) decided at bar close.
        stop_atr: stop distance = stop_atr * ATR at entry (= 1R).
        target_r: take-profit at target_r * R.
        max_bars: time-stop; if neither level hits, exit at that bar's close.
        fee_r: round-trip cost in R (flat). Used when ``fee_pct`` is None.
        fee_pct: realistic round-trip cost as a FRACTION OF PRICE (e.g. 0.0010
            = 0.10%). Converted per-trade to R via cost / (stop distance %), so
            cost is correctly timeframe-aware — tiny stops (1m) cost many R,
            wider stops (1h+) cost a fraction of R. Strongly preferred over the
            flat fee_r, which can badly understate low-timeframe costs.
        allow_overlap: if False, no new entry until the current trade exits.
        size: optional per-bar position size in [0,1]; each trade's R is scaled
            by the size at entry (confidence-scaled sizing). Default 1.0.
        limit_retrace_atr: if set, enter via a LIMIT order at a pullback of
            ``limit_retrace_atr`` * ATR against the signal (maker fill, better
            price — the Vol 8 "enter on the retrace, not the signal candle"
            rule). The trade only fills if price retraces to the limit within
            ``entry_window`` bars; otherwise the signal is MISSED (no trade).
            Stop/target are measured from the limit fill price.
        entry_window: bars allowed for a limit entry to fill.
    """
    need = {"high", "low", "close", "atr"}
    if not need <= set(df.columns):
        raise ValueError(f"bracket_backtest needs columns {sorted(need)}")
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    atr = df["atr"].to_numpy()
    sig = pd.Series(signal, index=df.index).fillna(0.0).to_numpy()
    sz = (pd.Series(size, index=df.index).fillna(0.0).to_numpy()
          if size is not None else np.ones(len(df)))
    n = len(df)

    trades: list[float] = []
    busy_until = -1
    for t in range(n - 1):
        if sig[t] == 0 or t <= busy_until:
            continue
        direction = 1.0 if sig[t] > 0 else -1.0
        sd = stop_atr * atr[t]
        if not np.isfinite(sd) or sd <= 0:
            continue
        # Entry: market at the signal close, or a LIMIT at a retrace (maker).
        if limit_retrace_atr is None:
            entry, entry_bar = close[t], t
        else:
            limit = close[t] - direction * limit_retrace_atr * atr[t]
            ewin = min(t + entry_window, n - 1)
            entry_bar = None
            for j in range(t + 1, ewin + 1):
                if (direction > 0 and low[j] <= limit) or (direction < 0 and high[j] >= limit):
                    entry_bar = j
                    break
            if entry_bar is None:
                continue  # retrace never came; signal missed (realistic)
            entry = limit
        stop = entry - direction * sd
        target = entry + direction * sd * target_r
        end = min(entry_bar + max_bars, n - 1)
        outcome = None
        exit_j = end
        for j in range(entry_bar + 1, end + 1):
            if direction > 0:
                if low[j] <= stop:      # stop checked first (conservative)
                    outcome, exit_j = -1.0, j; break
                if high[j] >= target:
                    outcome, exit_j = target_r, j; break
            else:
                if high[j] >= stop:
                    outcome, exit_j = -1.0, j; break
                if low[j] <= target:
                    outcome, exit_j = target_r, j; break
        if outcome is None:             # time-stop: mark to the exit close in R
            outcome = direction * (close[end] - entry) / sd
        # Realistic cost: convert a price-fraction cost to R via the stop size.
        cost = fee_r if fee_pct is None else fee_pct * entry / sd
        trade_size = sz[t] if size is not None else 1.0
        trades.append((outcome - cost) * trade_size)
        busy_until = exit_j

    return _summarize(trades, target_r)


def _summarize(trades: list, target_r: float) -> BracketResult:
    arr = np.array(trades, dtype=float)
    n = arr.size
    if n == 0:
        return BracketResult(0, 0, 0, 0, 0, 0, 0, 0, target_r, [])
    wins = arr[arr > 0]
    losses = arr[arr < 0]
    equity = np.cumsum(arr)
    peak = np.maximum.accumulate(equity)
    max_dd = float((equity - peak).min()) if n else 0.0
    pf = float(wins.sum() / -losses.sum()) if losses.sum() < 0 else float("inf")
    return BracketResult(
        n_trades=n,
        win_rate=float((arr > 0).mean()),
        avg_win_r=float(wins.mean()) if wins.size else 0.0,
        avg_loss_r=float(losses.mean()) if losses.size else 0.0,
        expectancy_r=float(arr.mean()),
        total_r=float(arr.sum()),
        profit_factor=pf,
        max_drawdown_r=max_dd,
        target_r=target_r,
        trades=trades,
    )
