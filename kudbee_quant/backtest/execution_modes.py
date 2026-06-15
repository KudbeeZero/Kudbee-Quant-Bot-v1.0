"""Execution head-to-head: maker-retrace vs market-at-signal vs hybrid.

RESEARCH-ONLY (offline). This module does NOT touch the live trading path. It
exists to answer one question honestly: of the three ways to ENTER a confluence
signal, which has the best NET-OF-FEES out-of-sample expectancy per timeframe?

It deliberately reuses the shared trade resolver (``backtest/resolver.py``) for
the forward stop/target walk, so a trade resolves identically to the live journal
and the production ``bracket_backtest`` — only the ENTRY rule and the FEE model
differ here.

Three entry modes (all no-lookahead — a signal is decided at bar T's CLOSE):

  maker_retrace : the CURRENT live rule. A LIMIT rests at ``close[T] - dir*0.25*ATR``
                  and fills only if price retraces to it within ``entry_window``
                  bars; otherwise the signal is CANCELLED (no trade). Maker fee in.
  market        : fill at the OPEN of bar T+1 (you cannot fill at the signal price
                  itself). Taker fee in.
  hybrid        : the limit rests for ONE bar (T+1); if unfilled, cancel and chase
                  with a market order at the OPEN of bar T+2. Maker fee if the limit
                  fills, taker fee if chased.

FEE MODEL (honest, per-leg, MEMORY §25 measured rates):
  - taker = 0.00045 / side  (market-in, stop-out, and time-stop market-out)
  - maker = 0.0002  / side  (resting-limit entry, and target exit) — NOT yet
            confirmed from a real limit fill; flagged as an assumption.
  Exits are costed BY TYPE: a STOP is a market-out (taker); a TARGET is a resting
  limit (maker); a TIME-STOP is a market-out (taker). Cost in R = (entry_side +
  exit_side) * entry_price / stop_distance, the same price->R conversion the live
  ``bracket_backtest`` uses.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .resolver import resolve_bracket

# Measured live fee rates (MEMORY §25). Maker side is an assumption pending a real
# limit-fill confirmation; taker side is verified on 5 live BTCC fills.
TAKER_SIDE = 0.00045
MAKER_SIDE = 0.0002

# Exits that cross the spread (pay taker). A target rests as a limit (maker).
_TAKER_EXITS = {"stop", "time"}


def _classify_exit(outcome_r: float, target_r: float) -> str:
    """Recover the exit TYPE from the resolver's R outcome (fast path is exact)."""
    if outcome_r == -1.0:
        return "stop"
    if outcome_r == target_r:
        return "target"
    return "time"


def _resolve_and_cost(direction, entry, entry_side, sd, target_r, max_bars,
                      high, low, close, entry_bar, n, taker_side, maker_side):
    """Walk the trade forward via the shared resolver and apply per-leg fees."""
    stop = entry - direction * sd
    target = entry + direction * sd * target_r
    end = min(entry_bar + max_bars, n - 1)
    out = resolve_bracket(direction, entry, stop, target, sd, target_r,
                          high[entry_bar + 1:end + 1], low[entry_bar + 1:end + 1],
                          close[entry_bar + 1:end + 1], force_close_at_end=True)
    if out.exit_offset is None:        # no bars after entry -> mark to close at entry bar
        gross = direction * (close[end] - entry) / sd
        exit_bar, exit_type = end, "time"
    else:
        gross = out.outcome_r
        exit_bar = entry_bar + 1 + out.exit_offset
        exit_type = _classify_exit(gross, target_r)
    exit_side = taker_side if exit_type in _TAKER_EXITS else maker_side
    cost = (entry_side + exit_side) * entry / sd
    return {"gross_r": float(gross), "net_r": float(gross - cost),
            "cost_r": float(cost), "exit_type": exit_type, "exit_bar": int(exit_bar)}


def run_variant(df: pd.DataFrame, signal, *, mode: str, stop_atr: float = 1.5,
                target_r: float = 3.0, max_bars: int = 24, retrace_atr: float = 0.25,
                entry_window: int = 6, taker_side: float = TAKER_SIDE,
                maker_side: float = MAKER_SIDE, start_idx: int = 0,
                allow_overlap: bool = False) -> dict:
    """Run one execution variant over a signal series.

    Returns {"trades": [...], "attempts": [...]}. Each attempt is a non-busy signal
    the variant tried to enter (with a ``filled`` flag); each trade is a filled
    attempt with its net/gross R, cost, and exit type. ``start_idx`` skips warmup
    bars (signals before the OOS window start). Non-overlap by default: a cancelled
    maker attempt does NOT block later signals (it never tied up capital), but a
    filled trade does until it exits.
    """
    need = {"open", "high", "low", "close", "atr"}
    if not need <= set(df.columns):
        raise ValueError(f"run_variant needs columns {sorted(need)}")
    op = df["open"].to_numpy()
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    atr = df["atr"].to_numpy()
    sig = pd.Series(signal, index=df.index).fillna(0.0).to_numpy()
    n = len(df)

    trades: list[dict] = []
    attempts: list[dict] = []
    busy_until = -1
    for t in range(start_idx, n - 1):
        if sig[t] == 0 or (not allow_overlap and t <= busy_until):
            continue
        direction = 1.0 if sig[t] > 0 else -1.0
        a = atr[t]
        sd = stop_atr * a
        if not np.isfinite(sd) or sd <= 0:
            continue

        entry_bar = entry = entry_side = None
        filled = False
        if mode == "maker_retrace":
            limit = close[t] - direction * retrace_atr * a
            ewin = min(t + entry_window, n - 1)
            for j in range(t + 1, ewin + 1):
                if (direction > 0 and low[j] <= limit) or (direction < 0 and high[j] >= limit):
                    entry_bar, entry, entry_side, filled = j, limit, maker_side, True
                    break
        elif mode == "market":
            entry_bar, entry, entry_side, filled = t + 1, op[t + 1], taker_side, True
        elif mode == "hybrid":
            limit = close[t] - direction * retrace_atr * a
            j = t + 1
            if (direction > 0 and low[j] <= limit) or (direction < 0 and high[j] >= limit):
                entry_bar, entry, entry_side, filled = t + 1, limit, maker_side, True
            elif t + 2 <= n - 1:
                entry_bar, entry, entry_side, filled = t + 2, op[t + 2], taker_side, True
        else:
            raise ValueError(f"unknown mode {mode!r}")

        attempts.append({"t": int(t), "direction": float(direction), "filled": bool(filled)})
        if not filled:
            continue
        rec = _resolve_and_cost(direction, entry, entry_side, sd, target_r, max_bars,
                                high, low, close, entry_bar, n, taker_side, maker_side)
        rec.update({"t": int(t), "entry_bar": int(entry_bar), "direction": float(direction),
                    "entry_side": float(entry_side)})
        trades.append(rec)
        if not allow_overlap:
            busy_until = rec["exit_bar"]
    return {"trades": trades, "attempts": attempts}


def adverse_selection(df: pd.DataFrame, signal, *, stop_atr: float = 1.5,
                      target_r: float = 3.0, max_bars: int = 24, retrace_atr: float = 0.25,
                      entry_window: int = 6, taker_side: float = TAKER_SIDE,
                      maker_side: float = MAKER_SIDE, start_idx: int = 0) -> list[dict]:
    """STEP 3 — resolve every signal the maker retrace CANCELLED as a MARKET entry.

    If those missed trades are net POSITIVE, the retrace is provably anti-selecting
    (throwing away edge the bot never captures). Each cancelled signal is resolved
    independently (overlap allowed — we are measuring SIGNAL QUALITY, not running a
    book) as a market fill at the open of T+1, taker in.
    """
    mk = run_variant(df, signal, mode="maker_retrace", stop_atr=stop_atr, target_r=target_r,
                     max_bars=max_bars, retrace_atr=retrace_atr, entry_window=entry_window,
                     taker_side=taker_side, maker_side=maker_side, start_idx=start_idx)
    op = df["open"].to_numpy()
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    atr = df["atr"].to_numpy()
    n = len(df)
    recs: list[dict] = []
    for a in mk["attempts"]:
        if a["filled"]:
            continue
        t = a["t"]
        if t + 1 > n - 1:
            continue
        direction = a["direction"]
        sd = stop_atr * atr[t]
        if not np.isfinite(sd) or sd <= 0:
            continue
        rec = _resolve_and_cost(direction, op[t + 1], taker_side, sd, target_r, max_bars,
                                high, low, close, t + 1, n, taker_side, maker_side)
        rec.update({"t": int(t), "direction": float(direction)})
        recs.append(rec)
    return recs


def bootstrap_p(net, n_boot: int = 5000, seed: int = 0) -> float:
    """P(mean net R <= 0) by per-trade bootstrap. NaN on an empty sample.

    Chunked to bound memory on large (5m) samples.
    """
    arr = np.asarray(net, dtype=float)
    m = arr.size
    if m == 0:
        return float("nan")
    rng = np.random.default_rng(seed)
    le_zero = 0
    done = 0
    while done < n_boot:
        chunk = min(1000, n_boot - done)
        idx = rng.integers(0, m, size=(chunk, m))
        means = arr[idx].mean(axis=1)
        le_zero += int((means <= 0).sum())
        done += chunk
    return le_zero / n_boot


def summarize(net, *, target_r: float = 3.0) -> dict:
    """Net-of-fees metrics for a list of per-trade net R values."""
    arr = np.asarray(net, dtype=float)
    n = arr.size
    if n == 0:
        return {"n_trades": 0, "win_rate": float("nan"), "expectancy_r": float("nan"),
                "total_r": 0.0, "profit_factor": float("nan"), "max_drawdown_r": 0.0,
                "bootstrap_p": float("nan")}
    wins = arr[arr > 0]
    losses = arr[arr < 0]
    equity = np.cumsum(arr)
    peak = np.maximum.accumulate(equity)
    pf = float(wins.sum() / -losses.sum()) if losses.sum() < 0 else float("inf")
    return {
        "n_trades": int(n),
        "win_rate": float((arr > 0).mean()),
        "expectancy_r": float(arr.mean()),
        "total_r": float(arr.sum()),
        "profit_factor": pf,
        "max_drawdown_r": float((equity - peak).min()),
        "bootstrap_p": bootstrap_p(arr),
    }
