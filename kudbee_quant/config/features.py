"""Experimental-signal feature flags — every new signal ships OFF by default.

The audit mandate (confluence/stack.py) is parsimony: the 10-vote confluence set
is saturated, and five extra votes were each REMOVED with walk-forward evidence.
So new signals (taker delta / CVD, volume profile, killzone gate, ...) are added
as *opt-in* features/filters that must EARN their place with out-of-sample
evidence before anyone flips them on. This module is the single place those
opt-ins live, so the default code path — and therefore live trading — is
byte-identical until a flag is set.

Env vars (all optional; every default is OFF / behaviour-preserving):
    ENABLE_TAKER_DELTA=false       (default: false)  bar delta + CVD + delta-div
    ENABLE_VOLUME_PROFILE=false    (default: false)  per-day POC / VAH / VAL / naked POC
    ENABLE_AI_CHART_REVIEW=false   (default: false)  dashboard AI chart-review endpoint

Read from the environment like ``config/runtime.py`` so a flag can be flipped per
process without touching code, and never silently turns a signal on.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

_TRUE = {"1", "true", "yes", "on"}


def _env_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    return default if raw is None else raw.strip().lower() in _TRUE


@dataclass(frozen=True)
class FeatureFlags:
    """Opt-in switches for experimental signals. All default to OFF."""

    enable_taker_delta: bool = False
    enable_volume_profile: bool = False
    enable_ai_chart_review: bool = False

    def as_dict(self) -> dict:
        return {"enable_taker_delta": self.enable_taker_delta,
                "enable_volume_profile": self.enable_volume_profile,
                "enable_ai_chart_review": self.enable_ai_chart_review}


def load_feature_flags(env: Mapping[str, str] | None = None) -> FeatureFlags:
    """Build :class:`FeatureFlags` from ``env`` (defaults to ``os.environ``).

    Fail-safe: anything not explicitly truthy stays OFF.
    """
    env = os.environ if env is None else env
    return FeatureFlags(
        enable_taker_delta=_env_bool(env, "ENABLE_TAKER_DELTA", False),
        enable_volume_profile=_env_bool(env, "ENABLE_VOLUME_PROFILE", False),
        enable_ai_chart_review=_env_bool(env, "ENABLE_AI_CHART_REVIEW", False),
    )
