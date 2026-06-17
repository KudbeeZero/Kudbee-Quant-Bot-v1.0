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

from .resolver import resolve_bracket


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
    require_confirmation: bool = False,
    tp1_r: float | None = None,
    tp1_frac: float = 0.5,
    be_after_tp1: bool = True,
    tp2_r: float | None = None,
    tp2_frac: float = 0.0,
    leverage: float = 1.0,
    trailing_atr: float | None = None,
    mae_giveup: tuple | None = None,
    time_decay: tuple | None = None,
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
        tp1_r: if set, take partial profit at this R-multiple (TARGET ONE) and
            let the remainder run to ``target_r`` (TARGET TWO). ``tp1_frac`` of
            the position is closed at TP1; the rest stays on. This is the
            "scale out" / "bank some, ride the rest" management the user asked
            for. When None, the trade is all-or-nothing at ``target_r`` (legacy).
        tp1_frac: fraction of the position closed at TP1 (default 0.5 = half).
        be_after_tp1: after TP1 fills, move the stop on the remainder to
            BREAKEVEN (entry). This is the classic "free trade" — once half is
            banked, the worst case on the rest is ~0R. Conservative within a
            bar: the (breakeven) stop is checked before the favorable level.
        tp2_r: if set (requires ``tp1_r``), add a SECOND scale-out leg at this
            R-multiple between TP1 and ``target_r`` — bank a further ``tp2_frac``
            of the original position there, ride the remainder to ``target_r``.
            This is the three-leg "bank most at TP1, trim again, let a runner
            ride" management (e.g. 75% at TP1 / 10% at TP2 / 15% at target).
            ``tp1_frac + tp2_frac`` must be < 1.0. Default-off.
        tp2_frac: fraction of the ORIGINAL position closed at TP2 (default 0.0).
        leverage: multiply each trade's net R by this factor. R-expectancy is
            risk-defined and so leverage-INVARIANT in *sign*; leverage only
            amplifies the magnitude — both the edge and the drawdown (and the
            fee drag) scale by it. 1.25x means +25% bigger wins AND losses. It
            does NOT model liquidation/margin-call; it is a linear P&L scaler.
    """
    need = {"high", "low", "close", "atr"}
    if not need <= set(df.columns):
        raise ValueError(f"bracket_backtest needs columns {sorted(need)}")
    op = df["open"].to_numpy() if "open" in df.columns else df["close"].to_numpy()
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
                touched = (direction > 0 and low[j] <= limit) or (direction < 0 and high[j] >= limit)
                if touched and (not require_confirmation or
                                _is_confirmation(op[j], high[j], low[j], close[j], direction)):
                    entry_bar = j
                    break
            if entry_bar is None:
                continue  # retrace never came; signal missed (realistic)
            entry = limit
        stop = entry - direction * sd
        target = entry + direction * sd * target_r
        end = min(entry_bar + max_bars, n - 1)
        if tp1_r is None:
            outcome, exit_j = _resolve_full(direction, entry, stop, target, sd,
                                            target_r, high, low, close, entry_bar, end,
                                            atr_at_entry=atr[t], trailing_atr=trailing_atr,
                                            mae_giveup=mae_giveup, time_decay=time_decay)
            extra_exit = 0.0
        else:
            outcome, exit_j = _resolve_partial(direction, entry, sd, target_r, tp1_r,
                                               tp1_frac, be_after_tp1, high, low, close,
                                               entry_bar, end, tp2_r=tp2_r, tp2_frac=tp2_frac)
            extra_exit = tp1_frac + (tp2_frac if tp2_r is not None else 0.0)
        # Realistic cost: convert a price-fraction cost to R via the stop size.
        # Each partial exit (TP1, TP2) incurs an extra half round-trip on its fraction.
        cost = fee_r if fee_pct is None else fee_pct * entry / sd * (1 + 0.5 * extra_exit)
        trade_size = sz[t] if size is not None else 1.0
        # Leverage is a linear P&L scaler on the net R (amplifies edge AND drawdown).
        trades.append((outcome - cost) * trade_size * leverage)
        busy_until = exit_j

    return _summarize(trades, target_r)


def bracket_excursions(
    df: pd.DataFrame,
    signal: pd.Series,
    stop_atr: float = 1.5,
    max_bars: int = 24,
    limit_retrace_atr: float | None = 0.25,
    entry_window: int = 6,
) -> pd.DataFrame:
    """Per-trade Max Favorable / Adverse Excursion in R — the honest answer to
    "how often does price reach 1R, 1.5R, 2R, 3R before my stop?".

    For each entered trade (same entry logic as ``bracket_backtest``: optional
    limit-retrace fill, fixed stop = 1R), walk forward until the stop is hit or
    ``max_bars`` elapse, and record:
      mfe_r  : the furthest FAVORABLE move reached, in R (capped at the bar the
               stop hits — you can only bank what came before you were stopped).
      mae_r  : the furthest ADVERSE move (<=0; -1 means the stop was reached).
      stopped: whether the 1R stop was hit within the window.
    With this, P(mfe_r >= X) is exactly the hit-rate of a take-profit at X R.
    """
    need = {"high", "low", "close", "atr"}
    if not need <= set(df.columns):
        raise ValueError(f"bracket_excursions needs columns {sorted(need)}")
    close = df["close"].to_numpy(); high = df["high"].to_numpy()
    low = df["low"].to_numpy(); atr = df["atr"].to_numpy()
    op = df["open"].to_numpy() if "open" in df.columns else close
    sig = pd.Series(signal, index=df.index).fillna(0.0).to_numpy()
    n = len(df)
    rows = []
    busy_until = -1
    for t in range(n - 1):
        if sig[t] == 0 or t <= busy_until:
            continue
        direction = 1.0 if sig[t] > 0 else -1.0
        sd = stop_atr * atr[t]
        if not np.isfinite(sd) or sd <= 0:
            continue
        if limit_retrace_atr is None:
            entry, entry_bar = close[t], t
        else:
            limit = close[t] - direction * limit_retrace_atr * atr[t]
            ewin = min(t + entry_window, n - 1)
            entry_bar = None
            for j in range(t + 1, ewin + 1):
                if (direction > 0 and low[j] <= limit) or (direction < 0 and high[j] >= limit):
                    entry_bar = j; break
            if entry_bar is None:
                continue
            entry = limit
        stop = entry - direction * sd
        end = min(entry_bar + max_bars, n - 1)
        mfe = 0.0; mae = 0.0; stopped = False; exit_j = end
        for j in range(entry_bar + 1, end + 1):
            fav = direction * (high[j] - entry) / sd if direction > 0 else direction * (low[j] - entry) / sd
            adv = direction * (low[j] - entry) / sd if direction > 0 else direction * (high[j] - entry) / sd
            mfe = max(mfe, fav)
            mae = min(mae, adv)
            hit_stop = (low[j] <= stop) if direction > 0 else (high[j] >= stop)
            if hit_stop:
                stopped = True; exit_j = j; mae = min(mae, -1.0); break
        rows.append({"entry_bar": int(entry_bar), "direction": direction,
                     "mfe_r": float(mfe), "mae_r": float(mae), "stopped": stopped})
        busy_until = exit_j
    return pd.DataFrame(rows)


def _resolve_full(direction, entry, stop, target, sd, target_r,
                  high, low, close, entry_bar, end, *, atr_at_entry=None,
                  trailing_atr=None, mae_giveup=None, time_decay=None):
    """All-or-nothing exit: first of stop/target wins; else mark to close.

    Thin adapter over the shared resolver (``backtest/resolver.py``) so the
    backtest and the live journal resolve trades identically. Optional
    path-dependent exits (trailing/MAE-giveup/time-decay) are forwarded.
    """
    out = resolve_bracket(direction, entry, stop, target, sd, target_r,
                          high[entry_bar + 1:end + 1], low[entry_bar + 1:end + 1],
                          close[entry_bar + 1:end + 1], force_close_at_end=True,
                          atr_at_entry=atr_at_entry, trailing_atr=trailing_atr,
                          mae_giveup=mae_giveup, time_decay=time_decay)
    if out.exit_offset is None:     # no bars after entry: mark to close at entry bar
        return direction * (close[end] - entry) / sd, end
    return out.outcome_r, entry_bar + 1 + out.exit_offset


def _resolve_partial(direction, entry, sd, target_r, tp1_r, tp1_frac, be_after_tp1,
                     high, low, close, entry_bar, end, *, tp2_r=None, tp2_frac=0.0):
    """Scale-out exit: bank ``tp1_frac`` at TARGET ONE (tp1_r), optionally trim a
    further ``tp2_frac`` at TARGET TWO (tp2_r), then ride the remainder to the
    final target (target_r); optionally move the stop to breakeven after TP1.

    Returns the BLENDED R for the whole position. Thin adapter over the shared
    resolver — see ``backtest/resolver.py`` for the (conservative) walk logic.
    """
    stop = entry - direction * sd
    tp1 = entry + direction * sd * tp1_r
    tp2 = (entry + direction * sd * tp2_r) if tp2_r is not None else None
    target = entry + direction * sd * target_r
    out = resolve_bracket(direction, entry, stop, target, sd, target_r,
                          high[entry_bar + 1:end + 1], low[entry_bar + 1:end + 1],
                          close[entry_bar + 1:end + 1], force_close_at_end=True,
                          tp1=tp1, tp1_r=tp1_r, tp1_frac=tp1_frac, be_after_tp1=be_after_tp1,
                          tp2=tp2, tp2_r=tp2_r, tp2_frac=tp2_frac)
    if out.exit_offset is None:     # no bars after entry: mark to close at entry bar
        return direction * (close[end] - entry) / sd, end
    return out.outcome_r, entry_bar + 1 + out.exit_offset


def _is_confirmation(o: float, h: float, l: float, c: float, direction: float) -> bool:
    """A candlestick confirmation/reversal candle in the trade direction.

    Long: a bullish close with either a large lower 'stopping' wick (hammer/pin
    bar rejecting lower) OR a strong bullish body. Short is the mirror (shooting
    star / strong bearish body). This is the 'stopping candle at the level'
    confirmation from the methodology (Vol 8), applied at the retrace fill.
    """
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    lower_wick = min(o, c) - l
    upper_wick = h - max(o, c)
    if direction > 0:
        return (c > o) and (lower_wick >= 0.5 * rng or body >= 0.6 * rng)
    return (c < o) and (upper_wick >= 0.5 * rng or body >= 0.6 * rng)


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
