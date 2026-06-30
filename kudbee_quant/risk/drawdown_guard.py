"""Drawdown circuit breaker — pause NEW entries after a rolling losing streak.

Tracks the rolling sum of realized R over the last ``window`` CLOSED trades. If that
sum drops below ``pause_threshold_r`` the breaker TRIPS (paused); it resumes only once
the rolling sum recovers to ``resume_threshold_r`` or better. The two thresholds give
hysteresis so it doesn't flap on the boundary.

State (the paused flag + last rolling R) persists to its OWN json file — NEVER
``data/journal.json`` (which is bot-owned and must not be mutated by this). The path
defaults to ``data/drawdown_state.json`` (gitignored).

FAIL-SAFE: with fewer than ``window`` closed trades the rolling sum is ``None`` and the
breaker stays ACTIVE (we don't pause trading on thin history). Persistence failures are
swallowed (a state-file hiccup must never crash a scan).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _resolve_time(p):
    return pd.to_datetime(getattr(p, "resolved_at", None) or getattr(p, "created_at", None),
                          utc=True)


def _last_closed_r(predictions, window: int):
    """The realized R of the last ``window`` closed trades (chronological), plus the
    total number of closed trades available."""
    closed = [p for p in (predictions or [])
              if getattr(p, "status", None) in ("hit", "miss")
              and getattr(p, "outcome_r", None) is not None]
    closed.sort(key=_resolve_time)
    rs = []
    for p in closed[-window:]:
        try:
            rs.append(float(p.outcome_r))
        except (TypeError, ValueError):
            continue
    return rs, len(closed)


class DrawdownGuard:
    def __init__(self, window: int = 10, pause_threshold_r: float = -3.0,
                 resume_threshold_r: float = -1.0,
                 state_path: str = "data/drawdown_state.json"):
        self.window = int(window)
        self.pause_threshold_r = float(pause_threshold_r)
        self.resume_threshold_r = float(resume_threshold_r)
        self.state_path = Path(state_path)
        self.rolling_r: float | None = None
        self.is_paused: bool = self._load_paused()

    def _load_paused(self) -> bool:
        try:
            return bool(json.loads(self.state_path.read_text()).get("paused", False))
        except Exception:
            return False

    def _save(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(
                {"paused": self.is_paused, "rolling_r": self.rolling_r}))
        except Exception:
            pass

    def update(self, predictions, persist: bool = True, on_state_change=None) -> bool:
        """Recompute rolling R from the journal's closed trades, apply the pause/resume
        hysteresis, and return the (new) ``is_paused`` state. Persists the state file
        unless ``persist`` is False (a read-only preview must have no side effects).

        ``on_state_change(old_state, new_state, guard)`` (states ``"active"``/``"paused"``)
        is called once when the breaker FLIPS — the hook the circuit-breaker alert
        registers. It is wrapped fail-open so a notification can never break the scan."""
        was_paused = self.is_paused
        rs, _ = _last_closed_r(predictions, self.window)
        if len(rs) < self.window:
            # Thin history: stay active — don't trip on too few samples.
            self.rolling_r = None
            if persist:
                self._save()
            return self.is_paused
        self.rolling_r = float(sum(rs))
        if self.is_paused:
            if self.rolling_r >= self.resume_threshold_r:
                self.is_paused = False
        elif self.rolling_r < self.pause_threshold_r:
            self.is_paused = True
        if persist:
            self._save()
        if on_state_change is not None and self.is_paused != was_paused:
            try:
                on_state_change("paused" if was_paused else "active",
                                "paused" if self.is_paused else "active", self)
            except Exception:  # noqa: BLE001 — an alert must never break the scan
                pass
        return self.is_paused

    def status_message(self) -> str:
        if self.rolling_r is None:
            return (f"DrawdownGuard: ACTIVE (insufficient history; need {self.window} "
                    f"closed trades).")
        state = "PAUSED" if self.is_paused else "ACTIVE"
        return (f"DrawdownGuard: {state} — rolling {self.window}-trade R "
                f"{self.rolling_r:+.2f} (pause<{self.pause_threshold_r:+.1f}, "
                f"resume>={self.resume_threshold_r:+.1f}).")
