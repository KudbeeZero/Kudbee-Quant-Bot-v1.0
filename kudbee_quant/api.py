"""Kudbee Quant backend API — exposes the engine to the website (one unit).

Run:  uvicorn kudbee_quant.api:app --reload
The static site's Live Signals page calls these endpoints. Read-only by
default; the paper-scan endpoint logs to the local journal. Everything reflects
the VALIDATED config: 1h, >=50% confluence, 3R target, 0.25-ATR limit retrace.

Honesty note: signals are the engine's directional read with confidence
intervals from backtests — not advice, not a guarantee.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from .alert_inbox import inbox_entry, log_alert, push_inbox_entry
from .api_security import RateLimiter, check_token, require_token, safe_spec, safe_symbol
from .confluence.stack import confluence_score
from .confluence.trace import (EMA_SPAN_MAX, EMA_SPAN_MIN, FACTOR_KEYS,
                               factor_trace, sandbox_score)
from .ingest import BinanceClient, RouterClient
from .journal import TradeJournal
from .levels import build_levels
from .replay import ReplayTooOld, ReplayUnsupported, replay_trade

app = FastAPI(title="Kudbee Quant API", version="1.0.0",
              description="Honest Traders Reality PVSRA quant engine — read-only signals.")
# CORS: scope to the site origin if configured (KUDBEE_SITE_ORIGIN), else permissive
# for local/dev. Reads are public by design (the Live Signals page); writes are
# additionally token-gated (see require_token).
_origins = [o for o in os.environ.get("KUDBEE_SITE_ORIGIN", "").split(",") if o] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST"],
                   allow_headers=["*"])

# Rate limiters: generous for public reads, tight for journal writes. The
# sandbox recompute gets its own scope so what-if spam can't starve the reads.
_write_limit = RateLimiter(limit=10, window=60.0, scope="write")
_read_limit = RateLimiter(limit=120, window=60.0, scope="read")
_sandbox_limit = RateLimiter(limit=30, window=60.0, scope="sandbox")

# Validated default config — single source of truth (config/validated_defaults.py).
from .config.validated_defaults import VALIDATED_BASELINE

CONFIG = dict(VALIDATED_BASELINE)
_ALLOWED_TF = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "config": CONFIG}


def _bracket_for(last) -> dict | None:
    """The validated limit-retrace bracket from a scored last bar (None when
    not actionable). Shared by /api/signal and /api/trace so they can't drift."""
    price, atr = float(last["close"]), float(last["atr"])
    direction, pct = int(last["direction"]), float(last["confluence_pct"])
    if not (pct >= CONFIG["min_pct"] and direction != 0):
        return None
    sd = atr * CONFIG["stop_atr"]
    limit = price - direction * CONFIG["retrace_atr"] * atr
    return {"entry_limit": round(limit, 6),
            "stop": round(limit - direction * sd, 6),
            "target": round(limit + direction * sd * CONFIG["target_r"], 6),
            "target_r": CONFIG["target_r"]}


@app.get("/api/signal/{symbol}")
def signal(symbol: str, interval: str = "1h", _rl: None = Depends(_read_limit)) -> dict:
    """Current confluence signal + the validated limit-retrace 3R bracket."""
    sym = safe_symbol(symbol)               # whitelist (SSRF/traversal guard)
    if interval not in _ALLOWED_TF:
        raise HTTPException(status_code=422, detail="invalid interval")
    try:
        f = build_levels(BinanceClient().klines(sym, interval=interval, limit=600))
    except HTTPException:
        raise
    except Exception:                       # network / upstream — no detail leak
        raise HTTPException(status_code=502, detail="upstream data error")
    last = confluence_score(f).iloc[-1]
    price = float(last["close"])
    direction, pct = int(last["direction"]), float(last["confluence_pct"])
    strength, nf = int(last["strength"]), int(last["n_factors"])
    actionable = pct >= CONFIG["min_pct"] and direction != 0
    side = "long" if direction > 0 else ("short" if direction < 0 else "flat")
    return {
        "symbol": sym, "interval": interval,
        "timestamp": str(last["timestamp"]), "price": round(price, 6),
        "confluence_pct": round(pct, 3), "strength": strength, "n_factors": nf,
        "net_score": int(last["net_score"]), "direction": direction, "side": side,
        "actionable": bool(actionable),
        "bracket": _bracket_for(last),
        "disclaimer": "Directional read, not advice. Enter via LIMIT (maker), size small.",
    }


@app.get("/api/trace/{spec}")
def trace(spec: str, interval: str = "1h", bars: int = 64,
          _rl: None = Depends(_read_limit)) -> dict:
    """Per-factor confluence flow for a symbol: each bar's 10 votes with
    human-readable details, for the trade-flow visualizer. Unlike /api/signal
    this accepts full specs (yahoo:GC=F) and routes TradFi correctly."""
    spec = safe_spec(spec)                  # whitelist, keeps the source prefix
    if interval not in _ALLOWED_TF:
        raise HTTPException(status_code=422, detail="invalid interval")
    if not 1 <= bars <= 200:
        raise HTTPException(status_code=422, detail="bars must be 1..200")
    try:
        f = build_levels(RouterClient().klines(spec, interval=interval, limit=600))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="upstream data error")
    return {
        "symbol": spec, "interval": interval,
        "bars": factor_trace(f, bars=bars),
        "config": {"min_pct": CONFIG["min_pct"]},
        "bracket": _bracket_for(confluence_score(f).iloc[-1]),
        "disclaimer": "Directional read, not advice. Enter via LIMIT (maker), size small.",
    }


class SandboxRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=30)
    interval: str = Field(default="1h", pattern=r"^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d)$")
    bars: int = Field(default=64, ge=1, le=200)
    ema: dict[str, int] | None = None
    factors: list[str] | None = Field(default=None, max_length=10)
    min_pct: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("ema")
    @classmethod
    def _ema_bounds(cls, v):
        if v is None:
            return v
        bad = set(v) - {"ema_13", "ema_50", "ema_800"}
        if bad:
            raise ValueError(f"unknown EMA keys: {sorted(bad)}")
        for k, span in v.items():
            if not EMA_SPAN_MIN <= span <= EMA_SPAN_MAX:
                raise ValueError(f"{k} span must be {EMA_SPAN_MIN}..{EMA_SPAN_MAX}")
        return v

    @field_validator("factors")
    @classmethod
    def _factor_keys(cls, v):
        if v is None:
            return v
        unknown = set(v) - set(FACTOR_KEYS)
        if unknown:
            raise ValueError(f"unknown factors: {sorted(unknown)}")
        if not v:
            raise ValueError("at least one factor must be enabled")
        return v


@app.post("/api/sandbox/trace")
def sandbox_trace(req: SandboxRequest, _rl: None = Depends(_sandbox_limit)) -> dict:
    """UNVALIDATED what-if recompute: custom EMA spans / factor subset / display
    threshold. Compute-only — it never trades, never journals, never touches
    the validated config (which is why it needs no token)."""
    spec = safe_spec(req.symbol)
    try:
        f = build_levels(RouterClient().klines(spec, interval=req.interval, limit=600))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="upstream data error")
    try:
        out = sandbox_score(f, ema_spans=req.ema, enabled=req.factors,
                            min_pct=req.min_pct, bars=req.bars)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    out.update(symbol=spec, interval=req.interval,
               sandbox_note="UNVALIDATED SANDBOX — display-only; never trades, never journals.")
    return out


@app.get("/api/replay/{trade_id}")
def replay(trade_id: str, _rl: None = Depends(_read_limit)) -> dict:
    """Replay a journal trade through the confluence stack (read-only). The
    response carries an honesty caveat: bars are recomputed from current data
    and may differ from live-edge conditions (MEMORY §29/§31)."""
    try:
        return replay_trade(trade_id, journal=TradeJournal(), client=RouterClient())
    except KeyError:
        raise HTTPException(status_code=404, detail="trade not found")
    except (ReplayUnsupported, ReplayTooOld, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="upstream data error")


@app.get("/api/journal")
def journal() -> dict:
    from .exposure import portfolio_exposure, total_gross_risk
    j = TradeJournal()
    by_status: dict[str, int] = {}
    for p in j.predictions:
        by_status[p.status] = by_status.get(p.status, 0) + 1
    sc = j.scorecard()
    return {
        "counts": by_status,
        "scorecard": sc.to_dict("records") if not sc.empty else [],
        "open": [{"id": p.id, "symbol": p.symbol, "setup": p.setup, "status": p.status,
                  "direction": p.direction, "entry": p.entry, "stop": p.stop,
                  "target": p.target, "created_at": p.created_at}
                 for p in j.predictions if p.status in ("open", "pending")],
        "exposure": [ex.as_dict() for ex in portfolio_exposure(j.predictions)],
        "total_gross_risk_pct": round(total_gross_risk(j.predictions) * 100, 2),
        "by_source": j.source_record(),
        "by_venue": j.venue_record(),
        "resolved_series": j.resolved_series(),
    }


class AlertPayload(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Za-z0-9._=^-]+$")
    direction: float = Field(..., ge=-1.0, le=1.0)
    entry: float = Field(..., gt=0)
    stop: float = Field(..., gt=0)
    target: float = Field(..., gt=0)
    target_r: float = Field(default=3.0, ge=0.5, le=10.0)
    conf: float | None = Field(default=None, ge=0.0, le=1.0)
    tf: str = Field(default="1h", pattern=r"^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d)$")
    note: str = Field(default="", max_length=500)
    # TradingView cannot send custom headers, so the shared secret may ride in
    # the alert's JSON body instead of X-API-Token. Never logged or echoed.
    token: str | None = Field(default=None, max_length=256)


@app.post("/api/alert")
def alert_webhook(a: AlertPayload,
                  x_api_token: str | None = Header(default=None),
                  token: str | None = Query(default=None),
                  _rl: None = Depends(_write_limit)) -> dict:
    """Receive a TradingView indicator alert (JSON) and log it as a paper trade.

    Closes the loop: chart setup fires -> webhook -> journal -> forward score.
    Logged with source="human" — TV alerts are the trader's chart read, and the
    bot-vs-human provenance split (journal.source_record) must stay honest.

    Auth (fail-closed, see api_security.py): the KUDBEE_API_TOKEN may arrive as
    the X-API-Token header, a ?token= query param, or a "token" field in the
    JSON body — TradingView supports no custom headers, so put it in the alert
    message body (preferred; query strings can end up in access logs).
    TV alert message template:
        {"symbol": "{{ticker}}", "direction": 1, "entry": {{close}},
         "stop": ..., "target": ..., "tf": "1h", "note": "...",
         "token": "<KUDBEE_API_TOKEN>"}

    Persistence (see alert_inbox.py): the host's journal is an ephemeral
    checkout, so the alert is ALSO committed to the repo's alert inbox for the
    hourly Action to ingest and score. "inbox": false in the response means
    that push didn't happen (no KUDBEE_GH_TOKEN, or GitHub unreachable) — the
    alert then lives only until the next redeploy.
    """
    check_token(x_api_token or token or a.token)
    if a.direction == 0:
        raise HTTPException(status_code=422, detail="direction must be non-zero (long>0, short<0)")
    alert = {k: v for k, v in a.model_dump().items() if k != "token"}
    entry = inbox_entry(alert)
    j = TradeJournal()
    p = log_alert(j, alert, entry["id"])
    if p is None:
        return {"logged": False, "reason": "already in a trade on this symbol+timeframe"}
    return {"logged": True, "id": p.id, "symbol": p.symbol, "entry": p.entry,
            "stop": p.stop, "target": p.target, "status": p.status,
            "inbox": push_inbox_entry(entry)}


class ScanRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=25)


@app.post("/api/paper/scan")
def paper_scan_endpoint(req: ScanRequest, _auth: None = Depends(require_token),
                        _rl: None = Depends(_write_limit)) -> dict:
    from .paper import paper_scan
    symbols = [safe_symbol(s) for s in req.symbols]   # whitelist every symbol
    logged = paper_scan(symbols, min_pct=CONFIG["min_pct"], target_r=CONFIG["target_r"],
                        stop_atr=CONFIG["stop_atr"], retrace_atr=CONFIG["retrace_atr"],
                        interval=CONFIG["interval"])
    return {"logged": [{"id": p.id, "symbol": p.symbol, "setup": p.setup,
                        "entry_limit": p.entry, "stop": p.stop, "target": p.target,
                        "status": p.status} for p in logged]}


@app.get("/api/metrics")
def system_metrics(_rl: None = Depends(_read_limit)) -> dict:
    """Host CPU/memory/disk of the machine serving the app — dashboard panel."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_pct": round(cpu, 1),
            "mem_used_gb": round(vm.used / 1e9, 2),
            "mem_total_gb": round(vm.total / 1e9, 2),
            "mem_pct": round(vm.percent, 1),
            "disk_used_gb": round(disk.used / 1e9, 1),
            "disk_total_gb": round(disk.total / 1e9, 1),
            "disk_pct": round(disk.percent, 1),
        }
    except ImportError:
        return {"error": "psutil not installed"}


_DASHBOARD_FILE = Path(__file__).resolve().parent / "static" / "dashboard.html"


@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def dashboard(_rl: None = Depends(_read_limit)) -> HTMLResponse:
    """Mission-control dashboard — static one-pager, read-only data only."""
    return HTMLResponse(_DASHBOARD_FILE.read_text(encoding="utf-8"))
