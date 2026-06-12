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

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .api_security import RateLimiter, require_token, safe_symbol
from .confluence.stack import confluence_score
from .ingest import BinanceClient
from .journal import Prediction, TradeJournal
from .levels import build_levels

app = FastAPI(title="Kudbee Quant API", version="1.0.0",
              description="Honest Traders Reality PVSRA quant engine — read-only signals.")
# CORS: scope to the site origin if configured (KUDBEE_SITE_ORIGIN), else permissive
# for local/dev. Reads are public by design (the Live Signals page); writes are
# additionally token-gated (see require_token).
_origins = [o for o in os.environ.get("KUDBEE_SITE_ORIGIN", "").split(",") if o] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST"],
                   allow_headers=["*"])

# Rate limiters: generous for public reads, tight for journal writes.
_write_limit = RateLimiter(limit=10, window=60.0, scope="write")
_read_limit = RateLimiter(limit=120, window=60.0, scope="read")

# Validated default config — single source of truth (config/validated_defaults.py).
from .config.validated_defaults import VALIDATED_BASELINE

CONFIG = dict(VALIDATED_BASELINE)
_ALLOWED_TF = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "config": CONFIG}


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
    price, atr = float(last["close"]), float(last["atr"])
    direction, pct = int(last["direction"]), float(last["confluence_pct"])
    strength, nf = int(last["strength"]), int(last["n_factors"])
    sd = atr * CONFIG["stop_atr"]
    limit = price - direction * CONFIG["retrace_atr"] * atr
    actionable = pct >= CONFIG["min_pct"] and direction != 0
    side = "long" if direction > 0 else ("short" if direction < 0 else "flat")
    return {
        "symbol": sym, "interval": interval,
        "timestamp": str(last["timestamp"]), "price": round(price, 6),
        "confluence_pct": round(pct, 3), "strength": strength, "n_factors": nf,
        "net_score": int(last["net_score"]), "direction": direction, "side": side,
        "actionable": bool(actionable),
        "bracket": ({"entry_limit": round(limit, 6),
                     "stop": round(limit - direction * sd, 6),
                     "target": round(limit + direction * sd * CONFIG["target_r"], 6),
                     "target_r": CONFIG["target_r"]} if actionable else None),
        "disclaimer": "Directional read, not advice. Enter via LIMIT (maker), size small.",
    }


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


@app.post("/api/alert")
def alert_webhook(a: AlertPayload, _auth: None = Depends(require_token),
                  _rl: None = Depends(_write_limit)) -> dict:
    """Receive a TradingView indicator alert (JSON) and log it as a paper trade.

    Closes the loop: chart setup fires -> webhook -> journal -> forward score.
    Token-gated + rate-limited + field-validated (see api_security.py).
    """
    j = TradeJournal()
    open_keys = {(p.symbol, p.timeframe) for p in j.predictions
                 if p.status in ("open", "pending") and p.kind == "bracket"}
    if (a.symbol.upper(), a.tf) in open_keys:
        return {"logged": False, "reason": "already in a trade on this symbol+timeframe"}
    p = j.add(Prediction(
        symbol=a.symbol.upper(), kind="bracket", level=a.entry, entry=a.entry, stop=a.stop,
        target=a.target, direction=1.0 if a.direction > 0 else -1.0, target_r=a.target_r,
        deadline_days=3.0, timeframe=a.tf, pending_limit=True, signal_price=a.entry,
        setup="tv_alert" + (f"_{int(round(a.conf*100))}pct" if a.conf else ""),
        note=f"TradingView alert: {a.note}. conf={a.conf}.",
    ))
    return {"logged": True, "id": p.id, "symbol": p.symbol, "entry": p.entry,
            "stop": p.stop, "target": p.target, "status": p.status}


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
