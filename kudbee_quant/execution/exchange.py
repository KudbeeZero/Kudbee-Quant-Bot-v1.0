"""Authenticated exchange client for LIVE order placement.

This is the real money seam. Everything here is reached ONLY after
``require_live_enabled()`` has passed (see ``execution/live.py``); nothing in this
module is exercised in paper mode.

Design choices (deliberate, grounded in MEMORY):

  * **Maker-only.** MEMORY §1/§25 are blunt: the strategy's edge *is* the
    limit-retrace MAKER fill; market/taker execution turns expectancy negative.
    So :meth:`ExchangeClient.create_limit_order` is the order primitive and the
    Binance implementation sends ``LIMIT_MAKER`` (rejected by the venue rather
    than filled as a taker if it would cross). There is intentionally **no**
    market-order method — taking liquidity is not part of this strategy.
  * **Native signed REST, not ccxt.** The repo already speaks the Binance REST
    API with plain ``requests`` (see ``ingest/binance.py``); a thin HMAC-signed
    client is lighter, hermetically testable, and sits behind the
    :class:`ExchangeClient` Protocol so ccxt (or any venue) can drop in later.
  * **No secrets here at rest.** API keys are read from the environment only
    inside :class:`BinanceBrokerClient`, only when an authenticated call is made,
    and are never logged or echoed.

Symbols are validated through the same SSRF-safe ``parse_spec`` whitelist the
ingest router uses before they are interpolated into a request URL/query.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

import requests

from ..ingest.router import parse_spec

# Normalised order states, mapped from venue-specific strings so the journal and
# the executor never branch on a particular exchange's vocabulary.
NEW = "new"
PARTIAL = "partial"
FILLED = "filled"
CANCELED = "canceled"
REJECTED = "rejected"

# Binance spot order-status -> our normalised state.
_BINANCE_STATUS = {
    "NEW": NEW, "PARTIALLY_FILLED": PARTIAL, "FILLED": FILLED,
    "CANCELED": CANCELED, "PENDING_CANCEL": CANCELED, "REJECTED": REJECTED,
    "EXPIRED": CANCELED,
}

BUY = "BUY"
SELL = "SELL"


class OrderError(RuntimeError):
    """Any failure placing / cancelling / polling an order on the venue."""


@dataclass
class OrderResult:
    """Normalised outcome of an order operation, venue-agnostic.

    ``filled_at`` is the VENUE's fill timestamp (ISO-8601 UTC), never a bar time —
    that distinction is the whole point of polling the exchange rather than
    inferring fills from candles (see the journal's §29 fictitious-fill caveat).
    """
    order_id: str
    status: str                      # one of NEW/PARTIAL/FILLED/CANCELED/REJECTED
    filled_qty: float = 0.0
    avg_price: float | None = None   # average fill price (None until any fill)
    filled_at: str | None = None     # ISO-8601 UTC, set once FILLED
    raw: dict = field(default_factory=dict)

    @property
    def is_filled(self) -> bool:
        return self.status == FILLED

    @property
    def is_open(self) -> bool:
        return self.status in (NEW, PARTIAL)


class ExchangeClient(Protocol):
    """Minimal authenticated venue surface the live executor needs.

    No market-order method on purpose: this strategy only ever rests a maker
    limit at the retrace level.
    """

    def create_limit_order(self, symbol: str, side: str, qty: float,
                           price: float) -> OrderResult: ...

    def fetch_order(self, symbol: str, order_id: str) -> OrderResult: ...

    def cancel_order(self, symbol: str, order_id: str) -> OrderResult: ...

    def fetch_free_balance(self, asset: str) -> float:
        """Free (available) balance of ``asset`` in its own units (e.g. USDT)."""
        ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ms_to_iso(ms: int | float | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc).isoformat()


class BinanceBrokerClient:
    """Authenticated Binance spot REST client (HMAC-SHA256 signed).

    Credentials come from the environment and ONLY from there:
        BINANCE_API_KEY, BINANCE_API_SECRET      (required for any signed call)
        BINANCE_TESTNET=true                     (use the spot testnet endpoint)

    Keys are never logged. Construction is cheap and does not touch the network;
    a missing key only fails when an authenticated request is actually made, so
    the live executor can be constructed (behind the gate) before keys are wired.
    """

    _LIVE_BASE = "https://api.binance.com"
    _TESTNET_BASE = "https://testnet.binance.vision"

    def __init__(self, api_key: str | None = None, api_secret: str | None = None,
                 base: str | None = None, session: requests.Session | None = None,
                 recv_window_ms: int = 5000):
        # Read from env if not injected; do NOT raise here (lazy — see submit()).
        self._api_key = api_key if api_key is not None else os.environ.get("BINANCE_API_KEY", "")
        self._api_secret = (api_secret if api_secret is not None
                            else os.environ.get("BINANCE_API_SECRET", ""))
        if base is None:
            testnet = os.environ.get("BINANCE_TESTNET", "").strip().lower() in {"1", "true", "yes", "on"}
            base = self._TESTNET_BASE if testnet else self._LIVE_BASE
        self.base = base
        self.session = session or requests.Session()
        self.recv_window_ms = recv_window_ms

    # --- low-level signed transport ----------------------------------------

    def _require_keys(self) -> None:
        if not self._api_key or not self._api_secret:
            raise OrderError(
                "missing exchange credentials — set BINANCE_API_KEY and "
                "BINANCE_API_SECRET (never commit these). Keys are read from the "
                "environment only."
            )

    def _sign(self, params: dict) -> str:
        query = urllib.parse.urlencode(params, doseq=True)
        sig = hmac.new(self._api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        return f"{query}&signature={sig}"

    def _signed_request(self, method: str, path: str, params: dict) -> dict:
        """Send a signed request; raise :class:`OrderError` on any failure.

        Error bodies are surfaced verbatim EXCEPT we never include the API key
        or signature in the message.
        """
        self._require_keys()
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.recv_window_ms
        url = f"{self.base}{path}?{self._sign(params)}"
        headers = {"X-MBX-APIKEY": self._api_key}
        try:
            resp = self.session.request(method, url, headers=headers, timeout=15)
        except requests.RequestException as exc:
            raise OrderError(f"{method} {path} network error: {exc}") from exc
        if resp.status_code >= 400:
            # Binance returns {"code": -2010, "msg": "..."} — pass the msg through.
            try:
                body = resp.json()
            except ValueError:
                body = {"msg": resp.text[:200]}
            raise OrderError(f"{method} {path} -> HTTP {resp.status_code}: {body.get('msg', body)}")
        return resp.json()

    @staticmethod
    def _result_from(d: dict) -> OrderResult:
        status = _BINANCE_STATUS.get(str(d.get("status", "")).upper(), NEW)
        executed = float(d.get("executedQty", 0.0) or 0.0)
        quote = float(d.get("cummulativeQuoteQty", 0.0) or 0.0)
        avg = (quote / executed) if executed > 0 else None
        # transactTime (on create) / updateTime (on fetch) is the venue clock.
        filled_at = _ms_to_iso(d.get("updateTime") or d.get("transactTime")) if status == FILLED else None
        return OrderResult(order_id=str(d.get("orderId", "")), status=status,
                           filled_qty=executed, avg_price=avg, filled_at=filled_at, raw=d)

    # --- ExchangeClient surface --------------------------------------------

    def create_limit_order(self, symbol: str, side: str, qty: float, price: float) -> OrderResult:
        """Rest a MAKER-only limit (``LIMIT_MAKER``). The venue REJECTS it rather
        than filling as a taker if ``price`` would cross the book — exactly the
        guarantee the strategy depends on (no accidental taker fills, §25)."""
        _source, sym = parse_spec(symbol)            # SSRF-safe symbol whitelist
        if side not in (BUY, SELL):
            raise OrderError(f"side must be {BUY!r} or {SELL!r}, got {side!r}")
        if qty <= 0 or price <= 0:
            raise OrderError(f"qty and price must be positive (qty={qty}, price={price})")
        d = self._signed_request("POST", "/api/v3/order", {
            "symbol": sym.upper(), "side": side, "type": "LIMIT_MAKER",
            "quantity": qty, "price": price,
        })
        return self._result_from(d)

    def fetch_order(self, symbol: str, order_id: str) -> OrderResult:
        _source, sym = parse_spec(symbol)
        d = self._signed_request("GET", "/api/v3/order",
                                 {"symbol": sym.upper(), "orderId": order_id})
        return self._result_from(d)

    def cancel_order(self, symbol: str, order_id: str) -> OrderResult:
        _source, sym = parse_spec(symbol)
        d = self._signed_request("DELETE", "/api/v3/order",
                                 {"symbol": sym.upper(), "orderId": order_id})
        return self._result_from(d)

    def fetch_free_balance(self, asset: str) -> float:
        d = self._signed_request("GET", "/api/v3/account", {})
        for bal in d.get("balances", []):
            if str(bal.get("asset", "")).upper() == asset.upper():
                return float(bal.get("free", 0.0) or 0.0)
        return 0.0
