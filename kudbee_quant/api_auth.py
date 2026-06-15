"""Dashboard auth — a signed, stateless session cookie gating the control center.

Mirrors the design ethos of ``api_security.py``: dependency-free (native ``hmac``,
no ``itsdangerous``), fail-closed, constant-time comparison. The public read
endpoints stay open (the marketing site proxies them); only the dashboard HTML
and the curated runner are gated by a session.

Auth model (deliberately minimal for now — see docs/HANDOFF.md):
  * ONE shared password (``KUDBEE_DASHBOARD_PASSWORD``) unlocks the dashboard.
    No users, no email, no DB yet.
  * On a correct password we mint a stateless cookie:
        b64url(payload) + "." + b64url(hmac_sha256(payload, KUDBEE_SESSION_SECRET))
    where payload is JSON ``{"iss": "kudbee", "exp": <unix>}``. The dict shape
    leaves room for ``sub``/``role`` when real accounts land, without a schema
    change to the cookie format.
  * FAIL CLOSED: if no password is configured the login route returns 503 and
    every gated route denies — exactly like ``check_token`` for writes.

Nothing here is logged or echoed; secrets are read via ``get_secret`` (SecretStr).
"""
from __future__ import annotations

import base64
import hmac
import json
import time
from hashlib import sha256

from fastapi import HTTPException, Request

from .config import get_secret

COOKIE_NAME = "kudbee_session"
# 12 hours: long enough for a working session, short enough to bound a leaked cookie.
DEFAULT_MAX_AGE = 12 * 3600
_ISS = "kudbee"


# --- secret access (fail-closed) ---------------------------------------------


def _password() -> str | None:
    s = get_secret("KUDBEE_DASHBOARD_PASSWORD", required=False)
    return s.reveal() if s else None


def _signing_key() -> bytes:
    """The HMAC key for session cookies.

    Prefers a dedicated ``KUDBEE_SESSION_SECRET`` so rotating the password does
    not silently invalidate the signing scheme. Falls back to deriving a key
    from the password (so the feature still works with one env var set) — but a
    dedicated secret is recommended and documented in render.yaml.
    """
    s = get_secret("KUDBEE_SESSION_SECRET", required=False)
    if s:
        return s.reveal().encode()
    pw = _password()
    if pw:
        # Derive a stable key from the password; clearly namespaced.
        return sha256(b"kudbee-session-v1:" + pw.encode()).digest()
    return b""  # no secret configured -> verify_session always fails (fail-closed)


def login_enabled() -> bool:
    """True when a dashboard password is configured (login is usable)."""
    return bool(_password())


def check_password(provided: str | None) -> None:
    """Constant-time password check. 503 when unconfigured, 401 on mismatch."""
    configured = _password()
    if not configured:
        raise HTTPException(status_code=503, detail="login disabled (no dashboard password configured)")
    if not provided or not hmac.compare_digest(str(provided), configured):
        raise HTTPException(status_code=401, detail="unauthorized")


# --- cookie sign / verify ----------------------------------------------------


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_session(max_age: int = DEFAULT_MAX_AGE) -> str:
    """Mint a signed session token valid for ``max_age`` seconds."""
    payload = {"iss": _ISS, "exp": int(time.time()) + int(max_age)}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(_signing_key(), raw, sha256).digest()
    return f"{_b64e(raw)}.{_b64e(sig)}"


def verify_session(cookie: str | None) -> bool:
    """True iff ``cookie`` is a well-formed, correctly-signed, unexpired token.

    Fail-closed: any malformation, bad signature, missing secret, or expiry
    returns False (never raises)."""
    key = _signing_key()
    if not key or not cookie or "." not in cookie:
        return False
    try:
        body_b64, sig_b64 = cookie.split(".", 1)
        raw = _b64d(body_b64)
        sig = _b64d(sig_b64)
        expected = hmac.new(key, raw, sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return False
        payload = json.loads(raw)
        if payload.get("iss") != _ISS:
            return False
        return int(payload.get("exp", 0)) > int(time.time())
    except Exception:
        return False


def has_session(request: Request) -> bool:
    return verify_session(request.cookies.get(COOKIE_NAME))


def require_session(request: Request) -> None:
    """FastAPI dependency for gated API/runner routes — 401 without a session."""
    if not has_session(request):
        raise HTTPException(status_code=401, detail="login required")
