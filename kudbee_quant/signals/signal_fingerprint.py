"""Signal fingerprint — per-bucket expectancy memory for a forward-looking gate.

A *fingerprint* is a coarse 5-dimensional key describing a signal:

  confluence_bucket — 0.50-0.60 / 0.60-0.70 / 0.70-0.80 / 0.80-1.00
  direction         — long / short
  session           — london / ny / asia / other   (UTC, aligned with SessionWindows)
  ema_stack         — bull_clean / bear_clean / mixed
  atr_regime        — low / medium / high

Any missing/unknown dimension collapses to ``"unknown"`` (it NEVER throws and never
drops a trade). :class:`SignalFingerprintDB` aggregates the realized R of CLOSED
trades by fingerprint, so the ``_fp`` experiment book can ask "in this exact bucket,
has the edge historically been negative?" and skip only buckets with a real,
sampled, losing record.

HONESTY / SCOPE NOTE: the trade journal only persists enough to recover THREE of the
five dimensions for a closed trade — the confluence bucket (from the ``setup`` tag),
the direction, and the session (from the timestamp). It does NOT persist ``ema_stack``
or ``atr_regime``, so the DB resolves those two to ``"unknown"`` for history. To keep
live signals and history on the SAME key (so the gate can actually match samples), the
live gate builds its fingerprint the same way — those two dims are ``"unknown"`` on
both sides. The 5-dim API is kept whole so the gate sharpens automatically if those
dims are ever persisted; today it keys effectively on confluence x direction x
session. No overclaiming.

SAFETY: ``MIN_SAMPLE`` (=5) — a bucket with fewer than 5 closed trades is NEVER
blocked (too little data to trust). Defaults (``min_expectancy=0.0``,
``min_win_rate=0.0``) make the gate a no-op until a bucket has >=5 samples AND a
losing (negative-expectancy) record.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

MIN_SAMPLE = 5

_PCT_RE = re.compile(r"_(\d+)pct")


# --- dimension labellers (each fail-soft to "unknown") ----------------------

def _session_bucket(hour: int) -> str:
    # Aligned with context.mm_cycle.SessionWindows (london 7-16, ny 13-21,
    # asian 23-7); the 13-16 overlap is folded into "ny" (NY checked first).
    if 13 <= hour < 21:
        return "ny"
    if 7 <= hour < 16:
        return "london"
    if hour >= 23 or hour < 7:
        return "asia"
    return "other"


def _confluence_bucket(pct) -> str:
    try:
        p = float(pct)
    except (TypeError, ValueError):
        return "unknown"
    if p != p:                      # NaN
        return "unknown"
    if p >= 0.80:
        return "0.80-1.00"
    if p >= 0.70:
        return "0.70-0.80"
    if p >= 0.60:
        return "0.60-0.70"
    if p >= 0.50:
        return "0.50-0.60"
    return "other"


def _direction_label(direction) -> str:
    try:
        d = float(direction)
    except (TypeError, ValueError):
        return "unknown"
    if d > 0:
        return "long"
    if d < 0:
        return "short"
    return "unknown"


def _session_label(timestamp) -> str:
    if timestamp is None:
        return "unknown"
    try:
        h = int(pd.to_datetime(timestamp, utc=True).hour)
    except (ValueError, TypeError):
        return "unknown"
    return _session_bucket(h)


def _ema_stack_label(ema_stack) -> str:
    return ema_stack if ema_stack in ("bull_clean", "bear_clean", "mixed") else "unknown"


def _atr_regime_label(atr_pct) -> str:
    """ATR as a fraction of price -> low (<1%) / medium (1-3%) / high (>=3%)."""
    if atr_pct is None:
        return "unknown"
    try:
        a = float(atr_pct)
    except (TypeError, ValueError):
        return "unknown"
    if a != a:
        return "unknown"
    if a < 0.01:
        return "low"
    if a < 0.03:
        return "medium"
    return "high"


# --- fingerprint --------------------------------------------------------------

@dataclass(frozen=True)
class Fingerprint:
    confluence_bucket: str
    direction: str
    session: str
    ema_stack: str
    atr_regime: str

    def key(self) -> tuple:
        return (self.confluence_bucket, self.direction, self.session,
                self.ema_stack, self.atr_regime)


def make_fingerprint(*, confluence_pct=None, direction=None, timestamp=None,
                     ema_stack=None, atr_pct=None) -> Fingerprint:
    """Build a :class:`Fingerprint` from whatever inputs are available; any missing
    dimension collapses to ``"unknown"``."""
    return Fingerprint(
        confluence_bucket=_confluence_bucket(confluence_pct),
        direction=_direction_label(direction),
        session=_session_label(timestamp),
        ema_stack=_ema_stack_label(ema_stack),
        atr_regime=_atr_regime_label(atr_pct),
    )


def _pct_from_setup(setup: str):
    m = _PCT_RE.search(setup or "")
    return int(m.group(1)) / 100.0 if m else None


def fingerprint_of_prediction(p) -> Fingerprint:
    """Reconstruct a fingerprint from a stored ``Prediction`` (recoverable dims
    only — ema_stack/atr_regime are not persisted, so they resolve to unknown)."""
    return make_fingerprint(
        confluence_pct=_pct_from_setup(getattr(p, "setup", "") or ""),
        direction=getattr(p, "direction", None),
        timestamp=getattr(p, "filled_at", None) or getattr(p, "created_at", None),
        ema_stack=None,
        atr_pct=None,
    )


@dataclass
class _Bucket:
    n: int = 0
    total_r: float = 0.0
    wins: int = 0


class SignalFingerprintDB:
    """Per-fingerprint expectancy / win-rate over CLOSED trades."""

    def __init__(self, buckets: dict | None = None):
        self._buckets: dict[tuple, _Bucket] = buckets or {}

    @classmethod
    def from_predictions(cls, predictions) -> "SignalFingerprintDB":
        buckets: dict[tuple, _Bucket] = {}
        for p in predictions or []:
            if getattr(p, "status", None) not in ("hit", "miss"):
                continue
            r = getattr(p, "outcome_r", None)
            if r is None:
                continue
            try:
                r = float(r)
            except (TypeError, ValueError):
                continue
            key = fingerprint_of_prediction(p).key()
            b = buckets.setdefault(key, _Bucket())
            b.n += 1
            b.total_r += r
            if r > 0:
                b.wins += 1
        return cls(buckets)

    def _b(self, fp: Fingerprint):
        return self._buckets.get(fp.key())

    def sample_size(self, fp: Fingerprint) -> int:
        b = self._b(fp)
        return b.n if b else 0

    def expectancy(self, fp: Fingerprint):
        b = self._b(fp)
        return (b.total_r / b.n) if b and b.n else None

    def win_rate(self, fp: Fingerprint):
        b = self._b(fp)
        return (b.wins / b.n) if b and b.n else None

    def should_skip(self, fp: Fingerprint, min_expectancy: float = 0.0,
                    min_win_rate: float = 0.0) -> bool:
        """``True`` = skip this signal. NEVER skip below ``MIN_SAMPLE``. A bucket is
        skipped only once it has >=MIN_SAMPLE closed trades AND its expectancy is
        below ``min_expectancy`` OR its win rate is below ``min_win_rate``."""
        if self.sample_size(fp) < MIN_SAMPLE:
            return False
        exp = self.expectancy(fp)
        wr = self.win_rate(fp)
        if exp is not None and exp < min_expectancy:
            return True
        if wr is not None and wr < min_win_rate:
            return True
        return False
