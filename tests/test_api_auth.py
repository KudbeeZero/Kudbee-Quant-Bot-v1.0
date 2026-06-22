"""Auth tests: the shared-password login + signed session cookie that gates the
dashboard and the curated runner. Fail-closed, like the write-token path."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import kudbee_quant.api as api  # noqa: E402
import kudbee_quant.api_auth as auth  # noqa: E402
from kudbee_quant.api_security import _reset_rate_limits  # noqa: E402

_PW = "letmein"


def _client(monkeypatch, password=_PW, secret="sign-key"):
    if password is not None:
        monkeypatch.setenv("KUDBEE_DASHBOARD_PASSWORD", password)
    else:
        monkeypatch.delenv("KUDBEE_DASHBOARD_PASSWORD", raising=False)
    if secret is not None:
        monkeypatch.setenv("KUDBEE_SESSION_SECRET", secret)
    _reset_rate_limits()
    # follow_redirects off so we can assert the 302 -> /login gate.
    return TestClient(api.app, follow_redirects=False)


def test_dashboard_redirects_without_cookie(monkeypatch):
    c = _client(monkeypatch)
    r = c.get("/dashboard")
    assert r.status_code == 302 and r.headers["location"] == "/login"


def test_login_sets_httponly_cookie(monkeypatch):
    c = _client(monkeypatch)
    r = c.post("/api/login", json={"password": _PW})
    assert r.status_code == 200
    sc = r.headers.get("set-cookie", "")
    assert auth.COOKIE_NAME in sc and "HttpOnly" in sc


def test_login_rejects_bad_password(monkeypatch):
    c = _client(monkeypatch)
    assert c.post("/api/login", json={"password": "nope"}).status_code == 401


def test_login_disabled_when_unset(monkeypatch):
    c = _client(monkeypatch, password=None)
    assert c.post("/api/login", json={"password": "anything"}).status_code == 503


def test_session_unlocks_dashboard(monkeypatch):
    c = _client(monkeypatch)
    token = auth.issue_session()                         # signed with the test secret
    r = c.get("/dashboard", cookies={auth.COOKIE_NAME: token})
    assert r.status_code == 200 and "Control Center" in r.text


def test_expired_session_is_rejected(monkeypatch):
    c = _client(monkeypatch)
    expired = auth.issue_session(max_age=-10)
    assert auth.verify_session(expired) is False
    r = c.get("/dashboard", cookies={auth.COOKIE_NAME: expired})
    assert r.status_code == 302                          # gate still bounces


def test_tampered_cookie_is_rejected(monkeypatch):
    c = _client(monkeypatch)
    token = auth.issue_session()
    # Flip the FIRST signature char — it always carries 6 meaningful bits of the
    # HMAC's byte 0, so the tamper is GUARANTEED to change the decoded signature.
    # (Mutating trailing base64 chars was brittle: their low bits are padding and
    # can decode unchanged, so the tamper was occasionally a no-op -> flaky pass.)
    payload, sig = token.split(".")
    flipped = "B" if sig[0] != "B" else "C"
    bad = f"{payload}.{flipped}{sig[1:]}"
    assert auth.verify_session(bad) is False
    assert c.get("/dashboard", cookies={auth.COOKIE_NAME: bad}).status_code == 302


def test_logout_clears_cookie(monkeypatch):
    c = _client(monkeypatch)
    r = c.post("/api/logout")
    assert r.status_code == 200 and auth.COOKIE_NAME in r.headers.get("set-cookie", "")


def test_login_rate_limited(monkeypatch):
    c = _client(monkeypatch)
    codes = [c.post("/api/login", json={"password": "x"}).status_code for _ in range(7)]
    assert 429 in codes                                  # 5/min login limiter trips


def test_gated_api_requires_session(monkeypatch):
    c = _client(monkeypatch)
    assert c.get("/api/research").status_code == 401
    assert c.get("/api/open-trades").status_code == 401
    assert c.get("/api/run").status_code == 401
