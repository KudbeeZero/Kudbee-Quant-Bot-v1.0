"""The meta-model: a secondary classifier that decides BET / NO-BET on a primary
signal, and the HONEST report of whether it actually helps.

Two models, always reported side by side:
  * Gradient-boosted trees (HistGradientBoostingClassifier) — handles NaNs and
    nonlinear factor interactions; the workhorse.
  * Logistic regression (imputed + scaled) — the interpretable baseline whose
    coefficients we always print, so the edge is never a black box.

Everything is scored OUT-OF-SAMPLE through the purged/embargoed walk-forward CV
(``cv.py``). The headline question is not "what AUC" but: *if we only took the
trades the meta-model is confident in (prob >= threshold), does the win-rate beat
the base rate, with a Wilson confidence interval that clears it?* If the CI lower
bound doesn't exceed the base rate, the meta-model has not earned its place — and
this module says so. No in-sample numbers are ever reported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..events.study import wilson_ci
from .cv import cross_val_oos
from .labels import make_features


def gbt_factory():
    """Fresh gradient-boosted-tree classifier (handles NaN features natively)."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=300,
        l2_regularization=1.0, min_samples_leaf=30, random_state=0,
    )


def logit_factory():
    """Fresh interpretable logistic baseline: median-impute -> scale -> logit."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("logit", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])


def _gated_stats(oos: pd.DataFrame, threshold: float, base_rate: float) -> dict:
    """Win-rate among trades the model would TAKE (prob >= threshold), with a
    Wilson CI and an honest 'beats the base rate?' flag."""
    take = oos[oos["oos_prob"] >= threshold]
    n_take = int(len(take))
    wins_take = int(take["y_true"].sum())
    total_wins = int(oos["y_true"].sum())
    if n_take == 0:
        return {"threshold": threshold, "n_take": 0, "precision": None,
                "ci_low": None, "ci_high": None, "recall": 0.0,
                "lift_vs_base": None, "beats_base": False}
    precision = wins_take / n_take
    lo, hi = wilson_ci(wins_take, n_take)
    return {
        "threshold": threshold,
        "n_take": n_take,
        "take_frac": round(n_take / len(oos), 3),
        "precision": round(precision, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        "recall": round(wins_take / total_wins, 4) if total_wins else 0.0,
        "lift_vs_base": round(precision - base_rate, 4),
        "beats_base": bool(lo > base_rate),   # CI lower bound clears the base rate
    }


def _expectancy_gate(oos: pd.DataFrame, thresholds) -> list:
    """The metric that matters: does gating on the meta-prob raise OUT-OF-SAMPLE
    R-EXPECTANCY above taking every trade? Uses realized R carried through CV."""
    if "realized_r" not in oos or oos["realized_r"].isna().all():
        return []
    r_all = oos["realized_r"].to_numpy(dtype=float)
    base_exp = float(r_all.mean())
    rng = np.random.default_rng(0)
    out = []
    for t in thresholds:
        take = oos[oos["oos_prob"] >= t]
        nt = int(len(take))
        if nt == 0:
            out.append({"threshold": t, "n_take": 0}); continue
        gated_exp = float(take["realized_r"].mean())
        # Permutation test: is selecting THESE nt trades better than selecting nt
        # trades at random? p = fraction of random picks that match/beat the model.
        rand = rng.choice(r_all, size=(3000, nt), replace=True).mean(axis=1)
        p_perm = float((rand >= gated_exp).mean())
        out.append({
            "threshold": t, "n_take": nt,
            "take_frac": round(nt / len(oos), 3),
            "gated_expectancy_r": round(gated_exp, 4),
            "base_expectancy_r": round(base_exp, 4),
            "lift_r": round(gated_exp - base_exp, 4),
            "p_perm": round(p_perm, 4),
            "significant": bool(p_perm < 0.05 and gated_exp > base_exp),
        })
    return out


def evaluate(X: pd.DataFrame, y: pd.Series, meta: pd.DataFrame,
             thresholds=(0.5, 0.6, 0.7), n_splits: int = 5,
             embargo_frac: float = 0.01) -> dict:
    """Out-of-sample evaluation of both models. Returns an honest report dict."""
    from sklearn.metrics import brier_score_loss, roc_auc_score

    base_rate = float(y.mean())
    report = {"n_trades": int(len(y)), "base_rate": round(base_rate, 4),
              "n_signal_bars": meta.attrs.get("n_signal_bars"),
              "models": {}}
    for name, factory in (("gbt", gbt_factory), ("logit", logit_factory)):
        oos = cross_val_oos(factory, X, y, meta, n_splits=n_splits, embargo_frac=embargo_frac)
        if len(oos) == 0 or oos["y_true"].nunique() < 2:
            report["models"][name] = {"error": "insufficient OOS data / single class"}
            continue
        auc = float(roc_auc_score(oos["y_true"], oos["oos_prob"]))
        brier = float(brier_score_loss(oos["y_true"], oos["oos_prob"]))
        gated = [_gated_stats(oos, t, base_rate) for t in thresholds]
        report["models"][name] = {
            "n_oos": int(len(oos)), "auc": round(auc, 4), "brier": round(brier, 4),
            "oos_base_rate": round(float(oos["y_true"].mean()), 4),
            "gated": gated,
            "expectancy_gate": _expectancy_gate(oos, thresholds),
        }
    report["logit_coefficients"] = logit_coefficients(X, y)
    return report


def logit_coefficients(X: pd.DataFrame, y: pd.Series, top: int = 15) -> list:
    """Standardized logistic coefficients (full-sample) for interpretability — the
    sign + magnitude of what predicts a winning trade. NOT an OOS claim; a lens."""
    if y.nunique() < 2:
        return []
    model = logit_factory()
    model.fit(X, y)
    coefs = model.named_steps["logit"].coef_[0]
    pairs = sorted(zip(X.columns, coefs), key=lambda kv: abs(kv[1]), reverse=True)
    return [{"feature": f, "coef": round(float(c), 4)} for f, c in pairs[:top]]


def fit_final(X: pd.DataFrame, y: pd.Series, model: str = "gbt"):
    """Fit a model on ALL labeled data for live use (gating future signals)."""
    est = gbt_factory() if model == "gbt" else logit_factory()
    est.fit(X, y)
    return est


def meta_prob_for_frame(model, df: pd.DataFrame, feature_columns: list | None = None) -> pd.Series:
    """P(win) per bar for a feature frame — the live gating input.

    ``make_features`` emits a VARIABLE column set (the killzone one-hots depend on
    which categories occur in the frame), so scoring by raw positional ``.to_numpy()``
    would silently misalign columns and return garbage probabilities. Passing the
    training ``feature_columns`` is therefore strongly recommended: we reindex to
    them (missing dummies → 0, the natural "category absent" value) so alignment is
    by NAME. Without them we fall back to positional order but verify the width
    matches the model, raising rather than emitting a plausible-but-wrong P(win)."""
    feats = make_features(df)
    if feature_columns is not None:
        feats = feats.reindex(columns=feature_columns, fill_value=0.0)
    expected = getattr(model, "n_features_in_", None)
    if expected is not None and feats.shape[1] != expected:
        raise ValueError(
            f"meta feature mismatch: frame has {feats.shape[1]} columns but the model "
            f"expects {expected}. Pass feature_columns=<training columns> to align by name.")
    proba = model.predict_proba(feats.to_numpy())
    classes = list(getattr(model, "classes_", [0, 1]))
    if proba.shape[1] > 1:
        prob = proba[:, classes.index(1)]           # normal 2-class: P(win)
    else:
        # Degenerate single-class model: P(win) is 1.0 iff that class IS the win
        # class, else 0.0 — never P(loss) mislabeled as P(win) (an IndexError before).
        prob = proba[:, 0] if classes[:1] == [1] else 1.0 - proba[:, 0]
    return pd.Series(prob, index=df.index, name="meta_prob")
