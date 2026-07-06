"""Kudbee Quant backend API — exposes the engine to the website (one unit).

Run:  uvicorn kudbee_quant.api:app --reload
The static site's Live Signals page calls these endpoints. Read-only by
default; the paper-scan endpoint logs to the local journal. Everything reflects
the VALIDATED config: 1h, >=50% confluence, 3R target, 0.25-ATR limit retrace.

Honesty note: signals are the engine's directional read with confidence
intervals from backtests — not advice, not a guarantee.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from pathlib import Path

import requests
from fastapi import (Depends, FastAPI, File, Form, Header, HTTPException, Query,
                     Request, UploadFile)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               RedirectResponse)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import api_runner, chart_review
from .alert_inbox import inbox_entry, log_alert, push_inbox_entry
from .api_auth import (COOKIE_NAME, DEFAULT_MAX_AGE, check_password, has_session,
                       issue_session, require_session)
from .api_security import RateLimiter, check_token, require_token, safe_spec, safe_symbol
from .config import get_secret
from .config.features import load_feature_flags
from .confluence.stack import confluence_score
from .confluence.trace import (EMA_SPAN_MAX, EMA_SPAN_MIN, FACTOR_KEYS,
                               factor_trace, sandbox_score)
from .ingest import BinanceClient, RouterClient
from .journal import TradeJournal
from .journal.chart_reviews import ChartReview, ChartReviewJournal
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

# Static assets (compiled Tailwind CSS + dashboard/login JS). Starlette ships
# StaticFiles — no new dependency. The Render-served dashboard references these
# same-origin so the CSP below can stay strict ('self', no inline, no CDN).
_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# The marketing site (Netlify) sets CSP via netlify.toml/_headers, but those do
# NOT cover this Render host, which serves the dashboard + login HTML. Set the
# matching policy here so the gated pages get the same protection. Also mark the
# private pages noindex (belt-and-braces with robots.txt + the page meta tag).
_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
        "object-src 'none'")
_NOINDEX_PATHS = {"/", "/dashboard", "/login"}


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("Content-Security-Policy", _CSP)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    if request.url.path in _NOINDEX_PATHS:
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


# Rate limiters: generous for public reads, tight for journal writes. The
# sandbox recompute gets its own scope so what-if spam can't starve the reads.
# Login + runner get their own tight scopes (brute-force / compute abuse).
_write_limit = RateLimiter(limit=10, window=60.0, scope="write")
_read_limit = RateLimiter(limit=120, window=60.0, scope="read")
_sandbox_limit = RateLimiter(limit=30, window=60.0, scope="sandbox")
_login_limit = RateLimiter(limit=5, window=60.0, scope="login")
_runner_limit = RateLimiter(limit=6, window=60.0, scope="runner")
# Chart review calls a paid vision API — keep it tight.
_chart_review_limit = RateLimiter(limit=6, window=60.0, scope="chart_review")

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
def journal(_rl: None = Depends(_read_limit)) -> dict:
    # PUBLIC endpoint (the marketing Lab page reads by_source/resolved_series/exposure).
    # Deliberately does NOT expose per-position entry/stop/target: exact live stop and
    # target levels are a stop-hunt / front-running vector, and neither the public Lab
    # nor the (session-gated) dashboard reads them here — the dashboard uses the gated
    # /api/open-trades for full position detail. Rate-limited like every other read
    # (it hits disk + runs several pandas groupbys per call).
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
                  "direction": p.direction, "created_at": p.created_at}
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


@app.post("/api/telegram")
async def telegram_webhook(request: Request) -> dict:
    """Two-way Telegram command webhook (paper-only). Three gates protect it:
    (2) the Telegram webhook secret header is verified HERE; (1) the chat-id
    whitelist and (3) the trade confirmation gate live in telegram_commands.
    Never touches a live exchange. See kudbee_quant/telegram_commands.py."""
    expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="forbidden")
    from .telegram_commands import handle_update
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")
    handle_update(body)                 # gate-1 whitelist + dispatch + reply
    return {"ok": True}


@app.get("/api/telegram/register-webhook")
def register_telegram_webhook(
    request: Request,
    token: str | None = Query(default=None),
    url: str | None = Query(default=None),
    x_api_token: str | None = Header(default=None),
    _rl: None = Depends(_write_limit),
) -> dict:
    """Self-register the Telegram webhook — no local secrets needed.

    Auth prefers the ``X-API-Token`` header (curl/scripts); a ``?token=`` query param
    is still accepted for a plain browser GET, but note it can land in access logs, so
    the header is recommended and, if the query form is ever used, rotate the token.
    The server calls Telegram ``setWebhook`` using the ``TELEGRAM_BOT_TOKEN`` already in
    the host env, pointing Telegram at this app's ``/api/telegram`` with the
    ``secret_token`` set to ``TELEGRAM_WEBHOOK_SECRET`` so the inbound gate passes.

    Idempotent — ``setWebhook`` can be called repeatedly. The bot token is NEVER echoed
    back. See docs/runbooks/telegram-setup.md.
    """
    check_token(x_api_token or token)  # header preferred; fail-closed (503 unset, 401 mismatch)
    bot = get_secret("TELEGRAM_BOT_TOKEN", required=False)
    if not bot:
        raise HTTPException(status_code=503, detail="TELEGRAM_BOT_TOKEN not configured")
    bot_token = bot.reveal()
    secret = get_secret("TELEGRAM_WEBHOOK_SECRET", required=False)
    secret_val = secret.reveal() if secret else ""

    # Resolve the public base URL: explicit ?url= wins, else API_ORIGIN (the
    # canonical public origin — same variable the Pages /api proxy uses), else
    # the Fly app's public hostname (Fly sets FLY_APP_NAME in every machine),
    # else this request's own base (correct behind Fly's TLS-terminating proxy
    # only because uvicorn runs with --proxy-headers; see Dockerfile). The old
    # RENDER_EXTERNAL_URL fallback is gone with Render (§80).
    fly_app = os.environ.get("FLY_APP_NAME")
    base = (
        url
        or os.environ.get("API_ORIGIN")
        or (f"https://{fly_app}.fly.dev" if fly_app else None)
        or str(request.base_url)
    ).rstrip("/")
    if not base.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail=f"refusing non-HTTPS webhook base {base!r}; pass ?url=https://<app>",
        )
    webhook_url = base if base.endswith("/api/telegram") else base + "/api/telegram"

    payload = {"url": webhook_url, "allowed_updates": ["message"]}
    if secret_val:
        payload["secret_token"] = secret_val
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook", json=payload, timeout=10
        )
        data = resp.json()
    except Exception as exc:  # never leak the token-bearing URL in the error
        raise HTTPException(
            status_code=502, detail=f"Telegram setWebhook failed: {type(exc).__name__}"
        ) from None
    return {
        "registered": bool(data.get("ok")),
        "webhook_url": webhook_url,
        "secret_set": bool(secret_val),
        "telegram_response": data,  # {ok, result, description} — no token in it
    }


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
def system_metrics(_rl: None = Depends(_read_limit),
                   _auth: None = Depends(require_session)) -> dict:
    """Host CPU/memory/disk of the machine serving the app — dashboard panel.
    Session-gated: host infra (real RAM/disk totals) is not public reconnaissance."""
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


# ---------------------------------------------------------------------------
# Read-only aggregate endpoints (session-gated — they feed the control center).
# Distinct from the public marketing reads above; these can surface the full
# track record, so they require a dashboard session.
# ---------------------------------------------------------------------------


@app.get("/api/open-trades")
def open_trades(_auth: None = Depends(require_session),
                _rl: None = Depends(_read_limit)) -> dict:
    """Every open/pending trade with live mark, MFE/MAE, health + portfolio block."""
    from .review import open_trades_report
    try:
        return open_trades_report()
    except Exception:
        raise HTTPException(status_code=502, detail="upstream data error") from None


class HistoryQuery(BaseModel):
    symbol: str | None = Field(default=None, max_length=30)
    status: str = Field(default="closed", pattern=r"^(closed|open|pending|hit|miss|cancelled|all)$")
    timeframe: str | None = Field(default=None, pattern=r"^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d)$")
    mode: str | None = Field(default=None, pattern=r"^(paper|live)$")
    date_from: str | None = Field(default=None, max_length=40)
    date_to: str | None = Field(default=None, max_length=40)


@app.get("/api/trade-history")
def trade_history(symbol: str | None = None, status: str = "closed",
                  timeframe: str | None = None, mode: str | None = None,
                  date_from: str | None = None, date_to: str | None = None,
                  _auth: None = Depends(require_session),
                  _rl: None = Depends(_read_limit)) -> dict:
    """Closed-trade detail + portfolio analytics. ``with_excursion`` is off so the
    dashboard never blocks on a network backfill."""
    from .review import trade_history_report
    try:
        q = HistoryQuery(symbol=symbol, status=status, timeframe=timeframe, mode=mode,
                         date_from=date_from, date_to=date_to)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    sym = safe_symbol(q.symbol) if q.symbol else None
    return trade_history_report(symbol=sym, status=q.status, timeframe=q.timeframe,
                                mode=q.mode, date_from=q.date_from, date_to=q.date_to,
                                with_excursion=False)


@app.get("/api/research")
def research(_auth: None = Depends(require_session),
             _rl: None = Depends(_read_limit)) -> dict:
    """Research outputs: overnight results, the FDR-corrected ledger, the latest
    market-regime reflection. Read-only; tolerates missing files."""
    import json as _json

    data_dir = Path(__file__).resolve().parent.parent / "data"

    def _load(name: str):
        fp = data_dir / name
        try:
            return _json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else None
        except Exception:
            return None

    out: dict = {"overnight_results": _load("overnight_results.json"),
                 "reflection": _load("reflection.json"), "ledger": None}
    try:
        from .memory.testing_ledger import family_ledger
        out["ledger"] = api_runner._jsonable(family_ledger())
    except Exception:
        out["ledger"] = None
    return out


# ---------------------------------------------------------------------------
# Curated runner (session-gated). See kudbee_quant/api_runner.py — whitelisted
# actions only, bounded params, async jobs, NEVER writes the journal.
# ---------------------------------------------------------------------------


@app.get("/api/run")
def runner_list(_auth: None = Depends(require_session),
                _rl: None = Depends(_read_limit)) -> dict:
    return {"actions": api_runner.list_actions(), "jobs": api_runner.list_jobs()}


@app.get("/api/run/{job_id}")
def runner_status(job_id: str, _auth: None = Depends(require_session),
                  _rl: None = Depends(_read_limit)) -> dict:
    job = api_runner.public_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


class RunRequest(BaseModel):
    params: dict = Field(default_factory=dict)


@app.post("/api/run/{action}")
def runner_submit(action: str, req: RunRequest,
                  _auth: None = Depends(require_session),
                  _rl: None = Depends(_runner_limit)) -> dict:
    from pydantic import ValidationError
    try:
        return api_runner.submit_job(action, req.params)
    except ValidationError as e:
        # Clean, JSON-safe field errors (pydantic ctx can hold raw exceptions).
        detail = [{"loc": list(err.get("loc", [])), "msg": str(err.get("msg"))}
                  for err in e.errors()]
        raise HTTPException(status_code=422, detail=detail) from e
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown action") from None
    except RuntimeError:
        raise HTTPException(status_code=429, detail="runner busy — try again shortly") from None


# ---------------------------------------------------------------------------
# Auth: shared-password login -> signed session cookie (see api_auth.py).
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=256)


@app.post("/api/login")
def login(req: LoginRequest, _rl: None = Depends(_login_limit)) -> JSONResponse:
    check_password(req.password)   # 503 if unconfigured, 401 on mismatch
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE_NAME, issue_session(), max_age=DEFAULT_MAX_AGE,
                    httponly=True, secure=True, samesite="lax", path="/")
    return resp


@app.post("/api/logout")
def logout() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


# --- AI chart review (dashboard-only; NEVER touches the live-execution path) ---
# Pipeline ends at a persisted chart_reviews.json record: an AI read of an
# uploaded chart that the operator acts on MANUALLY. No order is ever placed here.
_CHART_IMAGES_DIR = Path("data/chart_images")
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_HEX_ID = re.compile(r"^[0-9a-f]{8}$")
_IMAGE_MEDIA = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp",
                "gif": "image/gif"}


@app.post("/api/chart-review")
def chart_review_endpoint(image: UploadFile = File(...), symbol: str = Form(...),
                          timeframe: str = Form(""), notes: str = Form(""),
                          _auth: None = Depends(require_session),
                          _rl: None = Depends(_chart_review_limit)) -> dict:
    """Upload a chart -> server-side OpenAI vision read -> persisted record.
    Gated, default-OFF, and isolated from execution. Returns the structured read."""
    if not load_feature_flags().enable_ai_chart_review:
        raise HTTPException(status_code=503,
                            detail="chart review disabled (set ENABLE_AI_CHART_REVIEW=true)")
    content_type = (image.content_type or "").lower()
    if content_type not in chart_review.ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415,
                            detail="unsupported image type (png/jpeg/webp/gif only)")
    sym = safe_symbol(symbol)
    tf = timeframe.strip()
    if tf and tf not in _ALLOWED_TF:
        raise HTTPException(status_code=422, detail="invalid timeframe")
    data = image.file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty image upload")
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image exceeds 5MB limit")
    key = get_secret("OPENAI_API_KEY", required=False)
    if not key:
        raise HTTPException(status_code=503,
                            detail="chart review disabled (no OpenAI API key configured)")
    api_key = key.reveal() if hasattr(key, "reveal") else str(key)
    model = os.environ.get("OPENAI_CHART_REVIEW_MODEL", chart_review.DEFAULT_MODEL)
    try:
        review = chart_review.review_chart(data, content_type, sym, tf, notes,
                                           api_key=api_key, model=model)
    except chart_review.ChartReviewError as e:
        raise HTTPException(status_code=502, detail=f"chart review failed: {e}") from e

    rec = ChartReview(
        symbol=sym, timeframe=tf, notes=notes[:1000],
        image_sha256="sha256:" + hashlib.sha256(data).hexdigest(),
        image_size_bytes=len(data), ai_model_used=model, ai_review_json=review,
        bias=review["bias"], setup_name=review["setup_name"],
        confidence=review["confidence"], final_recommendation=review["final_recommendation"],
    )
    ext = chart_review.ALLOWED_CONTENT_TYPES[content_type]
    _CHART_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    img_path = _CHART_IMAGES_DIR / f"{rec.id}.{ext}"
    img_path.write_bytes(data)          # raw bytes live ONLY as the on-disk file
    rec.image_path = str(img_path)
    ChartReviewJournal().add(rec)
    return {"id": rec.id, "symbol": rec.symbol, "timeframe": rec.timeframe,
            "review": review, "ai_model_used": model, "created_at": rec.created_at,
            "image_sha256": rec.image_sha256}


@app.get("/api/chart-reviews")
def chart_reviews_list(_auth: None = Depends(require_session),
                       _rl: None = Depends(_read_limit)) -> dict:
    """Recent chart reviews (newest first) for the dashboard history list."""
    j = ChartReviewJournal()
    return {"reviews": [
        {"id": r.id, "symbol": r.symbol, "timeframe": r.timeframe, "bias": r.bias,
         "setup_name": r.setup_name, "confidence": r.confidence,
         "final_recommendation": r.final_recommendation, "ai_model_used": r.ai_model_used,
         "created_at": r.created_at, "review": r.ai_review_json,
         "has_image": bool(r.image_path and Path(r.image_path).exists())}
        for r in j.recent(50)
    ]}


@app.get("/api/chart-images/{review_id}")
def chart_image(review_id: str, _auth: None = Depends(require_session),
                _rl: None = Depends(_read_limit)):
    """Stream a stored chart image. Gated; hex-id guard blocks path traversal."""
    if not _HEX_ID.match(review_id):
        raise HTTPException(status_code=422, detail="invalid id")
    rec = ChartReviewJournal().get(review_id)
    if rec is None or not rec.image_path:
        raise HTTPException(status_code=404, detail="not found")
    p = Path(rec.image_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="image not found")
    media = _IMAGE_MEDIA.get(p.suffix.lstrip("."), "application/octet-stream")
    return FileResponse(str(p), media_type=media)


_LOGIN_FILE = _STATIC_DIR / "login.html"
_DASHBOARD_FILE = _STATIC_DIR / "dashboard.html"


@app.get("/login", include_in_schema=False)
def login_page(request: Request, _rl: None = Depends(_read_limit)):
    """Login form. If already authenticated, go straight to the dashboard."""
    if has_session(request):
        return RedirectResponse("/dashboard", status_code=302)
    return HTMLResponse(_LOGIN_FILE.read_text(encoding="utf-8"))


@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def dashboard(request: Request, _rl: None = Depends(_read_limit)):
    """Mission-control dashboard — gated. No session -> redirect to /login."""
    if not has_session(request):
        return RedirectResponse("/login", status_code=302)
    return HTMLResponse(_DASHBOARD_FILE.read_text(encoding="utf-8"))
