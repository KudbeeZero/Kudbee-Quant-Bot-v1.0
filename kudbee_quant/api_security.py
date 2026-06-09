"""API security helpers — auth, rate limiting, and input validation for the
FastAPI backend (kudbee_quant/api.py).

Closes the gaps the audit flagged: the write endpoints (/api/alert, /api/paper/scan)
were unauthenticated, unvalidated and un-rate-limited, and since CI commits the
journal, that was a real data-poisoning vector. Kept dependency-free (no slowapi)
to honour the project's minimal-dependency ethos — a single-process in-memory
sliding-window limiter is sufficient for this backend.

Design choices:
  * FAIL CLOSED: if no ``KUDBEE_API_TOKEN`` is configured in the environment, the
    write endpoints are DISABLED (503) rather than left open. Reads stay public
    (the site's Live Signals page needs them).
  * Constant-time token comparison (hmac.compare_digest) — no timing oracle.
  * Symbol inputs reuse the existing whitelist (ingest/router.parse_spec) so the
    SSRF/path-traversal guard is enforced at the API edge too.
"""
from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

from .config import get_secret
from .ingest.router import parse_spec

# --- input validation --------------------------------------------------------


def safe_symbol(symbol: str) -> str:
    """Validate + normalize a symbol via the shared whitelist; 422 on bad input."""
    try:
        _src, sym = parse_spec(symbol)
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid symbol")
    return sym.upper()


# --- token auth (fail-closed) ------------------------------------------------


def require_token(x_api_token: str | None = Header(default=None)) -> None:
    """Dependency for write endpoints. Requires the X-API-Token header to match
    the configured KUDBEE_API_TOKEN. If no token is configured, writes are
    disabled entirely (503) — fail closed, never fail open."""
    configured = get_secret("KUDBEE_API_TOKEN", required=False)
    if not configured:
        raise HTTPException(status_code=503, detail="writes disabled (no API token configured)")
    secret = configured.reveal() if hasattr(configured, "reveal") else str(configured)
    if not x_api_token or not hmac.compare_digest(str(x_api_token), secret):
        raise HTTPException(status_code=401, detail="unauthorized")


# --- rate limiting (in-memory sliding window) --------------------------------

_HITS: dict[str, deque] = defaultdict(deque)


class RateLimiter:
    """Per-client sliding-window limiter: ``limit`` requests per ``window`` seconds.
    Use as a FastAPI dependency, one instance per protected route group."""

    def __init__(self, limit: int = 20, window: float = 60.0, scope: str = "default"):
        self.limit = limit
        self.window = window
        self.scope = scope

    def __call__(self, request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        key = f"{self.scope}:{client}"
        now = time.monotonic()
        dq = _HITS[key]
        while dq and dq[0] <= now - self.window:
            dq.popleft()
        if len(dq) >= self.limit:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        dq.append(now)


def _reset_rate_limits() -> None:   # test helper
    _HITS.clear()
