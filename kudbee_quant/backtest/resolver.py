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
    tp2_offset: int | None = None       # index where TP2 banked (tiered exits)
    runner_r: float | None = None        # R contributed by the runner remainder
                                         # (set once the trade is in the runner phase)


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
    stop_to_tp1: bool = False,
    tp2: float | None = None,
    tp2_r: float | None = None,
    tp2_frac: float = 0.0,
    trailing_atr: float | None = None,
    atr_at_entry: float | None = None,
    mae_giveup: tuple | None = None,
    time_decay: tuple | None = None,
    runner_trail_atr: float | None = None,
    runner_floor_r: float = 1.0,
    runner_max_bars: int | None = None,
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
        stop_to_tp1: when ``be_after_tp1`` is also set, move the post-TP1 stop to the
            ``tp1`` PRICE instead of breakeven (``entry``) — locks in the TP1 R on
            the runner instead of merely avoiding a loss on it. Default-off
            (breakeven, the original/live behaviour, is unchanged).
        tp2, tp2_r, tp2_frac: optional SECOND scale-out leg between TP1 and the final
            ``target`` — after TP1 banks, take a further ``tp2_frac`` of the (original)
            position at ``tp2`` (worth ``tp2_r`` R), and ride the remainder to
            ``target``. This is the three-leg "bank most at TP1, trim again, let a
            runner ride" management (e.g. 75% at TP1 / 10% at TP2 / 15% at target).
            Requires ``tp1`` to be set; default-off (``tp2`` None). The fractions are
            of the ORIGINAL position, so ``tp1_frac + tp2_frac`` must be < 1.0.

        Path-dependent exits (all optional, off by default; only on the non-TP1
        path — when every one is None the walk reduces to the exact original
        stop/target/mark-to-close behaviour):
        trailing_atr: chandelier trailing stop — trail at the extreme-since-entry
            minus ``trailing_atr * atr_at_entry``; the stop only ratchets in the
            favorable direction. Requires ``atr_at_entry``. The trail extreme uses
            only bars BEFORE the current one (no same-bar look-ahead).
        mae_giveup: ``(k_bars, adverse_r, mfe_max_r)`` — if by bar ``k_bars`` the
            trade's max adverse excursion is at least ``adverse_r`` (in R) AND its
            max favorable excursion is still below ``mfe_max_r``, give up and exit
            at that bar's close ("it went red fast and never showed green").
        time_decay: ``(decay_bars, floor_r)`` — the target shrinks linearly from
            ``win_r`` toward ``floor_r`` over ``decay_bars`` bars (harvest stale
            trades instead of waiting for a full target that won't come).

    Returns a :class:`ResolveOutcome`.
    """
    n = len(high)
    if n == 0:
        return ResolveOutcome(False, None, None, None)
    long = direction > 0

    if tp1 is None:
        use_path = trailing_atr is not None or mae_giveup is not None or time_decay is not None
        if not use_path:
            # Fast path — identical to the original all-or-nothing resolution.
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

        # Enriched path: trailing stop / MAE give-up / time-decay target.
        cur_stop = stop
        extreme = entry          # best price seen so far (prior bars only)
        mfe = 0.0
        mae = 0.0
        trail_dist = (trailing_atr * atr_at_entry) if (trailing_atr and atr_at_entry) else None
        for j in range(n):
            # Trail off PRIOR bars' extreme (conservative; set at loop end).
            if trail_dist is not None:
                trail_level = extreme - direction * trail_dist
                cur_stop = max(cur_stop, trail_level) if long else min(cur_stop, trail_level)
            # 1) stop (possibly trailed) — conservative, checked first.
            if (low[j] <= cur_stop) if long else (high[j] >= cur_stop):
                return ResolveOutcome(True, float(direction * (cur_stop - entry) / sd), j, None)
            # 2) MAE give-up.
            if mae_giveup is not None:
                k_bars, adverse_r, mfe_max_r = mae_giveup
                if (j + 1) >= k_bars and mae <= -abs(adverse_r) and mfe < mfe_max_r:
                    return ResolveOutcome(True, float(direction * (close[j] - entry) / sd), j, None)
            # 3) target (possibly decaying).
            cur_win_r = win_r
            if time_decay is not None:
                decay_bars, floor_r = time_decay
                frac = min(1.0, (j + 1) / max(1, decay_bars))
                cur_win_r = max(floor_r, win_r - (win_r - floor_r) * frac)
            tgt = entry + direction * sd * cur_win_r
            if (high[j] >= tgt) if long else (low[j] <= tgt):
                return ResolveOutcome(True, float(cur_win_r), j, None)
            # update excursions + trailing extreme with THIS bar (for next bar).
            fav = (high[j] - entry) / sd if long else (entry - low[j]) / sd
            adv = (low[j] - entry) / sd if long else (entry - high[j]) / sd
            mfe = max(mfe, fav)
            mae = min(mae, adv)
            extreme = max(extreme, high[j]) if long else min(extreme, low[j])
        if force_close_at_end:
            r = direction * (close[n - 1] - entry) / sd
            return ResolveOutcome(True, float(r), n - 1, None)
        return ResolveOutcome(False, None, None, None)

    # Scale-out path: TARGET ONE (tp1) -> optional TARGET TWO (tp2) -> final target,
    # with an optional TRAILING RUNNER on the remainder after the last scale-out.
    # At most ONE level resolves per bar (conservative: bank, then `continue`).
    has_tp2 = tp2 is not None
    realized = 0.0
    remaining = 1.0
    tp1_done = False
    tp2_done = not has_tp2     # if no second leg, treat it as already satisfied
    cur_stop = stop
    tp1_off = None
    tp2_off = None
    extreme = entry           # best price seen so far (prior bars only) — for the trail
    runner_trailing = runner_trail_atr is not None and atr_at_entry is not None
    floor_price = entry + direction * runner_floor_r * sd   # 1R-profit floor for the runner
    runner_start = None       # bar index at which the runner phase began

    def _in_runner() -> bool:
        return tp1_done and tp2_done

    for j in range(n):
        # Runner phase: ratchet the stop up to the trail (off prior-bar extreme),
        # never retreating below the 1R floor; honour the runner time cap.
        if runner_trailing and _in_runner():
            trail_level = extreme - direction * runner_trail_atr * atr_at_entry
            desired = max(floor_price, trail_level) if long else min(floor_price, trail_level)
            cur_stop = max(cur_stop, desired) if long else min(cur_stop, desired)
            if runner_max_bars is not None and runner_start is not None and (j - runner_start) >= runner_max_bars:
                mark_r = direction * (close[j] - entry) / sd
                return ResolveOutcome(True, float(realized + remaining * mark_r), j,
                                      tp1_off, tp2_off, remaining * mark_r)

        hit_stop = (low[j] <= cur_stop) if long else (high[j] >= cur_stop)
        if hit_stop:
            stop_r = direction * (cur_stop - entry) / sd   # -1R pre-TP1, ~0 at BE, >=floor in runner
            runner_r = remaining * stop_r if _in_runner() else None
            return ResolveOutcome(True, float(realized + remaining * stop_r), j, tp1_off, tp2_off, runner_r)
        if not tp1_done:
            hit_tp1 = (high[j] >= tp1) if long else (low[j] <= tp1)
            if hit_tp1:
                realized += tp1_frac * tp1_r
                remaining -= tp1_frac
                tp1_done = True
                tp1_off = j
                if be_after_tp1:
                    cur_stop = tp1 if stop_to_tp1 else entry
                if _in_runner():        # no TP2 leg -> runner begins right after TP1
                    runner_start = j
                    if runner_trailing:
                        cur_stop = max(cur_stop, floor_price) if long else min(cur_stop, floor_price)
                extreme = max(extreme, high[j]) if long else min(extreme, low[j])
                continue   # don't also resolve a later leg on the TP1 bar (conservative)
        elif not tp2_done:
            hit_tp2 = (high[j] >= tp2) if long else (low[j] <= tp2)
            if hit_tp2:
                realized += tp2_frac * tp2_r
                remaining -= tp2_frac
                tp2_done = True
                tp2_off = j
                runner_start = j        # runner begins now
                if runner_trailing:     # move the stop to the 1R floor immediately
                    cur_stop = max(cur_stop, floor_price) if long else min(cur_stop, floor_price)
                extreme = max(extreme, high[j]) if long else min(extreme, low[j])
                continue   # ride the remainder (runner) on later bars
        else:
            # Runner phase: the final target still caps the upside on either path.
            hit_tgt = (high[j] >= target) if long else (low[j] <= target)
            if hit_tgt:
                runner_r = remaining * win_r
                return ResolveOutcome(True, float(realized + runner_r), j, tp1_off, tp2_off, runner_r)
        extreme = max(extreme, high[j]) if long else min(extreme, low[j])
    if force_close_at_end:
        mark = direction * (close[n - 1] - entry) / sd
        runner_r = remaining * mark if _in_runner() else None
        return ResolveOutcome(True, float(realized + remaining * mark), n - 1, tp1_off, tp2_off, runner_r)
    return ResolveOutcome(False, None, None, tp1_off, tp2_off, None)
