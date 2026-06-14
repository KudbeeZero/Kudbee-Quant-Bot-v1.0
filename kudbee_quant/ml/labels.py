"""Meta-labeling dataset construction: (features at entry) -> (will this trade win?).

The label answers the meta-question precisely: *for a primary signal that actually
got a fill, did the trade reach its target (``target_r``) before the 1R stop?* We
read that straight off ``bracket_excursions`` (which already computes per-trade MFE
in R and now reports the ``entry_bar``), so the label is grounded in the SAME
execution the strategy trades — limit-retrace fills included.

Features are pulled at the ENTRY BAR only, from the causal ``build_levels`` frame +
the confluence votes/score. Everything here is trailing-only (lookahead-audited
elsewhere via ``scenarios/audit.py``), so a model trained on it is tradeable.

Honest caveats baked in:
  * Selection bias: by default we label only signals that FILLED (limit retrace),
    because that is what we trade. ``build_dataset`` reports the fill rate so the
    bias is visible; pass ``limit_retrace_atr=None`` for a market-entry control.
  * No target leakage: features at bar t use only data up to t; the label uses the
    forward path, which is the supervised target — never a feature.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..backtest.resolver import resolve_bracket
from ..confluence.stack import confluence_score, factor_votes


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer a causal, numeric feature frame aligned to ``df`` (one row/bar).

    Built defensively: only columns actually present in ``df`` (from build_levels)
    are used, so it works across assets/timeframes with slightly different feature
    availability. Ratios are normalised by ATR/price to be scale-free across coins.
    """
    f = pd.DataFrame(index=df.index)
    votes = factor_votes(df)
    for c in votes.columns:                      # the 8-10 confluence votes
        f[c] = votes[c]
    scored = confluence_score(df)
    for c in ("net_score", "strength", "confluence_pct", "direction"):
        f[c] = scored[c]

    atr = df["atr"].replace(0, np.nan)
    def have(*cols):
        return all(c in df.columns for c in cols)

    if have("close"):
        f["atr_pct"] = (df["atr"] / df["close"]).replace([np.inf, -np.inf], np.nan)
    if have("close", "ema_50"):
        f["ext_ema50_atr"] = (df["close"] - df["ema_50"]) / atr
    if have("ema_50", "ema_800"):
        f["ema_sep_atr"] = (df["ema_50"] - df["ema_800"]) / atr
    if have("ema_13", "ema_50"):
        f["ema_fast_atr"] = (df["ema_13"] - df["ema_50"]) / atr
    for c in ("ema_cloud_pos", "pd_pos", "rsi", "bos_dir", "structure_dir",
              "sweep_bias", "pct_adr_used", "pct_awr_used", "dist_daily_open_atr",
              "dist_weekly_open_atr", "ny_hour", "day_of_week", "in_overlap",
              "in_macro_best", "in_silver_bullet",
              # Opt-in taker-delta features (present only when ENABLE_TAKER_DELTA
              # built the frame; absent -> silently skipped, frame unchanged).
              "delta_pct", "delta_z", "cvd_session_pct", "cvd_roll_pct", "delta_div",
              # Opt-in volume-profile features (ENABLE_VOLUME_PROFILE).
              "dist_vp_poc_atr", "dist_vp_naked_poc_atr", "in_value_area", "near_vp_poc"):
        if c in df.columns:
            f[c] = pd.to_numeric(df[c], errors="coerce")
    if have("volume", "avg_volume"):
        f["rel_volume"] = df["volume"] / df["avg_volume"].replace(0, np.nan)
    if "is_climax" in df.columns:
        f["is_climax"] = df["is_climax"].astype(float)
    if "killzone" in df.columns:                 # one-hot the session killzone
        kz = pd.get_dummies(df["killzone"].astype(str), prefix="kz")
        f = pd.concat([f, kz.set_index(f.index)], axis=1)
    # Coerce any boolean flags/dummies to float so the whole frame is numeric.
    bool_cols = [c for c in f.columns if f[c].dtype == bool]
    if bool_cols:
        f[bool_cols] = f[bool_cols].astype(float)
    return f.replace([np.inf, -np.inf], np.nan)


def trade_outcomes(
    df: pd.DataFrame,
    signal: pd.Series,
    target_r: float = 3.0,
    stop_atr: float = 1.5,
    limit_retrace_atr: float | None = 0.25,
    max_bars: int = 24,
    entry_window: int = 6,
    fee_pct: float = 0.0004,
    trailing_atr: float | None = None,
    mae_giveup: tuple | None = None,
    time_decay: tuple | None = None,
) -> pd.DataFrame:
    """Per-trade REALIZED R for the validated bracket — the truth a meta-model
    should be judged against (expectancy), not just whether it tagged 3R.

    Same entry logic as ``bracket_excursions`` (limit-retrace fills), but resolves
    each trade through the shared resolver to get the realized R (net of a
    timeframe-aware maker cost), the MFE, and the MAE/adverse-move measured only
    while the position is open. Optional path-dependent exits (trailing/mae_giveup/
    time_decay) are forwarded so the realized R and the open-window MAE reflect the
    actual exit. Returns ``entry_bar, direction, realized_r, mfe_r, mae_r, adverse_pct``.
    """
    need = {"high", "low", "close", "atr"}
    if not need <= set(df.columns):
        raise ValueError(f"trade_outcomes needs {sorted(need)}")
    close = df["close"].to_numpy(); high = df["high"].to_numpy()
    low = df["low"].to_numpy(); atr = df["atr"].to_numpy()
    sig = pd.Series(signal, index=df.index).fillna(0.0).to_numpy()
    n = len(df)
    rows = []
    busy = -1
    for t in range(n - 1):
        if sig[t] == 0 or t <= busy:
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
        target = entry + direction * sd * target_r
        end = min(entry_bar + max_bars, n - 1)
        hs, ls, cs = high[entry_bar + 1:end + 1], low[entry_bar + 1:end + 1], close[entry_bar + 1:end + 1]
        out = resolve_bracket(direction, entry, stop, target, sd, target_r, hs, ls, cs,
                              force_close_at_end=True, atr_at_entry=atr[t],
                              trailing_atr=trailing_atr, mae_giveup=mae_giveup,
                              time_decay=time_decay)
        raw_r = out.outcome_r if out.outcome_r is not None else 0.0
        cost = fee_pct * entry / sd
        # MFE / MAE in R, measured ONLY while the position is open (up to the exit
        # bar) — adverse moves after the trade closes are irrelevant to risk, and
        # adverse_pct (what drives perp liquidation) must reflect the live window.
        k = (out.exit_offset + 1) if out.exit_offset is not None else len(hs)
        if k > 0:
            hk, lk = hs[:k], ls[:k]
            fav = (hk - entry) / sd if direction > 0 else (entry - lk) / sd
            adv = (lk - entry) / sd if direction > 0 else (hk - entry) / sd
            mfe = float(np.max(fav))
            mae = float(np.min(adv))           # <= 0
        else:
            mfe = mae = 0.0
        adverse_pct = abs(mae) * sd / entry    # |MAE in R| * (1R as % of entry)
        rows.append({"entry_bar": int(entry_bar), "direction": direction,
                     "realized_r": float(raw_r - cost), "mfe_r": mfe,
                     "mae_r": mae, "adverse_pct": float(adverse_pct)})
        busy = entry_bar + 1 + (out.exit_offset or 0)
    return pd.DataFrame(rows)


def make_labels(
    df: pd.DataFrame,
    signal: pd.Series,
    target_r: float = 3.0,
    stop_atr: float = 1.5,
    limit_retrace_atr: float | None = 0.25,
    max_bars: int = 24,
    entry_window: int = 6,
    fee_pct: float = 0.0004,
) -> pd.DataFrame:
    """Per-(filled)-trade label frame: entry_bar, label, realized_r, mfe_r, direction.

    label = 1 if the trade was PROFITABLE (realized R > 0, net of cost). This ties
    the meta-model directly to expectancy — "should we have taken this trade?" —
    rather than the harder, rarer "did it tag the full target" question.
    """
    out = trade_outcomes(df, signal, target_r=target_r, stop_atr=stop_atr,
                         limit_retrace_atr=limit_retrace_atr, max_bars=max_bars,
                         entry_window=entry_window, fee_pct=fee_pct)
    if out.empty:
        return pd.DataFrame(columns=["entry_bar", "label", "realized_r", "mfe_r", "direction"])
    out["label"] = (out["realized_r"] > 0).astype(int)
    return out[["entry_bar", "label", "realized_r", "mfe_r", "direction"]]


def build_dataset(
    frames: dict[str, pd.DataFrame],
    signal_fn,
    target_r: float = 3.0,
    **label_kw,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Assemble a pooled meta-labeling dataset across symbols.

    Args:
        frames: {symbol: build_levels(df)} feature frames.
        signal_fn: df -> primary signal Series ({-1,0,+1}); e.g.
            ``lambda d: confluence_position(d, min_pct=0.5, trend_align=True)``.

    Returns (X, y, meta) where meta carries symbol + entry timestamp + direction +
    mfe_r (for purged time-series CV and diagnostics). Index is a clean RangeIndex.
    """
    X_parts, y_parts, meta_parts = [], [], []
    n_signal_bars = n_trades = 0
    for sym, df in frames.items():
        sig = signal_fn(df)
        n_signal_bars += int((pd.Series(sig, index=df.index).fillna(0) != 0).sum())
        labels = make_labels(df, sig, target_r=target_r, **label_kw)
        if labels.empty:
            continue
        n_trades += len(labels)
        feats = make_features(df)
        rows = labels["entry_bar"].to_numpy()
        Xs = feats.iloc[rows].reset_index(drop=True)
        ts = (df["timestamp"].iloc[rows].reset_index(drop=True)
              if "timestamp" in df.columns else pd.Series(rows))
        meta = pd.DataFrame({"symbol": sym, "entry_time": pd.to_datetime(ts, utc=True, errors="coerce"),
                             "direction": labels["direction"].to_numpy(),
                             "realized_r": labels["realized_r"].to_numpy(),
                             "mfe_r": labels["mfe_r"].to_numpy()})
        X_parts.append(Xs)
        y_parts.append(labels["label"].reset_index(drop=True))
        meta_parts.append(meta)
    if not X_parts:
        return pd.DataFrame(), pd.Series(dtype=int), pd.DataFrame()
    X = pd.concat(X_parts, ignore_index=True)
    y = pd.concat(y_parts, ignore_index=True).astype(int)
    meta = pd.concat(meta_parts, ignore_index=True)
    # n_signal_bars counts every bar a primary signal was active (clusters
    # included); n_trades counts non-overlapping bracket trades that actually got
    # a limit-retrace fill. Their ratio is NOT a clean fill-rate — kept separately
    # so we never overclaim. (A true fill-rate needs entry-attempt accounting.)
    meta.attrs["n_signal_bars"] = n_signal_bars
    meta.attrs["n_trades"] = n_trades
    return X, y, meta
