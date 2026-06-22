"""Run heartbeat + scheduler-gap detector.

The problem this solves: GitHub Actions' `schedule:` cron is best-effort and
silently DROPS a large fraction of scheduled runs (observed ~70% on this repo).
When a run is dropped no scan happens and no Telegram message is sent — so the
owner can't tell the difference between "nothing to report" and "the platform
skipped us." This module gives an HONEST answer: every owner-scan stamps a
heartbeat, and the summary reports how many of the last 24 hours actually had a
run vs. were blind, plus how long since the last one.

It does NOT change trading. It's pure observability: ``record_run`` is called
once per hourly scan (writes ``data/heartbeat.json``); ``load_health`` is a
read-only computation the Telegram summary uses to append one status line.

``data/heartbeat.json`` is bot-written (like the journal) — never hand-edit it.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HEARTBEAT_PATH = Path("data/heartbeat.json")
_KEEP = 300                 # ~12 days of hourly stamps; trims unbounded growth
_STALE_AFTER_MIN = 75.0     # >1h+slack since last run => we're currently blind
EXPECTED_PER_DAY = 24       # the scan is hourly; 24 hours should each have a run


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_history(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    hist = data.get("history") if isinstance(data, dict) else None
    return [str(x) for x in hist] if isinstance(hist, list) else []


def _parse(ts: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def health_from_history(history: list[str], *, now: datetime | None = None) -> dict:
    """Compute run-health from a list of ISO timestamps (no IO).

    ``runs_24h`` counts DISTINCT clock-hours in the last 24h that had >=1 run —
    i.e. "hours we had eyes on the market" — so denser within-hour retries don't
    inflate it. ``drop_pct`` is the fraction of those 24 hours that were blind.
    """
    now = now or _utcnow()
    stamps = sorted(d for d in (_parse(t) for t in history) if d is not None)
    if not stamps:
        return {"last_run": None, "gap_min": None, "runs_24h": 0,
                "expected_24h": EXPECTED_PER_DAY, "drop_pct": None, "stale": True}
    last = stamps[-1]
    gap_min = max(0.0, (now - last).total_seconds() / 60.0)
    cutoff = now - timedelta(hours=24)
    hours_covered = {s.replace(minute=0, second=0, microsecond=0)
                     for s in stamps if s >= cutoff}
    runs_24h = len(hours_covered)
    drop_pct = max(0.0, 1.0 - runs_24h / EXPECTED_PER_DAY)
    return {"last_run": last.isoformat(), "gap_min": gap_min, "runs_24h": runs_24h,
            "expected_24h": EXPECTED_PER_DAY, "drop_pct": drop_pct,
            "stale": gap_min > _STALE_AFTER_MIN}


def load_health(*, path: Path | None = None, now: datetime | None = None) -> dict:
    """Read-only run-health from the heartbeat file (safe if it doesn't exist)."""
    return health_from_history(_load_history(path or HEARTBEAT_PATH), now=now)


def record_run(*, path: Path | None = None, now: datetime | None = None) -> dict:
    """Append `now` to the heartbeat history, trim, save, and return the health
    computed BEFORE this run was recorded (so 'gap since last run' reflects the
    real elapsed drop). Best-effort: a write failure returns health and moves on."""
    path = path or HEARTBEAT_PATH
    now = now or _utcnow()
    history = _load_history(path)
    health = health_from_history(history, now=now)   # gap vs the PREVIOUS run
    history.append(now.isoformat())
    history = history[-_KEEP:]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"history": history}, indent=0))
    except OSError:
        pass
    return health


def _fmt_gap(mins: float | None) -> str:
    if mins is None:
        return "—"
    if mins < 90:
        return f"{mins:.0f}m"
    h, m = divmod(int(round(mins)), 60)
    return f"{h}h{m:02d}m"


def health_line(health: dict | None) -> str | None:
    """One Telegram line summarizing scheduler health, or None on a cold start.

    Healthy:  ``⏱ Runs: last 8m ago • 22/24h covered``
    Dropping: ``⚠️ Scheduler gap 3h10m • only 9/24h covered (62% dropped) — deploy the external trigger``
    """
    if not health or health.get("last_run") is None:
        return None
    covered = health.get("runs_24h", 0)
    exp = health.get("expected_24h", EXPECTED_PER_DAY)
    gap = _fmt_gap(health.get("gap_min"))
    drop = health.get("drop_pct") or 0.0
    bad = health.get("stale") or drop >= 0.25
    if bad:
        tail = " — deploy the external trigger (cloudflare/trade-bot-cron)" if drop >= 0.25 else ""
        return (f"⚠️ Scheduler gap {gap} • only {covered}/{exp}h covered "
                f"({drop*100:.0f}% dropped){tail}")
    return f"⏱ Runs: last {gap} ago • {covered}/{exp}h covered"
