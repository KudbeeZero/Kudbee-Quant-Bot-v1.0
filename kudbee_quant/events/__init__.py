"""Conditional Event-Study Engine.

Turns Traders Reality teachings into measured conditional probabilities:
P(outcome | context), with confidence intervals, minimum-sample gates,
multiple-comparisons control, and out-of-sample checks. The model gets
"smarter" by accumulating base rates from real data and pruning buckets that
do not beat a null — not by believing harder. See docs/research/.
"""

from .detectors import detect_level_tests, detect_vector_events
from .features import build_features
from .recovery import recovery_curve
from .study import conditional_table, wilson_ci

__all__ = [
    "build_features",
    "detect_vector_events",
    "detect_level_tests",
    "recovery_curve",
    "conditional_table",
    "wilson_ci",
]
