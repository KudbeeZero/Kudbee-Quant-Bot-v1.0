"""Kudbee Quant backend API — exposes the engine to the website (one unit).

Run:  uvicorn kudbee_quant.api:app --reload
The static site's Live Signals page calls these endpoints. Read-only by
default; the paper-scan endpoint logs to the local journal. Everything reflects
the VALIDATED config: 1h, >=50% confluence, 3R target, 0.25-ATR limit retrace.

Honesty note: signals are the engine's directional read with confidence
intervals from backtests — not advice, not a guarantee.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .confluence.stack import confluence_score
from .ingest import BinanceClient
from .journal import Prediction, TradeJournal
from .levels import build_levels

app = FastAPI(title="Kudbee Quant API", version="1.0.0",
              description="Honest Traders Reality PVSRA quant engine — read-only signals.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"],
                   allow_headers=["*"])

# Validated default config (see docs/research/testable_ruleset.md).
CONFIG = {"min_pct": 0.5, "target_r": 3.0, "stop_atr": 1.5, "retrace_atr": 0.25, "interval": "1h"}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "config": CONFIG}


@app.get("/api/signal/{symbol}")
def signal(symbol: str, interval: str = "1h") -> dict:
    """Current confluence signal + the validated limit-retrace 3R bracket."""
    try:
        f = build_levels(BinanceClient().klines(symbol.upper(), interval=interval, limit=600))
    except Exception as e:  # network / bad symbol
        raise HTTPException(status_code=502, detail=f"data error: {e}")
    last = confluence_score(f).iloc[-1]
    price, atr = float(last["close"]), float(last["atr"])
    direction, pct = int(last["direction"]), float(last["confluence_pct"])
    strength, nf = int(last["strength"]), int(last["n_factors"])
    sd = atr * CONFIG["stop_atr"]
    limit = price - direction * CONFIG["retrace_atr"] * atr
    actionable = pct >= CONFIG["min_pct"] and direction != 0
    side = "long" if direction > 0 else ("short" if direction < 0 else "flat")
    return {
        "symbol": symbol.upper(), "interval": interval,
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
    }


class AlertPayload(BaseModel):
    symbol: str
    direction: float
    entry: float
    stop: float
    target: float
    target_r: float = 3.0
    conf: float | None = None
    tf: str = "1h"
    note: str = ""


@app.post("/api/alert")
def alert_webhook(a: AlertPayload) -> dict:
    """Receive a TradingView indicator alert (JSON) and log it as a paper trade.

    Closes the loop: chart setup fires -> webhook -> journal -> forward score.
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
    symbols: list[str]


@app.post("/api/paper/scan")
def paper_scan_endpoint(req: ScanRequest) -> dict:
    from .paper import paper_scan
    logged = paper_scan(req.symbols, min_pct=CONFIG["min_pct"], target_r=CONFIG["target_r"],
                        stop_atr=CONFIG["stop_atr"], retrace_atr=CONFIG["retrace_atr"],
                        interval=CONFIG["interval"])
    return {"logged": [{"id": p.id, "symbol": p.symbol, "setup": p.setup,
                        "entry_limit": p.entry, "stop": p.stop, "target": p.target,
                        "status": p.status} for p in logged]}
