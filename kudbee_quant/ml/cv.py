"""Purged + embargoed walk-forward cross-validation for time-series meta-labeling.

Plain k-fold CV is a lie for trading data: shuffling lets a model train on the
future and "predict" the past, and adjacent samples share overlapping label
windows so a test point leaks into its neighbours' training rows. We use the
honest construction (López de Prado, *Advances in Financial ML*, ch. 7):

  * EXPANDING WINDOW, forward only — fold k trains on everything strictly BEFORE
    the test fold's start time and tests on the fold. A model is only ever judged
    on data that came after everything it learned from.
  * PURGE — drop training rows whose entry time falls inside the test fold's span
    (removes overlap when many symbols share timestamps / ties on the boundary).
  * EMBARGO — drop training rows within a small window AFTER the test fold, so
    serially-correlated labels just past the boundary can't leak. With a pure
    expanding window train is always before the test, so the embargo only trims
    the seam; it is kept for correctness and for when callers widen the window.

Symbols are pooled and ordered by a single global timeline, which is exactly what
we want: the embargo/purge are by TIME, so a BTC label can't leak into an ETH
training row that occurred at the same hour.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_TRAIN = 30   # below this a fold is uninformative; skip it


def purged_walk_forward_splits(meta: pd.DataFrame, n_splits: int = 5,
                               embargo_frac: float = 0.01):
    """Yield ``(train_idx, test_idx)`` positional index arrays (into meta's rows).

    Args:
        meta: must have an ``entry_time`` column (tz-aware datetime). Row order is
            preserved; the returned indices are positions into that order.
        n_splits: number of contiguous, forward-only test folds.
        embargo_frac: embargo length as a fraction of the total time span.
    """
    if "entry_time" not in meta.columns or len(meta) == 0:
        return
    t = pd.to_datetime(meta["entry_time"], utc=True)
    order = np.argsort(t.values, kind="stable")          # positions, time-ascending
    t_sorted = t.values[order]
    span = t_sorted[-1] - t_sorted[0]
    embargo = span * embargo_frac if span > np.timedelta64(0) else np.timedelta64(0)

    folds = np.array_split(np.arange(len(order)), n_splits)   # ranks within the order
    for fold in folds:
        if len(fold) == 0:
            continue
        test_pos = order[fold]                            # positions in meta
        test_start = t_sorted[fold[0]]
        test_end = t_sorted[fold[-1]]
        tt = t.values
        # Train = strictly before the test window, PURGED of any in-span overlap,
        # and EMBARGOED for the window just after the test fold.
        before = tt < test_start
        in_test_span = (tt >= test_start) & (tt <= test_end)
        in_embargo = (tt > test_end) & (tt <= test_end + embargo)
        train_mask = before & ~in_test_span & ~in_embargo
        train_pos = np.where(train_mask)[0]
        if len(train_pos) < MIN_TRAIN:
            continue
        yield train_pos, test_pos


def cross_val_oos(estimator_factory, X: pd.DataFrame, y: pd.Series,
                  meta: pd.DataFrame, n_splits: int = 5, embargo_frac: float = 0.01):
    """Out-of-sample predictions via purged walk-forward CV.

    ``estimator_factory`` is a zero-arg callable returning a fresh, unfitted
    sklearn-style classifier (``fit`` + ``predict_proba``); it must tolerate any
    NaNs in X (e.g. wrap an imputer in a Pipeline, or use HistGradientBoosting).

    Returns a DataFrame with one row per covered TEST sample — each predicted by a
    model that never saw it — with columns ``oos_prob, y_true, fold`` plus
    ``symbol, entry_time, mfe_r`` carried through from ``meta``. If a fold's train
    set is single-class, that fold falls back to a constant prediction (the train
    base rate) instead of crashing, so the OOS frame is always well-formed.
    """
    Xv = X.reset_index(drop=True)
    yv = pd.Series(np.asarray(y), name="y").reset_index(drop=True)
    rows = []
    for fold_i, (tr, te) in enumerate(purged_walk_forward_splits(meta, n_splits, embargo_frac)):
        ytr = yv.iloc[tr]
        if ytr.nunique() < 2:                       # single-class train -> baseline
            prob = np.full(len(te), float(ytr.mean()))
        else:
            est = estimator_factory()
            est.fit(Xv.iloc[tr], ytr)
            prob = est.predict_proba(Xv.iloc[te])[:, 1]
        block = pd.DataFrame({
            "oos_prob": prob,
            "y_true": yv.iloc[te].to_numpy(),
            "fold": fold_i,
            "symbol": meta["symbol"].to_numpy()[te] if "symbol" in meta else "?",
            "entry_time": pd.to_datetime(meta["entry_time"], utc=True).to_numpy()[te]
            if "entry_time" in meta else pd.NaT,
            "mfe_r": meta["mfe_r"].to_numpy()[te] if "mfe_r" in meta else np.nan,
        })
        rows.append(block)
    if not rows:
        return pd.DataFrame(columns=["oos_prob", "y_true", "fold", "symbol", "entry_time", "mfe_r"])
    return pd.concat(rows, ignore_index=True)
