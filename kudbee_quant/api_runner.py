"""Curated test runner — launch a WHITELISTED set of engine actions from the
logged-in dashboard, with bounded params and async jobs. NOT a code executor.

Why this is safe (the design brief was "control center, not RCE"):
  * Dispatch is a FIXED dict lookup (``_ACTIONS``); an unknown action is 422.
    There is no path that executes user-supplied code.
  * Every parameter goes through a Pydantic model with hard bounds, and every
    symbol through the shared ``parse_spec`` whitelist (SSRF/traversal guard).
  * Actions call importable ENGINE functions, never a shell.
  * The runner NEVER writes the journal: ``paper-scan`` here is dry-run only
    (``paper_scan(dry_run=True)``). A regression test asserts journal bytes are
    unchanged across a run.
  * Jobs run on a small thread pool (cap 2) so backtest spam can't starve the
    single uvicorn worker; new jobs are rejected (429) when the pool is full.

Honesty: results are EPHEMERAL (in-memory; lost on any process restart / Render
redeploy — and the hourly journal commit redeploys often), a backtest is a
single draw, and nothing here is added to the validated record.
"""
from __future__ import annotations

import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field, field_validator

from .ingest.router import parse_spec

_INTERVAL_RE = r"^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d)$"
_PERIODS_PER_YEAR = {
    "1m": 525_600, "3m": 175_200, "5m": 105_120, "15m": 35_040,
    "30m": 17_520, "1h": 8_760, "2h": 4_380, "4h": 2_190,
    "6h": 1_460, "8h": 1_095, "12h": 730, "1d": 365,
}

# Per-job wall-clock budget. A thread can't be force-killed in Python, so on
# timeout we mark the job failed and free the polling slot; the underlying
# compute may finish in the background (acceptable for a single-operator tool).
JOB_TIMEOUT_S = 150.0
_MAX_WORKERS = 2
_MAX_JOBS_KEPT = 50


# --- param validation helpers ------------------------------------------------


def _norm_spec(s: str) -> str:
    """Whitelist + normalize one symbol/spec, preserving the source prefix."""
    try:
        src, sym = parse_spec(s)
    except ValueError:
        raise ValueError(f"invalid symbol: {s!r}") from None
    return sym.upper() if src == "binance" else f"{src}:{sym.upper()}"


class _SymbolParam(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=30)
    interval: str = Field(default="1h", pattern=_INTERVAL_RE)

    @field_validator("symbol")
    @classmethod
    def _v(cls, v: str) -> str:
        return _norm_spec(v)


class BacktestParams(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=30)
    interval: str = Field(default="1h", pattern=_INTERVAL_RE)
    strategy: str = Field(default="pvsra", pattern=r"^(pvsra|pvsra_mm)$")
    limit: int = Field(default=1000, ge=100, le=1500)
    paths: int = Field(default=2000, ge=100, le=5000)
    long_only: bool = False

    @field_validator("symbol")
    @classmethod
    def _v(cls, v: str) -> str:
        return _norm_spec(v)


class _UniverseParams(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=8)
    interval: str = Field(default="1h", pattern=_INTERVAL_RE)
    limit: int = Field(default=2000, ge=200, le=4000)

    @field_validator("symbols")
    @classmethod
    def _v(cls, v: list[str]) -> list[str]:
        return [_norm_spec(s) for s in v]


class ValidateParams(_UniverseParams):
    strategy: str = Field(default="pvsra", pattern=r"^(pvsra|pvsra_mm)$")
    long_only: bool = False
    paths: int = Field(default=1000, ge=100, le=2000)


class SweepParams(_UniverseParams):
    hold: int = Field(default=12, ge=1, le=48)


class BracketSweepParams(_UniverseParams):
    target_r: float = Field(default=2.0, ge=0.5, le=10.0)
    stop_atr: float = Field(default=1.0, ge=0.25, le=5.0)
    max_bars: int = Field(default=24, ge=4, le=96)


class PaperScanParams(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=10)
    interval: str = Field(default="1h", pattern=_INTERVAL_RE)
    min_pct: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("symbols")
    @classmethod
    def _v(cls, v: list[str]) -> list[str]:
        return [_norm_spec(s) for s in v]


# --- JSON serialization (dataclasses / pandas / numpy -> plain JSON) ----------


def _jsonable(x: Any) -> Any:
    if x is None or isinstance(x, (bool, int, str)):
        return x
    if isinstance(x, float):
        return x
    if is_dataclass(x) and not isinstance(x, type):
        return _jsonable(asdict(x))
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    # pandas / numpy without importing them eagerly
    mod = type(x).__module__
    if mod.startswith("pandas"):
        if hasattr(x, "to_dict"):
            try:
                return _jsonable(x.to_dict(orient="records"))  # DataFrame
            except TypeError:
                return _jsonable(x.to_dict())                   # Series
    if mod.startswith("numpy"):
        if hasattr(x, "item"):
            return x.item()
        if hasattr(x, "tolist"):
            return x.tolist()
    return str(x)


# --- action implementations (each returns a JSON-able dict) ------------------


def _strategy_fn(name: str, long_only: bool) -> Callable:
    from .backtest import pvsra_mm_positions, pvsra_positions
    if name == "pvsra":
        return lambda d: pvsra_positions(d, allow_short=not long_only)
    return lambda d: pvsra_mm_positions(d, allow_short=not long_only)


def _act_signal(p: _SymbolParam) -> dict:
    from .confluence.stack import confluence_score
    from .ingest import RouterClient
    from .levels import build_levels
    f = build_levels(RouterClient().klines(p.symbol, interval=p.interval, limit=600))
    last = confluence_score(f).iloc[-1]
    pct, direction = float(last["confluence_pct"]), int(last["direction"])
    return {
        "symbol": p.symbol, "interval": p.interval,
        "timestamp": str(last["timestamp"]), "price": round(float(last["close"]), 6),
        "confluence_pct": round(pct, 3), "direction": direction,
        "side": "long" if direction > 0 else ("short" if direction < 0 else "flat"),
        "strength": int(last["strength"]), "n_factors": int(last["n_factors"]),
    }


def _act_backtest(p: BacktestParams) -> dict:
    from .backtest import BacktestConfig, monte_carlo, run_backtest
    from .ingest import load_ohlcv
    df = load_ohlcv(p.symbol, interval=p.interval, limit=p.limit)
    config = BacktestConfig(
        periods_per_year=_PERIODS_PER_YEAR.get(p.interval, 8_760),
        allow_short=not p.long_only,
    )
    positions = _strategy_fn(p.strategy, p.long_only)(df)
    result = run_backtest(df, positions, config)
    mc = monte_carlo(result.returns, n_paths=p.paths)
    return {
        "symbol": p.symbol, "interval": p.interval, "strategy": p.strategy,
        "metrics": _jsonable(result.metrics.to_dict()),
        "monte_carlo": _jsonable(mc.to_dict()),
        "caveat": "Single backtest = one draw. Read the Monte Carlo bad percentiles, "
                  "not just the headline return. Not added to the validated record.",
    }


def _act_validate(p: ValidateParams) -> dict:
    from .backtest import BacktestConfig
    from .validation import validate_universe
    config = BacktestConfig(
        periods_per_year=_PERIODS_PER_YEAR.get(p.interval, 8_760),
        allow_short=not p.long_only,
    )
    report = validate_universe(p.symbols, _strategy_fn(p.strategy, p.long_only),
                               interval=p.interval, limit=p.limit, config=config,
                               mc_paths=p.paths)
    return {"interval": p.interval, "strategy": p.strategy, "report": _jsonable(report)}


def _act_sweep(p: SweepParams) -> dict:
    from .scenarios import run_sweep
    table = run_sweep(p.symbols, interval=p.interval, limit=p.limit, hold_n=p.hold)
    return {"interval": p.interval, "hold": p.hold, "scenarios": _jsonable(table)}


def _act_bracket_sweep(p: BracketSweepParams) -> dict:
    from .scenarios import run_bracket_sweep
    table = run_bracket_sweep(p.symbols, interval=p.interval, limit=p.limit,
                              target_r=p.target_r, stop_atr=p.stop_atr, max_bars=p.max_bars)
    return {"interval": p.interval, "target_r": p.target_r, "stop_atr": p.stop_atr,
            "scenarios": _jsonable(table)}


def _act_paper_scan(p: PaperScanParams) -> dict:
    from .paper import paper_scan
    preds = paper_scan(p.symbols, min_pct=p.min_pct, interval=p.interval, dry_run=True)
    return {
        "interval": p.interval, "min_pct": p.min_pct,
        "signals": _jsonable(preds),
        "caveat": "DRY RUN — nothing was logged to the journal. Preview only.",
    }


# action -> (param model, callable, human label)
_ACTIONS: dict[str, tuple[type[BaseModel], Callable, str]] = {
    "signal": (_SymbolParam, _act_signal, "Live confluence signal"),
    "backtest": (BacktestParams, _act_backtest, "Backtest + Monte Carlo"),
    "validate": (ValidateParams, _act_validate, "Walk-forward universe validation"),
    "sweep": (SweepParams, _act_sweep, "Scenario sweep (OOS Sharpe)"),
    "bracket-sweep": (BracketSweepParams, _act_bracket_sweep, "Bracket sweep (R expectancy)"),
    "paper-scan": (PaperScanParams, _act_paper_scan, "Paper scan (DRY RUN)"),
}


def list_actions() -> list[dict]:
    """Whitelist + JSON schema for each action (drives the UI form)."""
    return [{"action": name, "label": label, "params": model.model_json_schema()}
            for name, (model, _fn, label) in _ACTIONS.items()]


# --- job registry + execution ------------------------------------------------

_EXECUTOR = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="kq-runner")
_JOBS: dict[str, dict] = {}


def _active_count() -> int:
    return sum(1 for j in _JOBS.values() if j["status"] in ("queued", "running"))


def _prune() -> None:
    if len(_JOBS) <= _MAX_JOBS_KEPT:
        return
    done = sorted((j for j in _JOBS.values() if j["status"] not in ("queued", "running")),
                  key=lambda j: j.get("finished") or 0)
    for j in done[: len(_JOBS) - _MAX_JOBS_KEPT]:
        _JOBS.pop(j["id"], None)


def _worker(job_id: str, fn: Callable, params: BaseModel) -> None:
    job = _JOBS[job_id]
    job["status"] = "running"
    try:
        job["result"] = fn(params)
        job["status"] = "done"
    except Exception as e:  # never leak a traceback to the client
        job["error"] = f"{type(e).__name__}: {e}"
        job["status"] = "error"
    finally:
        job["finished"] = time.time()


def submit_job(action: str, raw_params: dict) -> dict:
    """Validate + enqueue a job. Returns the job record (status 'queued')."""
    if action not in _ACTIONS:
        raise ValueError("unknown action")
    if _active_count() >= _MAX_WORKERS:
        raise RuntimeError("runner busy")
    model, fn, _label = _ACTIONS[action]
    params = model(**(raw_params or {}))   # ValidationError -> 422 at the route
    job_id = secrets.token_hex(8)
    _JOBS[job_id] = {"id": job_id, "action": action, "status": "queued",
                     "result": None, "error": None,
                     "started": time.time(), "finished": None}
    _prune()
    _EXECUTOR.submit(_worker, job_id, fn, params)
    return public_job(job_id)


def public_job(job_id: str) -> dict | None:
    job = _JOBS.get(job_id)
    if job is None:
        return None
    # Watchdog: a still-running job past its budget is reported timed_out.
    if job["status"] in ("queued", "running") and time.time() - job["started"] > JOB_TIMEOUT_S:
        job["status"] = "error"
        job["error"] = f"timed out after {int(JOB_TIMEOUT_S)}s"
        job["finished"] = time.time()
    return {k: job[k] for k in ("id", "action", "status", "result", "error", "started", "finished")}


def list_jobs() -> list[dict]:
    return sorted((public_job(j) for j in list(_JOBS)),
                  key=lambda j: j["started"], reverse=True)


def _reset_jobs() -> None:   # test helper
    _JOBS.clear()
