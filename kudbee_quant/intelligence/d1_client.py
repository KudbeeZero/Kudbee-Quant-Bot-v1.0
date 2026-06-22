"""D1 REST client for TR level intelligence.

Cloudflare D1 REST API:
  POST https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{db_id}/query

Requires: CF_ACCOUNT_ID, CF_API_TOKEN, D1_DATABASE_ID in the environment.

This is the path the Render FastAPI app + the paper-scan CLI use to read/write D1.
The Cloudflare Worker itself uses its native ``env.DB`` binding (no REST needed
there). Every caller in this package wraps these functions in try/except — a D1
outage must never block a scan or a Telegram reply.
"""
from __future__ import annotations

import os

import httpx

CF_BASE = "https://api.cloudflare.com/client/v4"


def _headers() -> dict:
    token = os.environ.get("CF_API_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}",
                "Content-Type": "application/json"}
    raise RuntimeError("CF_API_TOKEN not set")


def _url() -> str:
    account_id = os.environ["CF_ACCOUNT_ID"]
    db_id = os.environ["D1_DATABASE_ID"]
    return f"{CF_BASE}/accounts/{account_id}/d1/database/{db_id}/query"


def _post(sql: str, params: list | None) -> dict:
    body = {"sql": sql, "params": params or []}
    r = httpx.post(_url(), json=body, headers=_headers(), timeout=10)
    r.raise_for_status()
    result = r.json()
    if not result.get("success"):
        raise RuntimeError(f"D1 error: {result.get('errors')}")
    # D1 returns a list of per-statement results; we send one statement.
    return result["result"][0]


def d1_query(sql: str, params: list | None = None) -> list[dict]:
    """Execute a SQL query against the D1 database. Returns rows as dicts."""
    return _post(sql, params).get("results", [])


def d1_execute(sql: str, params: list | None = None) -> dict:
    """Execute a write (INSERT/UPDATE) against D1. Returns the statement meta
    (``changes``, ``last_row_id``, ...)."""
    return _post(sql, params).get("meta", {})
