"""Shared bracket trade resolver — the single source of truth for "given an entry
and forward price path, how did this trade resolve in R?".

WHY THIS EXISTS: the same stop/target/TP1 logic was implemented twice — once in
``backtest/bracket.py`` (vectorised backtest over a signal series) and once in
``journal/journal.py`` (forward resolution of a single live Prediction). Two copies
drift. This module is the ONE implementation both delegate to, so a backtest and a
live paper trade can never disagree about what a trade did. It is also the single
place new path-dependent exits (trailing stop, MAE give-up, time-decay target) get
added — once, for both.

The core is deliberately price-based (explicit stop/target/tp1 PRICES + an explicit
``win_r`` credited at the target and ``sd`` = 1R distance), because the journal may
carry a ``target`` price that isn't exactly ``entry + dir*sd*win_r``; passing prices
reproduces both callers' behaviour exactly.

Conservatism (unchanged from both originals): within a bar the STOP is checked
before the favorable level, so results are never flattered.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolveOutcome:
    """Result of walking a trade forward over the bars AFTER entry.

    exited:      a stop/target (or forced end-of-window close) ended the trade.
    outcome_r:   realized R if exited (blended across tranches for TP1 trades);
                 None when not exited and no forced close (journal "still open").
    exit_offset: index into the forward arrays where the exit happened (or None).
    tp1_offset:  index where TP1 banked (or None) — lets the journal stamp
                 ``tp1_filled_at`` without re-deriving it.
    """
    exited: bool
    outcome_r: float | None
    exit_offset: int | None
    tp1_offset: int | None = None


def resolve_bracket(
    direction: float,
    entry: float,
    stop: float,
    target: float,
    sd: float,
    win_r: float,
    high,
    low,
    close,
    *,
    force_close_at_end: bool = True,
    tp1: float | None = None,
    tp1_r: float | None = None,
    tp1_frac: float = 0.5,
    be_after_tp1: bool = True,
) -> ResolveOutcome:
    """Walk the forward bars (``high``/``low``/``close`` are the bars AFTER the
    entry bar, in order) and resolve the trade.

    Args:
        direction: +1 long / -1 short.
        entry: fill price.
        stop: hard stop price (= 1R from entry).
        target: take-profit price (TARGET TWO when TP1 is used).
        sd: stop distance in price (1R) — used to express mark-to-close in R.
        win_r: R credited when ``target`` is reached (e.g. 3.0).
        force_close_at_end: if True, when neither level is hit, mark the trade to
            the last bar's close in R and report it as exited (backtest behaviour
            and journal time-stop). If False, report exited=False (journal "open").
        tp1, tp1_r, tp1_frac, be_after_tp1: optional scale-out at TARGET ONE — bank
            ``tp1_frac`` at ``tp1`` (worth ``tp1_r`` R), ride the rest to ``target``;
            move the stop to breakeven after TP1 when ``be_after_tp1``.

    Returns a :class:`ResolveOutcome`.
    """
    n = len(high)
    if n == 0:
        return ResolveOutcome(False, None, None, None)
    long = direction > 0

    if tp1 is None:
        for j in range(n):
            if long:
                if low[j] <= stop:
                    return ResolveOutcome(True, -1.0, j, None)
                if high[j] >= target:
                    return ResolveOutcome(True, win_r, j, None)
            else:
                if high[j] >= stop:
                    return ResolveOutcome(True, -1.0, j, None)
                if low[j] <= target:
                    return ResolveOutcome(True, win_r, j, None)
        if force_close_at_end:
            r = direction * (close[n - 1] - entry) / sd
            return ResolveOutcome(True, float(r), n - 1, None)
        return ResolveOutcome(False, None, None, None)

    # Scale-out (TP1 / TP2) path.
    realized = 0.0
    remaining = 1.0
    tp1_done = False
    cur_stop = stop
    tp1_off = None
    for j in range(n):
        hit_stop = (low[j] <= cur_stop) if long else (high[j] >= cur_stop)
        if hit_stop:
            stop_r = direction * (cur_stop - entry) / sd   # -1R pre-TP1, ~0 at BE
            return ResolveOutcome(True, float(realized + remaining * stop_r), j, tp1_off)
        if not tp1_done:
            hit_tp1 = (high[j] >= tp1) if long else (low[j] <= tp1)
            if hit_tp1:
                realized += tp1_frac * tp1_r
                remaining -= tp1_frac
                tp1_done = True
                tp1_off = j
                if be_after_tp1:
                    cur_stop = entry
                continue   # don't also resolve TP2 on the TP1 bar (conservative)
        else:
            hit_tgt = (high[j] >= target) if long else (low[j] <= target)
            if hit_tgt:
                return ResolveOutcome(True, float(realized + remaining * win_r), j, tp1_off)
    if force_close_at_end:
        mark = direction * (close[n - 1] - entry) / sd
        return ResolveOutcome(True, float(realized + remaining * mark), n - 1, tp1_off)
    return ResolveOutcome(False, None, None, tp1_off)
