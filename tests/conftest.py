"""Shared pytest fixtures."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _neutralize_event_gate(monkeypatch):
    """Keep the binary-event gate inert across the suite.

    ``paper_scan`` consults a wall-clock event calendar (``get_blocking_event`` /
    the Friday-close & Monday-open windows) before evaluating signals. Left live,
    that would make the existing ``paper_scan`` tests non-deterministic — they'd
    pass on a Tuesday and fail if CI happened to run on a Friday evening or early
    Monday UTC. So we pin the gate OPEN for the general suite by patching the
    references imported into ``kudbee_quant.paper.paper`` (the same way the paper
    tests already patch ``build_levels`` / ``confluence_score`` on that module).

    The gate's own logic is exercised directly in ``tests/test_event_calendar.py``,
    and a test that wants to see the gate BLOCK simply re-patches these on ``pp``
    (last write wins within a test).
    """
    try:
        import kudbee_quant.paper.paper as pp
    except Exception:  # pragma: no cover - paper deps unavailable
        return
    monkeypatch.setattr(pp, "get_blocking_event", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(pp, "is_friday_close_window", lambda *a, **k: False, raising=False)
    monkeypatch.setattr(pp, "is_monday_open_window", lambda *a, **k: False, raising=False)
