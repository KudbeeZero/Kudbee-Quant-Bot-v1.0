"""Tests for the run heartbeat / scheduler-gap detector. No network, no real
clock — a fixed `now` and an in-tmp heartbeat file drive the coverage + gap math."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kudbee_quant.notifications.heartbeat import (
    health_from_history, health_line, load_health, record_run,
)

NOW = datetime(2026, 6, 22, 15, 30, tzinfo=timezone.utc)


def _hours_back(n, *, step_min=60):
    """n timestamps ending ~now, spaced step_min apart (most recent = ~now)."""
    return [(NOW - timedelta(minutes=step_min * i)).isoformat() for i in range(n)]


def test_cold_start_has_no_line():
    h = health_from_history([], now=NOW)
    assert h["last_run"] is None and h["stale"] is True
    assert health_line(h) is None


def test_full_coverage_is_healthy():
    h = health_from_history(_hours_back(24), now=NOW)
    assert h["runs_24h"] == 24 and h["drop_pct"] == 0.0 and not h["stale"]
    line = health_line(h)
    assert line.startswith("⏱ Runs:") and "24/24h covered" in line


def test_distinct_hours_not_inflated_by_dense_retries():
    # 6 runs all within the SAME clock-hour (15:00-15:25) count as ONE covered hour
    base = NOW.replace(minute=25)
    dense = [(base - timedelta(minutes=5 * i)).isoformat() for i in range(6)]
    h = health_from_history(dense, now=NOW)
    assert h["runs_24h"] == 1


def test_dropped_runs_flag_warning():
    # only 9 of the last 24 hours had a run -> 62% dropped -> warn + deploy hint
    h = health_from_history(_hours_back(9), now=NOW)
    assert h["runs_24h"] == 9
    assert round(h["drop_pct"], 2) == round(1 - 9 / 24, 2)
    line = health_line(h)
    assert line.startswith("⚠️ Scheduler gap")
    assert "9/24h covered" in line and "dropped" in line
    assert "external trigger" in line


def test_stale_gap_warns_even_with_recent_coverage():
    # every run is >=3h old -> latest run 3h ago -> stale, even though the
    # earlier part of the day was covered
    hist = [(NOW - timedelta(hours=3) - timedelta(minutes=60 * i)).isoformat()
            for i in range(24)]
    h = health_from_history(hist, now=NOW)
    assert h["gap_min"] >= 175 and h["stale"] is True
    assert health_line(h).startswith("⚠️ Scheduler gap")


def test_gap_formatting_minutes_and_hours():
    recent = health_from_history([(NOW - timedelta(minutes=8)).isoformat()], now=NOW)
    assert "8m" in health_line(recent)
    old = health_from_history([(NOW - timedelta(hours=3, minutes=10)).isoformat()], now=NOW)
    assert "3h10m" in health_line(old)


def test_record_run_persists_and_trims(tmp_path):
    p = tmp_path / "hb.json"
    # first run: cold start, file created
    record_run(path=p, now=NOW - timedelta(hours=1))
    assert p.exists()
    # second run an hour later: gap reflects the PREVIOUS run (~60m)
    h = record_run(path=p, now=NOW)
    assert h["last_run"] is not None
    assert 55 <= h["gap_min"] <= 65
    # read-only load sees both stamps -> 2 covered hours
    assert load_health(path=p, now=NOW)["runs_24h"] == 2


def test_record_run_missing_file_is_cold(tmp_path):
    h = record_run(path=tmp_path / "nope.json", now=NOW)
    assert h["last_run"] is None        # nothing existed before this run


def test_summary_includes_health_line_when_passed():
    from kudbee_quant.notifications.notify import format_summary
    report = {"portfolio": {"total_open": 0, "total_unrealized_r": 0.0}, "trades": []}
    health = health_from_history(_hours_back(9), now=NOW)   # dropping
    out = format_summary(report, schedule_health=health)
    assert "Scheduler gap" in out
    # absent health -> no line, back-compat
    assert "Scheduler" not in format_summary(report)
