"""Candidate edge registry for the overnight research harness.

Each candidate is ONE hypothesis for lifting the validated strategy's expectancy
(see docs/MEMORY.md §1). The harness (overnight_research.py) tests each one
honestly against the SHIPPING baseline — pooled across the top-10 majors with a
split-half robustness check — and records the verdict so a dead end is never
re-tested (the project's honesty contract, docs/PHILOSOPHY.md).

A candidate is a callable:

    candidate(df, scored, base_sig) -> (signal, size, overrides)

      df       : feature frame from build_levels (atr, ema_*, volume, swings, …)
      scored   : confluence_score(df) (net_score, strength, direction, pct, …)
      base_sig : the SHIPPING signal — confluence_position(min_pct=0.5,
                 trend_align=True). Most candidates GATE this (keep entries only
                 where a condition holds) or change EXECUTION (stop/target/retrace).

      signal   : {-1,0,+1} entries to test (usually base_sig masked to a subset)
      size     : per-trade size in [0,1], or None for full size
      overrides: dict of bracket_backtest kwargs to override (execution variants)

DESIGN NOTE — why these buckets: the project has proven REPEATEDLY that adding
price-derived *confluence factors* does not help (the 10-factor set is saturated;
Order Blocks, macro, BOS/CHoCH, funding, RSI-divergence, MTF agreement all
diluted the edge — docs/MEMORY.md §2). What HAS moved the needle is EXECUTION,
ENTRY TIMING, and REGIME SELECTION. So every candidate here lives in one of:
volatility-regime gating, dynamic execution, momentum/pullback structure, volume
participation, or trade-management — never "one more indicator vote".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kudbee_quant.confluence.stack import confluence_position

# --- small helpers -----------------------------------------------------------


def _gate(base_sig: pd.Series, mask: pd.Series) -> pd.Series:
    """Keep the baseline entries only where ``mask`` is True; else flat."""
    mask = pd.Series(mask, index=base_sig.index).fillna(False)
    return base_sig.where(mask, 0.0).astype(float)


def _dir_gate(base_sig: pd.Series, long_ok, short_ok) -> pd.Series:
    """Keep longs where ``long_ok`` and shorts where ``short_ok`` (direction-
    conditional filters). Both masks are aligned to base_sig's index."""
    long_ok = pd.Series(long_ok, index=base_sig.index).fillna(False)
    short_ok = pd.Series(short_ok, index=base_sig.index).fillna(False)
    keep = ((base_sig > 0) & long_ok) | ((base_sig < 0) & short_ok)
    return base_sig.where(keep, 0.0).astype(float)


def _atr_pct(df: pd.DataFrame) -> pd.Series:
    """Realized-volatility proxy: ATR as a fraction of price."""
    return (df["atr"] / df["close"]).replace([np.inf, -np.inf], np.nan)


def _rolling_pctrank(s: pd.Series, window: int) -> pd.Series:
    """Percentile rank of the latest value within its trailing ``window`` (0..1).

    Causal (uses only the trailing window, current bar inclusive) so it is safe
    to gate live trades on.
    """
    return s.rolling(window, min_periods=max(20, window // 5)).apply(
        lambda x: (x[-1] >= x).mean(), raw=True
    )


# --- candidates --------------------------------------------------------------
# Each returns (signal, size, overrides). Keep each to ~10 readable lines.


def c_vol_regime_mid(df, scored, base_sig):
    """Trade only in the MIDDLE volatility band (skip dead-calm chop AND
    vol-shock/news bars). Both tails are where retrace-entries get whipsawed or
    never fill. mask = 20th..80th percentile of ATR% over a trailing 200 bars."""
    r = _rolling_pctrank(_atr_pct(df), 200)
    return _gate(base_sig, (r >= 0.20) & (r <= 0.80)), None, {}


def c_skip_vol_shock(df, scored, base_sig):
    """Skip entries right after a volatility SHOCK (top-decile ATR% over 200
    bars) — these are usually the news spike, the worst place to fade a retrace."""
    r = _rolling_pctrank(_atr_pct(df), 200)
    return _gate(base_sig, r < 0.90), None, {}


def c_vol_contraction(df, scored, base_sig):
    """Volatility-contraction (NR7-style) entries: take the signal only when the
    last bar's range is the narrowest of the trailing 7 — squeeze before
    expansion, the classic low-risk entry location."""
    rng = df["high"] - df["low"]
    nr = rng <= rng.rolling(7, min_periods=7).min() * 1.05
    return _gate(base_sig, nr), None, {}


def c_no_climax_entry(df, scored, base_sig):
    """Skip signals whose trigger bar is a CLIMAX-volume candle (is_climax) —
    don't fade/enter into an exhaustion spike (catching a knife)."""
    mask = ~df["is_climax"].fillna(False).astype(bool)
    return _gate(base_sig, mask), None, {}


def c_relvol_participation(df, scored, base_sig):
    """Require above-average participation at the signal: volume >= 1.2x the
    20-bar average volume. Tests whether 'real' volume confirms the move."""
    mask = df["volume"] >= 1.2 * df["avg_volume"]
    return _gate(base_sig, mask), None, {}


def c_relvol_quiet(df, scored, base_sig):
    """The OPPOSITE of participation: only quiet bars (volume < avg). A/B partner
    to c_relvol_participation — one of the two should lose; that's the point."""
    mask = df["volume"] < df["avg_volume"]
    return _gate(base_sig, mask), None, {}


def c_pullback_in_trend(df, scored, base_sig):
    """Buy-the-dip / sell-the-rip WITH the trend: longs only when price has
    pulled back below the fast EMA while the trend (ema_13>ema_50) is still up;
    mirror for shorts. Improves the entry LOCATION of a with-trend signal."""
    up = (df["ema_13"] > df["ema_50"]) & (df["close"] < df["ema_13"])
    dn = (df["ema_13"] < df["ema_50"]) & (df["close"] > df["ema_13"])
    long_ok = (base_sig > 0) & up
    short_ok = (base_sig < 0) & dn
    return _gate(base_sig, long_ok | short_ok), None, {}


def c_clean_trend(df, scored, base_sig):
    """Only trade when the trend is CLEAN, not tangled: the 50/800-EMA gap is at
    least 1 ATR (the EMAs are clearly separated, a real trend not a chop)."""
    mask = (df["ema_50"] - df["ema_800"]).abs() >= df["atr"]
    return _gate(base_sig, mask), None, {}


def c_skip_overextended(df, scored, base_sig):
    """Skip entries when price is already stretched > 2.5 ATR from the 50-EMA —
    chasing an over-extended move into mean-reversion risk."""
    ext = (df["close"] - df["ema_50"]).abs() / df["atr"]
    return _gate(base_sig, ext <= 2.5), None, {}


def c_deeper_retrace(df, scored, base_sig):
    """EXECUTION variant: enter on a DEEPER 0.5-ATR retrace (vs 0.25). Better
    price + tighter risk, at the cost of fewer fills — the project's edge has
    lived in execution before, so probe the retrace-depth lever directly."""
    return base_sig, None, {"limit_retrace_atr": 0.5}


def c_shallow_retrace(df, scored, base_sig):
    """EXECUTION variant: shallower 0.12-ATR retrace — fills more often at a
    worse price. A/B partner to c_deeper_retrace."""
    return base_sig, None, {"limit_retrace_atr": 0.12}


def c_fast_timestop(df, scored, base_sig):
    """EXECUTION variant: cut dead trades faster (12-bar time stop vs 24). If the
    move hasn't worked in half a day, the thesis is likely wrong."""
    return base_sig, None, {"max_bars": 12}


def c_slow_timestop(df, scored, base_sig):
    """EXECUTION variant: give winners more room (48-bar time stop). A/B partner
    to c_fast_timestop — let the 3R target have time to fill."""
    return base_sig, None, {"max_bars": 48}


def c_highvol_bigtarget(df, scored, base_sig):
    """REGIME x EXECUTION: in the high-volatility regime (top-40% ATR%), aim for
    a bigger 4R target — volatile regimes can run further. Gated to high-vol
    bars so the comparison isolates the regime."""
    r = _rolling_pctrank(_atr_pct(df), 200)
    return _gate(base_sig, r >= 0.60), None, {"target_r": 4.0}


def c_lowvol_smalltarget(df, scored, base_sig):
    """REGIME x EXECUTION: in the low-volatility regime (bottom-40% ATR%), take a
    nearer 2R target — quiet regimes don't travel as far. A/B partner above."""
    r = _rolling_pctrank(_atr_pct(df), 200)
    return _gate(base_sig, r <= 0.40), None, {"target_r": 2.0}


def c_voltarget_size(df, scored, base_sig):
    """SIZING: volatility-targeted position size — risk-normalise across regimes
    by sizing DOWN when ATR% is high and UP (capped at 1) when it's low, so each
    trade contributes more equal risk. Tests if vol-targeting lifts per-trade R."""
    r = _rolling_pctrank(_atr_pct(df), 200).fillna(0.5)
    size = (1.0 - 0.5 * r).clip(0.25, 1.0)  # high vol -> 0.5, low vol -> 1.0
    return base_sig, size, {}


def c_size_by_confluence(df, scored, base_sig):
    """SIZING: scale size by confluence strength (more agreement -> bigger),
    floor 0.3 at the 50% threshold ramping to 1.0 at full agreement. Tests
    whether the confluence score carries CONVICTION info beyond direction."""
    pct = scored["confluence_pct"].clip(0.5, 1.0)
    size = (0.3 + 0.7 * (pct - 0.5) / 0.5).clip(0.3, 1.0)
    return base_sig, size, {}


def c_variance_ratio_trend(df, scored, base_sig):
    """REGIME GATE (the most theory-grounded one): a Lo-MacKinlay variance ratio
    on log returns. VR>1 means returns are positively autocorrelated (trending);
    VR<1 means mean-reverting (chop). The whole strategy is a with-trend 3R
    payoff, so take it only in the trending regime (VR>1)."""
    ret = np.log(df["close"]).diff()
    q = 8
    sum_q = ret.rolling(q).sum()
    vr = sum_q.rolling(96).var() / (q * ret.rolling(96).var())
    return _gate(base_sig, vr > 1.0), None, {}


def c_clean_trend_stack(df, scored, base_sig):
    """REGIME GATE: only trade when the 13/50/800-EMA stack has been correctly
    ordered for the last 10 bars AND the 13/50 gap is WIDENING (a clean,
    separating trend, not a braided/tangling one). Richer than c_clean_trend."""
    up = (df["ema_13"] > df["ema_50"]) & (df["ema_50"] > df["ema_800"])
    dn = (df["ema_13"] < df["ema_50"]) & (df["ema_50"] < df["ema_800"])
    stacked = up.rolling(10, min_periods=10).min().astype(bool) | dn.rolling(10, min_periods=10).min().astype(bool)
    gap = (df["ema_13"] - df["ema_50"]).abs() / df["atr"]
    widening = gap > gap.shift(10)
    return _gate(base_sig, stacked & widening), None, {}


def c_round_number_entry(df, scored, base_sig):
    """ENTRY LOCATION: only take the trade when price is near a psychological
    round number (within 0.4 ATR of round_below/round_above) — liquidity pools
    cluster there, where retrace fills are cleaner."""
    near = (
        ((df["close"] - df["round_below"]).abs() <= 0.4 * df["atr"])
        | ((df["round_above"] - df["close"]).abs() <= 0.4 * df["atr"])
    )
    return _gate(base_sig, near), None, {}


def c_coil_rng_pct(df, scored, base_sig):
    """Coil: take the signal only when the PRIOR bar's range was in the bottom
    quintile of its trailing-50 distribution — a volatility contraction right
    before the entry (agent idea; rolling-percentile variant of NR7)."""
    rng = df["high"] - df["low"]
    coil = _rolling_pctrank(rng, 50).shift(1) <= 0.20
    return _gate(base_sig, coil), None, {}


def c_atr_band_3085(df, scored, base_sig):
    """ATR-percentile band 0.30..0.85 over a trailing 500 bars — a different
    (wider, higher) band than c_vol_regime_mid, to map the regime sweet spot."""
    r = _rolling_pctrank(_atr_pct(df), 500)
    return _gate(base_sig, (r >= 0.30) & (r <= 0.85)), None, {}


def c_ret_autocorr_pos(df, scored, base_sig):
    """Momentum regime: take the (with-trend) signal only when 1-bar return
    autocorrelation over the last 48 bars is positive (trend-friendly tape)."""
    ret = df["close"].pct_change()
    ac = ret.rolling(48, min_periods=24).apply(lambda x: pd.Series(x).autocorr(lag=1), raw=False)
    return _gate(base_sig, ac > 0.0), None, {}


def c_climax_dir_veto(df, scored, base_sig):
    """Veto only climax bars that move WITH the trade direction (buying the top
    tick of an up-spike / shorting the bottom of a down-spike) — narrower than
    c_no_climax_entry, which vetoes every climax bar."""
    body_dir = np.sign(df["close"] - df["open"])
    bad = df["is_climax"].fillna(False).astype(bool) & (body_dir == np.sign(base_sig))
    return _gate(base_sig, ~bad), None, {}


def c_pullback_run2(df, scored, base_sig):
    """Stronger pullback gate: with-trend entry only after >=2 consecutive
    counter-trend closes into the trend (longs after 2 down-closes in an uptrend,
    mirror for shorts) — a deeper dip than c_pullback_in_trend."""
    down2 = (df["close"] < df["close"].shift(1)) & (df["close"].shift(1) < df["close"].shift(2))
    up2 = (df["close"] > df["close"].shift(1)) & (df["close"].shift(1) > df["close"].shift(2))
    up_tr = df["ema_50"] > df["ema_800"]
    long_ok = (base_sig > 0) & up_tr & down2
    short_ok = (base_sig < 0) & (~up_tr) & up2
    return _gate(base_sig, long_ok | short_ok), None, {}


def c_wider_stop(df, scored, base_sig):
    """Execution geometry: 2.0-ATR stop keeping the 3R target (=6-ATR target).
    Probes whether more breathing room beyond MEMORY §10's 1.5-ATR helps."""
    return base_sig, None, {"stop_atr": 2.0}


def c_tighter_stop(df, scored, base_sig):
    """Execution geometry: 1.0-ATR stop with the 3R target (tighter risk, more
    stop-outs). A/B partner to c_wider_stop."""
    return base_sig, None, {"stop_atr": 1.0}


def c_entry_window_long(df, scored, base_sig):
    """Execution: give the limit retrace more time to fill (12 bars vs 6) — more
    fills, possibly at staler context."""
    return base_sig, None, {"entry_window": 12}


def c_entry_window_short(df, scored, base_sig):
    """Execution: demand a fast fill (3-bar window) — only retraces that come
    quickly, A/B partner to c_entry_window_long."""
    return base_sig, None, {"entry_window": 3}


def c_target_5r(df, scored, base_sig):
    """Execution: a 5R target everywhere (let winners run further). Tests the
    fat right tail directly, against the 3R default."""
    return base_sig, None, {"target_r": 5.0}


def c_vol_dryup_coil(df, scored, base_sig):
    """Accumulation tell: a range coil (prior bar narrow) AND a volume dry-up
    (prior bar volume in the bottom quartile of trailing-50) — quiet-then-go."""
    rng = df["high"] - df["low"]
    coil = _rolling_pctrank(rng, 50).shift(1) <= 0.25
    dry = _rolling_pctrank(df["volume"], 50).shift(1) <= 0.25
    return _gate(base_sig, coil & dry), None, {}


def c_inside_bar(df, scored, base_sig):
    """Inside-bar compression: take the signal only when the prior bar was an
    inside bar (high<prev-high AND low>prev-low) — a coiled-spring entry."""
    inside = (df["high"].shift(1) < df["high"].shift(2)) & (df["low"].shift(1) > df["low"].shift(2))
    return _gate(base_sig, inside), None, {}


def c_conf_60(df, scored, base_sig):
    """Stricter confluence threshold: require >=60% agreement (vs the 50%
    baseline) — a subset of the baseline entries with higher conviction."""
    return confluence_position(df, min_pct=0.60, trend_align=True), None, {}


def c_trend_strong_sep(df, scored, base_sig):
    """Strong-trend gate: 13/800-EMA separation >= 2 ATR — only the most clearly
    trending tape (a stronger cut than clean_trend's 50/800 >= 1 ATR)."""
    mask = (df["ema_13"] - df["ema_800"]).abs() >= 2.0 * df["atr"]
    return _gate(base_sig, mask), None, {}


def c_two_bar_momentum(df, scored, base_sig):
    """Momentum confirmation: take longs only when the last two closes both rose
    (mirror for shorts) — enter into demonstrated, not hoped-for, momentum."""
    up2 = (df["close"] > df["close"].shift(1)) & (df["close"].shift(1) > df["close"].shift(2))
    dn2 = (df["close"] < df["close"].shift(1)) & (df["close"].shift(1) < df["close"].shift(2))
    return _gate(base_sig, ((base_sig > 0) & up2) | ((base_sig < 0) & dn2)), None, {}


def c_range_expansion(df, scored, base_sig):
    """Expansion (opposite of coil): take the signal only when the trigger bar's
    range is > 1.5x the trailing-20 average range — momentum already releasing."""
    rng = df["high"] - df["low"]
    mask = rng > 1.5 * rng.rolling(20, min_periods=10).mean()
    return _gate(base_sig, mask), None, {}


def c_ret_percentile_self(df, scored, base_sig):
    """Relative-strength-of-self: long only when the symbol's 24-bar return is in
    the upper 30% of its trailing-500 history (hot vs its own normal); mirror for
    shorts. Normalises momentum per-symbol without a hard ROC threshold."""
    roc = df["close"].pct_change(24)
    rank = _rolling_pctrank(roc, 500)
    return _dir_gate(base_sig, rank >= 0.70, rank <= 0.30), None, {}


def c_near_high_recovery(df, scored, base_sig):
    """Trade near the recent extreme, not deep in a local drawdown: long only
    within 5% of the 50-bar high, short only within 5% of the 50-bar low."""
    hi = df["high"].rolling(50, min_periods=25).max()
    lo = df["low"].rolling(50, min_periods=25).min()
    long_ok = (hi - df["close"]) / df["close"] <= 0.05
    short_ok = (df["close"] - lo) / df["close"] <= 0.05
    return _dir_gate(base_sig, long_ok, short_ok), None, {}


def c_run_streak_gate(df, scored, base_sig):
    """Moderate-run timing: require 2-5 consecutive same-direction closes before
    entry (established drive, not yet exhausted)."""
    up = (df["close"] > df["close"].shift(1)).astype(int)
    su = (up.groupby((up != up.shift()).cumsum()).cumcount() + 1).where(up == 1, 0)
    dn = (df["close"] < df["close"].shift(1)).astype(int)
    sd = (dn.groupby((dn != dn.shift()).cumsum()).cumcount() + 1).where(dn == 1, 0)
    return _dir_gate(base_sig, su.between(2, 5), sd.between(2, 5)), None, {}


def c_jump_continuation(df, scored, base_sig):
    """Impulse-continuation (crypto's 'gap'): after a big bar (TR > 1.8 ATR) in
    the trade direction, enter only if the next close takes out the impulse
    bar's extreme — selects the continuation branch, drops the blowoff fade."""
    bar = df["close"] - df["open"]
    big = (df["high"] - df["low"]) > 1.8 * df["atr"]
    long_ok = big.shift(1) & (bar.shift(1) > 0) & (df["close"] > df["high"].shift(1))
    short_ok = big.shift(1) & (bar.shift(1) < 0) & (df["close"] < df["low"].shift(1))
    return _dir_gate(base_sig, long_ok, short_ok), None, {}


def c_atr_vs_tr_compression(df, scored, base_sig):
    """Contraction timing: enter only when the latest true range is <=0.7x the
    smoothed ATR — fill the maker retrace inside a quiet bar that precedes
    expansion, with the stop sized off the (higher) recent vol."""
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - df["close"].shift()).abs(),
                    (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    return _gate(base_sig, (tr / df["atr"]) <= 0.7), None, {}


def c_ema50_slope_accel(df, scored, base_sig):
    """Trend VELOCITY, not just level: require the ATR-normalised ema_50 slope to
    be aligned AND accelerating (second difference same sign) — active, steepening
    trend rather than flat-above-EMA chop."""
    slope = df["ema_50"].diff()
    accel = slope.diff()
    norm = slope / df["atr"]
    long_ok = (norm > 0.02) & (accel > 0)
    short_ok = (norm < -0.02) & (accel < 0)
    return _dir_gate(base_sig, long_ok, short_ok), None, {}


def c_structural_stop_swing(df, scored, base_sig):
    """Structural stop placement: take the trade only when the 1.5-ATR stop lands
    just beyond the nearest swing (within 0.5 ATR) — structure must break before
    the stop trips, so noise wicks get absorbed."""
    entry = df["close"]
    sl = entry - 1.5 * df["atr"]
    ss = entry + 1.5 * df["atr"]
    buf = 0.5 * df["atr"]
    long_ok = (df["swing_low"] > sl) & (df["swing_low"] < entry) & ((df["swing_low"] - sl) <= buf)
    short_ok = (df["swing_high"] < ss) & (df["swing_high"] > entry) & ((ss - df["swing_high"]) <= buf)
    return _dir_gate(base_sig, long_ok, short_ok), None, {}


def c_contraction_reclaim(df, scored, base_sig):
    """Effort-vs-result: among retrace entries, keep only those after a 2-bar
    range contraction (counter-push exhausting) AND an immediate reclaim of the
    prior close (demand returns) — a spring/absorption tell."""
    rng = df["high"] - df["low"]
    falling = (rng < rng.shift(1)) & (rng.shift(1) < rng.shift(2))
    long_ok = falling & (df["close"] > df["close"].shift(1))
    short_ok = falling & (df["close"] < df["close"].shift(1))
    return _dir_gate(base_sig, long_ok, short_ok), None, {}


def c_exit_trail_3atr(df, scored, base_sig):
    """EXECUTION (path-dependent): chandelier trailing stop at 3 ATR below the
    high-since-entry, instead of the fixed 3R target. Tests whether trailing
    captures the fat-tail runner (MEMORY §17 frontier)."""
    return base_sig, None, {"trailing_atr": 3.0}


def c_exit_mae_giveup(df, scored, base_sig):
    """EXECUTION: MAE 'give-up' — if by bar 6 the trade is >=0.8R offside and has
    not shown >=0.5R favorable, exit at market rather than wait for the 1R stop."""
    return base_sig, None, {"mae_giveup": (6, 0.8, 0.5)}


def c_exit_time_decay(df, scored, base_sig):
    """EXECUTION: time-decay target from 3R down to 1.5R over the 24-bar window —
    harvest stale trades instead of marking out at the time stop."""
    return base_sig, None, {"time_decay": (24, 1.5)}


def c_bb_band_reject(df, scored, base_sig):
    """KudbeeX's READ, mechanized for testing (docs/MEMORY §20): a STANDALONE
    Bollinger-band rejection reversal. Short when a shooting-star / 'reverse
    hammer' (long UPPER wick, small body, ~no lower wick) prints AT or ABOVE the
    upper band; long on the mirror (hammer at/below the lower band). BOLL(26,2),
    matching his chart. This is NOT a gate on the confluence signal — it is his
    setup as its own hypothesis, measured against the shipping baseline so we learn
    whether the discretionary read has a mechanical edge or is pure reasoning."""
    c = df["close"]
    mid = c.rolling(26, min_periods=26).mean()
    sd = c.rolling(26, min_periods=26).std()
    upper, lower = mid + 2 * sd, mid - 2 * sd
    o, h, l = df["open"], df["high"], df["low"]
    body = (c - o).abs()
    upper_wick = h - pd.concat([o, c], axis=1).max(axis=1)
    lower_wick = pd.concat([o, c], axis=1).min(axis=1) - l
    star = (h >= upper) & (upper_wick >= 1.5 * body) & (lower_wick <= 0.5 * body)
    hammer = (l <= lower) & (lower_wick >= 1.5 * body) & (upper_wick <= 0.5 * body)
    sig = pd.Series(0.0, index=df.index)
    sig[star] = -1.0
    sig[hammer] = 1.0
    return sig, None, {}


def c_exit_showme(df, scored, base_sig):
    """KudbeeX 'fast-fail' theory (MEMORY §21): keep the 1.5-ATR stop but EXIT
    EARLY if the trade hasn't shown >=0.5R in our favor by bar 3 ('you should know
    quickly if it's working'). Measured win: structurally smaller losses + ~15%
    lower variance (risk-efficiency for leverage), at ~flat expectancy."""
    return base_sig, None, {"mae_giveup": (3, 0.0, 0.5)}


def c_exit_tight_showme(df, scored, base_sig):
    """KudbeeX fast-fail, aggressive: tighter 1.0-ATR stop + give up if not +0.3R
    by bar 2. Highest expectancy of the variants but a wider worst-case (gap risk
    on the tight stop) — the A/B partner to c_exit_showme."""
    return base_sig, None, {"stop_atr": 1.0, "mae_giveup": (2, 0.0, 0.3)}


# --- Traders-Reality M-level candidates --------------------------------------
# These read the M-level grid / day-color / session levels that build_levels emits
# (kudbee_quant.levels.MLEVEL_COLUMNS). They are candidate-LOCAL: nothing here is a
# live vote (the live stack's factor_votes is untouched). The dynamic-target ones
# pass a per-bar absolute `target_price` (supported by bracket_backtest); the harness
# slices it for the split-half tests.

import warnings  # noqa: E402

_MLEVELS = ["mlevel_m0", "mlevel_m1", "mlevel_m2", "mlevel_m3", "mlevel_m4", "mlevel_m5"]


def _augmented_signal(df, scored, extra_vote, min_pct=0.50):
    """Re-derive the SHIPPING signal (min_pct=0.5 + trend_align) with one EXTRA
    candidate-local vote folded into the confluence score (n_factors -> n+1). This
    is the honest 'add a vote' — it shifts the threshold like a real factor would."""
    net = scored["net_score"] + extra_vote
    n = scored["n_factors"] + 1
    direction = np.sign(net)
    gate = (net.abs() / n) >= min_pct
    if "ema_800" in df:                                  # trend_align (price vs 800-EMA)
        gate = gate & (direction == np.sign(df["close"] - df["ema_800"]))
    return pd.Series(np.where(gate, direction, 0.0), index=df.index).astype(float)


def _dir_extreme(df, sig, cols):
    """Per-bar nearest level among ``cols`` in the trade direction: the smallest
    level ABOVE close for longs, the largest BELOW close for shorts (NaN if none)."""
    close = df["close"].to_numpy()
    M = df[cols].to_numpy()
    with warnings.catch_warnings():                      # all-NaN row -> NaN (gated out)
        warnings.simplefilter("ignore", RuntimeWarning)
        up = np.nanmin(np.where(M > close[:, None], M, np.nan), axis=1)
        dn = np.nanmax(np.where(M < close[:, None], M, np.nan), axis=1)
    s = pd.Series(sig, index=df.index).fillna(0.0).to_numpy()
    return pd.Series(np.where(s > 0, up, np.where(s < 0, dn, np.nan)), index=df.index)


def c_mlevel_reject(df, scored, base_sig):
    """VOTE (candidate-local): an M-level REJECTION. Low pierces within 0.3 ATR of
    any M-level and the bar CLOSES back above it -> +1 (support held); the mirror
    (high tags a level, close below) -> -1. Folded into the confluence score and
    re-thresholded like the shipping signal. The TRUE level-rejection vote (the live
    v_pivot is direction-only)."""
    atr = df["atr"].to_numpy()
    close, low, high = df["close"].to_numpy(), df["low"].to_numpy(), df["high"].to_numpy()
    M = df[_MLEVELS].to_numpy()
    tol = (0.3 * atr)[:, None]
    bull = ((np.abs(low[:, None] - M) <= tol) & (close[:, None] > M)).any(axis=1)
    bear = ((np.abs(high[:, None] - M) <= tol) & (close[:, None] < M)).any(axis=1)
    vote = pd.Series(np.where(bull, 1.0, np.where(bear, -1.0, 0.0)), index=df.index)
    return _augmented_signal(df, scored, vote), None, {}


def c_mlevel_magnet(df, scored, base_sig):
    """EXECUTION: replace the fixed 3R target with the NEAREST M-level in the trade
    direction (Tino's 'price returns to the levels'). All-or-nothing at the level
    (tp1 off); gated to bars where such a level exists ahead of price."""
    tgt = _dir_extreme(df, base_sig, _MLEVELS)
    return _gate(base_sig, tgt.notna()), None, {"target_price": tgt, "tp1_r": None}


def c_daycolor_target(df, scored, base_sig):
    """PROJECTION as target-mapper: on a RED prior day long->M3 / short->M1; on a
    GREEN day long->M4 / short->M2 (Tino's day-color range projection). Kept only
    when the projected level is ahead of price."""
    red = (df["prev_day_color"] < 0).to_numpy()
    s = pd.Series(base_sig, index=df.index).fillna(0.0).to_numpy()
    long_t = np.where(red, df["mlevel_m3"], df["mlevel_m4"])
    short_t = np.where(red, df["mlevel_m1"], df["mlevel_m2"])
    tgt = pd.Series(np.where(s > 0, long_t, np.where(s < 0, short_t, np.nan)), index=df.index)
    close = df["close"]
    ahead = ((pd.Series(s, index=df.index) > 0) & (tgt > close)) | \
            ((pd.Series(s, index=df.index) < 0) & (tgt < close))
    return _gate(base_sig, ahead), None, {"target_price": tgt.where(ahead), "tp1_r": None}


def c_daycolor_filter(df, scored, base_sig):
    """PROJECTION as a mean-reversion ENTRY FILTER: fade the extremes back toward the
    projected range. RED day -> favor shorts in the upper band (close>=M3), longs in
    the lower band (close<=M2); GREEN day -> inverse."""
    close = df["close"]
    upper, lower = close >= df["mlevel_m3"], close <= df["mlevel_m2"]
    red = df["prev_day_color"] < 0
    long_ok = (red & lower) | (~red & upper)
    short_ok = (red & upper) | (~red & lower)
    return _dir_gate(base_sig, long_ok, short_ok), None, {}


def c_brinks_window(df, scored, base_sig):
    """ENTRY TIMING: take entries ONLY inside the London-Brinks / NY-Brinks / overlap
    killzones (reuses the existing in_london_kz / in_ny_brinks / in_overlap flags)."""
    flags = [c for c in ("in_london_kz", "in_ny_brinks", "in_overlap") if c in df.columns]
    active = (df[flags].astype(bool).any(axis=1) if flags
              else pd.Series(True, index=df.index))
    return _gate(base_sig, active), None, {}


def c_session_return(df, scored, base_sig):
    """EXECUTION: target the nearest PRIOR-SESSION extreme (prior NY high/low or the
    Asian-range edge) in the trade direction, when it's within reach (<=4 ATR) —
    Tino's 'price revisits last session's extremes'. All-or-nothing at the level."""
    levels = ["prior_ny_high", "prior_ny_low", "asian_high", "asian_low"]
    have = [c for c in levels if c in df.columns]
    tgt = _dir_extreme(df, base_sig, have)
    keep = tgt.notna() & ((tgt - df["close"]).abs() <= 4.0 * df["atr"])
    return _gate(base_sig, keep), None, {"target_price": tgt.where(keep), "tp1_r": None}


# --- Weekly-cycle / BTMM candidates ------------------------------------------
# These read the weekly-cycle features build_levels emits (day_of_week, level_day,
# week_ib_high/low, consec_run_*). Candidate-local only; the live stack is untouched.


def c_monday_skip(df, scored, base_sig):
    """WEEKLY: take NO new entries on Monday (NY day). Tests the BTMM claim that
    Monday is an accumulation/trap day and its trades are net-negative."""
    return _gate(base_sig, df["day_of_week"] != 0), None, {}


def c_monday_fade(df, scored, base_sig):
    """WEEKLY: Monday only — fade the Monday low. Keep LONGS only when price sits in
    the lower third of the day's RUNNING range, and suppress fresh shorts; off Monday
    the baseline passes through unchanged."""
    is_mon = (df["day_of_week"] == 0).to_numpy()
    day_hi = df.groupby("ny_date")["high"].cummax()
    day_lo = df.groupby("ny_date")["low"].cummin()
    pos = (df["close"] - day_lo) / (day_hi - day_lo).replace(0, np.nan)
    s = pd.Series(base_sig, index=df.index).fillna(0.0)
    keep = (~is_mon) | ((s.to_numpy() > 0) & (pos.to_numpy() <= 1.0 / 3.0))
    return s.where(keep, 0.0).astype(float), None, {}


def c_midweek_reversal(df, scored, base_sig):
    """WEEKLY: on Tue/Wed keep only COUNTER-TREND entries (against the week-to-date
    direction = price vs the weekly open) — the midweek reversal of the early-week
    push — and give them more room (48-bar hold, 4R target)."""
    midweek = df["day_of_week"].isin([1, 2])
    week_dir = np.sign(df["close"] - df["weekly_open"])
    s = pd.Series(base_sig, index=df.index).fillna(0.0)
    counter = np.sign(s) == -week_dir
    return _gate(s, midweek & counter & (s != 0)), None, {"max_bars": 48, "target_r": 4.0}


def c_weekly_ib(df, scored, base_sig):
    """WEEKLY: the Mon+Tue range is the weekly initial-balance box. Fade rejections
    back INTO the box — pierced above week_ib_high but closed back inside -> short
    toward week_ib_low; pierced below and closed back inside -> long toward
    week_ib_high. Standalone signal; targets the opposite IB edge (Wed+ only)."""
    hi, lo, close = df["week_ib_high"], df["week_ib_low"], df["close"]
    short = (df["high"] > hi) & (close < hi)
    long_ = (df["low"] < lo) & (close > lo)
    sig = pd.Series(np.where(long_, 1.0, np.where(short, -1.0, 0.0)), index=df.index)
    tgt = pd.Series(np.where(sig > 0, hi, np.where(sig < 0, lo, np.nan)), index=df.index)
    ahead = ((sig > 0) & (tgt > close)) | ((sig < 0) & (tgt < close))
    return sig.where(ahead, 0.0), None, {"target_price": tgt.where(ahead), "tp1_r": None}


def c_level_count_3day(df, scored, base_sig):
    """WEEKLY/BTMM: take trend-continuation (the baseline) only on the aggressive MM
    'level days' — L1/L3 (Mon/Wed) at full size, L2 (Tue) de-weighted to half size,
    nothing on L4 (Thu/Fri) or weekends."""
    ld = df["level_day"]
    s = pd.Series(base_sig, index=df.index).fillna(0.0)
    sig = s.where(ld.isin([1, 2, 3]), 0.0)
    size = pd.Series(np.where(ld.to_numpy() == 2, 0.5, 1.0), index=df.index)
    return sig, size, {}


def c_three_push_stophunt(df, scored, base_sig):
    """BTMM 'three pushes + stop hunt': after >=3 consecutive same-direction closes,
    expect a stop-raid reversal — keep only entries AGAINST the run direction. Uses
    the completed-bar consec_run (no current-bar leak)."""
    primed = df["consec_run_len"] >= 3
    s = pd.Series(base_sig, index=df.index).fillna(0.0)
    against = np.sign(s) == -np.sign(df["consec_run_dir"])
    return _gate(base_sig, primed & against & (s != 0)), None, {}


# --- three_push deep-dive (the one §58 lead worth chasing) --------------------
# §58 found c_three_push_stophunt the only candidate with Δ>0 AND both halves +ve
# (Δ+0.144, but n=122≈floor, p=0.19). These probe whether a version clears the full
# luck-proof gate on more data (run -h_run/3x history): stronger exhaustion, a bigger
# sample without the trend-align shrink, killzone timing, and a quicker target.


def _push_against(df, base_sig, min_run):
    """base entries that FADE a same-direction run of length >= min_run."""
    s = pd.Series(base_sig, index=df.index).fillna(0.0)
    primed = df["consec_run_len"] >= min_run
    against = np.sign(s) == -np.sign(df["consec_run_dir"])
    return s, primed & against & (s != 0)


def c_three_push_4(df, scored, base_sig):
    """Deeper exhaustion: fade only after >=4 consecutive same-direction closes."""
    s, keep = _push_against(df, base_sig, 4)
    return _gate(s, keep), None, {}


def c_three_push_pure(df, scored, base_sig):
    """Bigger sample: fade a >=3 run using the raw confluence direction (>=50%) WITHOUT
    the trend-align gate that shrank the original to n=122 — the fade is inherently
    counter-trend, so trend_align was fighting it. Tests if the effect survives at n."""
    pct, direction = scored["confluence_pct"], scored["direction"]
    primed = df["consec_run_len"] >= 3
    fade = np.sign(direction) == -np.sign(df["consec_run_dir"])
    sig = np.where(primed & fade & (pct >= 0.5), direction, 0.0)
    return pd.Series(sig, index=df.index).astype(float), None, {}


def c_three_push_kz(df, scored, base_sig):
    """Combine the two §58 mild-positives: fade a >=3 run, but ONLY inside the
    London/NY-Brinks/overlap killzones (where stop-hunts cluster)."""
    s, keep = _push_against(df, base_sig, 3)
    flags = [c for c in ("in_london_kz", "in_ny_brinks", "in_overlap") if c in df.columns]
    active = (df[flags].astype(bool).any(axis=1) if flags else pd.Series(True, index=df.index))
    return _gate(s, keep & active), None, {}


def c_three_push_2r(df, scored, base_sig):
    """A reversal off a stop-hunt may not run a full 3R — fade a >=3 run with a
    nearer 2R target (test whether a quicker exit banks the edge more reliably)."""
    s, keep = _push_against(df, base_sig, 3)
    return _gate(s, keep), None, {"target_r": 2.0}


# Registry: name -> (callable, one-line description). The harness pulls names
# from data/overnight_queue.json; anything here that isn't queued/tested yet can
# be enqueued by the hourly loop (research agents append NEW ones over the night).
REGISTRY: dict[str, tuple] = {
    "vol_regime_mid": (c_vol_regime_mid, "Trade only the middle ATR%-percentile band (skip calm & shock)"),
    "skip_vol_shock": (c_skip_vol_shock, "Skip top-decile ATR% (news-shock) entries"),
    "vol_contraction": (c_vol_contraction, "NR7-style: enter only after a volatility squeeze"),
    "no_climax_entry": (c_no_climax_entry, "Skip climax-volume trigger bars (no knife-catching)"),
    "relvol_participation": (c_relvol_participation, "Require volume >= 1.2x avg at signal"),
    "relvol_quiet": (c_relvol_quiet, "A/B: only quiet (below-avg volume) entries"),
    "pullback_in_trend": (c_pullback_in_trend, "With-trend entries only after a pullback past the fast EMA"),
    "clean_trend": (c_clean_trend, "Only when 50/800-EMA gap >= 1 ATR (untangled trend)"),
    "skip_overextended": (c_skip_overextended, "Skip entries >2.5 ATR stretched from the 50-EMA"),
    "deeper_retrace": (c_deeper_retrace, "Execution: 0.5-ATR limit retrace (better price, fewer fills)"),
    "shallow_retrace": (c_shallow_retrace, "Execution: 0.12-ATR limit retrace (more fills, worse price)"),
    "fast_timestop": (c_fast_timestop, "Execution: 12-bar time stop (cut dead trades faster)"),
    "slow_timestop": (c_slow_timestop, "Execution: 48-bar time stop (more room for 3R)"),
    "highvol_bigtarget": (c_highvol_bigtarget, "Regime: high-vol bars -> 4R target"),
    "lowvol_smalltarget": (c_lowvol_smalltarget, "Regime: low-vol bars -> 2R target"),
    "voltarget_size": (c_voltarget_size, "Sizing: volatility-targeted (down in high vol)"),
    "size_by_confluence": (c_size_by_confluence, "Sizing: scale by confluence strength"),
    "round_number_entry": (c_round_number_entry, "Entry location: near psychological round numbers"),
    "variance_ratio_trend": (c_variance_ratio_trend, "Regime: Lo-MacKinlay variance ratio > 1 (trending only)"),
    "clean_trend_stack": (c_clean_trend_stack, "Regime: 10-bar monotonic EMA stack + widening gap"),
    "coil_rng_pct": (c_coil_rng_pct, "Coil: prior-bar range in bottom quintile of trailing-50"),
    "atr_band_3085": (c_atr_band_3085, "Regime: ATR%-percentile band 0.30..0.85 (wider band)"),
    "ret_autocorr_pos": (c_ret_autocorr_pos, "Regime: 48-bar return autocorrelation > 0"),
    "climax_dir_veto": (c_climax_dir_veto, "Veto only climax bars moving with the trade direction"),
    "pullback_run2": (c_pullback_run2, "With-trend entry after >=2 counter-trend closes"),
    "wider_stop": (c_wider_stop, "Execution: 2.0-ATR stop, 3R target"),
    "tighter_stop": (c_tighter_stop, "Execution: 1.0-ATR stop, 3R target"),
    "entry_window_long": (c_entry_window_long, "Execution: 12-bar limit-fill window"),
    "entry_window_short": (c_entry_window_short, "Execution: 3-bar limit-fill window"),
    "target_5r": (c_target_5r, "Execution: 5R target everywhere"),
    "vol_dryup_coil": (c_vol_dryup_coil, "Coil + volume dry-up (accumulation tell)"),
    "inside_bar": (c_inside_bar, "Prior bar is an inside bar (compression)"),
    "conf_60": (c_conf_60, "Stricter >=60% confluence threshold"),
    "trend_strong_sep": (c_trend_strong_sep, "Strong trend: 13/800-EMA gap >= 2 ATR"),
    "two_bar_momentum": (c_two_bar_momentum, "Two consecutive with-direction closes"),
    "range_expansion": (c_range_expansion, "Trigger-bar range > 1.5x trailing-20 avg"),
    "ret_percentile_self": (c_ret_percentile_self, "Own-momentum percentile (24-bar ROC vs trailing-500)"),
    "near_high_recovery": (c_near_high_recovery, "Within 5% of the 50-bar extreme (not in drawdown)"),
    "run_streak_gate": (c_run_streak_gate, "2-5 consecutive same-direction closes"),
    "jump_continuation": (c_jump_continuation, "Impulse bar (TR>1.8 ATR) + extreme takeout"),
    "atr_vs_tr_compression": (c_atr_vs_tr_compression, "Latest TR <= 0.7x smoothed ATR (contraction)"),
    "ema50_slope_accel": (c_ema50_slope_accel, "EMA50 slope aligned AND accelerating"),
    "structural_stop_swing": (c_structural_stop_swing, "1.5-ATR stop lands just beyond nearest swing"),
    "contraction_reclaim": (c_contraction_reclaim, "2-bar range contraction then prior-close reclaim"),
    "exit_trail_3atr": (c_exit_trail_3atr, "Execution: 3-ATR chandelier trailing stop"),
    "exit_mae_giveup": (c_exit_mae_giveup, "Execution: MAE give-up (0.8R offside by bar 6, no 0.5R fav)"),
    "exit_time_decay": (c_exit_time_decay, "Execution: target decays 3R->1.5R over 24 bars"),
    "bb_band_reject": (c_bb_band_reject, "KudbeeX read: shooting-star@upper / hammer@lower BB(26,2) reversal"),
    "exit_showme": (c_exit_showme, "KudbeeX fast-fail: exit if not +0.5R by bar 3 (cuts loss tail)"),
    "exit_tight_showme": (c_exit_tight_showme, "KudbeeX fast-fail: 1.0 stop + exit if not +0.3R by bar 2"),
    # Traders-Reality M-level system (level-rejection vote / level-magnet targets /
    # day-color projection / killzone timing / session-extreme targets).
    "mlevel_reject": (c_mlevel_reject, "TR: candidate-local M-level REJECTION vote (low/high tags level, closes back)"),
    "mlevel_magnet": (c_mlevel_magnet, "TR: target the nearest M-level in trade direction (price returns to levels)"),
    "daycolor_target": (c_daycolor_target, "TR: day-color projection as target (red->M3/M1, green->M4/M2)"),
    "daycolor_filter": (c_daycolor_filter, "TR: day-color mean-reversion filter (fade extremes toward range)"),
    "brinks_window": (c_brinks_window, "TR: entries only in London/NY-Brinks/overlap killzones"),
    "session_return": (c_session_return, "TR: target nearest prior-session/Asian extreme within 4 ATR"),
    # Weekly-cycle / BTMM (day-of-week, level day, weekly IB, run-count).
    "monday_skip": (c_monday_skip, "BTMM: no new entries on Monday (NY day)"),
    "monday_fade": (c_monday_fade, "BTMM: Monday only — longs in lower-third running range, suppress shorts"),
    "midweek_reversal": (c_midweek_reversal, "BTMM: Tue/Wed counter-trend reversal vs week-to-date, 48-bar/4R"),
    "weekly_ib": (c_weekly_ib, "BTMM: fade rejections back into the Mon+Tue IB box, target opposite edge"),
    "level_count_3day": (c_level_count_3day, "BTMM: continuation on L1/L3 days (Mon/Wed), half-size L2 (Tue)"),
    "three_push_stophunt": (c_three_push_stophunt, "BTMM: after >=3-run, fade the run (stop-hunt reversal)"),
    # three_push deep-dive (chasing the §58 lead on 3x history).
    "three_push_4": (c_three_push_4, "three_push: deeper exhaustion, fade only after >=4-run"),
    "three_push_pure": (c_three_push_pure, "three_push: fade >=3-run on raw confluence (no trend-align shrink)"),
    "three_push_kz": (c_three_push_kz, "three_push: fade >=3-run only inside killzones"),
    "three_push_2r": (c_three_push_2r, "three_push: fade >=3-run with a nearer 2R target"),
}
