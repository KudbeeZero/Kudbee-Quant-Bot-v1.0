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

from ..backtest.bracket import bracket_excursions
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
              "in_macro_best", "in_silver_bullet"):
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


def make_labels(
    df: pd.DataFrame,
    signal: pd.Series,
    target_r: float = 3.0,
    stop_atr: float = 1.5,
    limit_retrace_atr: float | None = 0.25,
    max_bars: int = 24,
    entry_window: int = 6,
) -> pd.DataFrame:
    """Per-(filled)-trade label frame: entry_bar, label, mfe_r, mae_r, direction.

    label = 1 if the trade reached ``target_r`` (in R) before the 1R stop within
    ``max_bars`` — i.e. it would have been a winning bracket — else 0.
    """
    ex = bracket_excursions(df, signal, stop_atr=stop_atr, max_bars=max_bars,
                            limit_retrace_atr=limit_retrace_atr, entry_window=entry_window)
    if ex.empty:
        return pd.DataFrame(columns=["entry_bar", "label", "mfe_r", "mae_r", "direction"])
    ex = ex.copy()
    ex["label"] = (ex["mfe_r"] >= target_r).astype(int)
    return ex[["entry_bar", "label", "mfe_r", "mae_r", "direction"]]


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
