"""Machine-learning layer — META-LABELING and the honest CV that guards it.

The primary model (confluence_position) decides DIRECTION. This package adds a
SECONDARY model that decides BET / NO-BET: given the same causal features at the
moment a primary signal fires, predict whether the trade will reach its target
before its stop (López de Prado, *Advances in Financial ML*, ch. 3). It is the
honest way to raise win-% — measured out-of-sample with purge+embargo, never by
adding another indicator.

Modules:
  labels     — turn primary signals + bracket excursions into (features, label).
  cv         — purged + embargoed walk-forward CV (no look-ahead in time-series).
  meta_model — train/score the secondary classifier; report OOS metrics honestly.
"""
from .labels import build_dataset, make_features, make_labels

__all__ = ["build_dataset", "make_features", "make_labels"]
