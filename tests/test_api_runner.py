"""Curated-runner tests: session-gated, whitelist-only, bounded params, async
jobs, and the load-bearing guarantee that it NEVER writes the journal."""
import time

import pandas as pd
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import kudbee_quant.api as api  # noqa: E402
import kudbee_quant.api_auth as auth  # noqa: E402
import kudbee_quant.api_runner as runner  # noqa: E402
from kudbee_quant.api_security import _reset_rate_limits  # noqa: E402


def _client(monkeypatch):
    monkeypatch.setenv("KUDBEE_DASHBOARD_PASSWORD", "pw")
    monkeypatch.setenv("KUDBEE_SESSION_SECRET", "k")
    _reset_rate_limits()
    runner._reset_jobs()
    return TestClient(api.app)


def _auth_cookies():
    return {auth.COOKIE_NAME: auth.issue_session()}


def test_runner_requires_session(monkeypatch):
    c = _client(monkeypatch)
    assert c.post("/api/run/signal", json={"params": {}}).status_code == 401
    assert c.get("/api/run").status_code == 401


def test_list_actions_exposes_whitelist(monkeypatch):
    c = _client(monkeypatch)
    r = c.get("/api/run", cookies=_auth_cookies())
    assert r.status_code == 200
    names = {a["action"] for a in r.json()["actions"]}
    assert {"signal", "backtest", "paper-scan"} <= names


def test_runner_rejects_unknown_action(monkeypatch):
    c = _client(monkeypatch)
    r = c.post("/api/run/rm_rf", json={"params": {}}, cookies=_auth_cookies())
    assert r.status_code == 404


def test_runner_rejects_bad_params(monkeypatch):
    c = _client(monkeypatch)
    bad_symbol = c.post("/api/run/backtest", json={"params": {"symbol": "../../etc"}},
                        cookies=_auth_cookies())
    assert bad_symbol.status_code == 422
    out_of_bounds = c.post("/api/run/backtest",
                           json={"params": {"symbol": "BTCUSDT", "limit": 999999}},
                           cookies=_auth_cookies())
    assert out_of_bounds.status_code == 422


def test_runner_job_lifecycle(monkeypatch):
    c = _client(monkeypatch)

    class EchoParams(BaseModel):
        value: int = Field(default=1, ge=0, le=10)

    monkeypatch.setitem(runner._ACTIONS, "_echo",
                        (EchoParams, lambda p: {"echo": p.value}, "Echo"))
    r = c.post("/api/run/_echo", json={"params": {"value": 7}}, cookies=_auth_cookies())
    assert r.status_code == 200
    job_id = r.json()["id"]

    result = None
    for _ in range(40):
        j = c.get("/api/run/" + job_id, cookies=_auth_cookies()).json()
        if j["status"] in ("done", "error"):
            result = j
            break
        time.sleep(0.1)
    assert result and result["status"] == "done" and result["result"] == {"echo": 7}


def test_runner_busy_returns_429(monkeypatch):
    c = _client(monkeypatch)
    monkeypatch.setattr(runner, "_active_count", lambda: runner._MAX_WORKERS)
    r = c.post("/api/run/signal", json={"params": {"symbol": "BTCUSDT"}},
               cookies=_auth_cookies())
    assert r.status_code == 429


def test_paper_scan_dry_run_never_writes_journal(tmp_path, monkeypatch):
    """The runner's paper-scan uses dry_run=True; the journal must be untouched.

    This is the guardrail against the data-poisoning vector api_security.py closed.
    """
    import kudbee_quant.paper.paper as pp
    from kudbee_quant.journal import TradeJournal

    # Force a strong, actionable long signal (same seam test_paper.py uses).
    fake = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1,
                                                            freq="h", tz="UTC")})

    path = tmp_path / "j.json"
    j = TradeJournal(path=path, client=C())

    # DRY RUN: returns the computed bracket but persists nothing.
    preview = pp.paper_scan(["BTCUSDT"], min_pct=0.5, journal=j, client=C(), dry_run=True)
    assert len(preview) == 1 and preview[0].direction == 1.0
    assert j.predictions == []          # nothing added in-memory
    assert not path.exists()            # nothing written to disk

    # Sanity: the SAME inputs DO persist when not a dry run (proves the seam works).
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, journal=j, client=C(), dry_run=False)
    assert len(logged) == 1 and len(j.predictions) == 1
