"""Per-factor trace + sandbox recompute for the confluence stack (pure, no I/O).

The visualizer ("trade flow" page / `trade-trace` CLI) needs three things the
stack doesn't expose: WHICH factor voted which way on a bar, a human-readable
one-liner explaining each vote, and a what-if recompute with overridden EMA
spans or a factor subset. This module decorates ``factor_votes`` — it NEVER
forks the vote logic. Votes always come from ``factor_votes(df)`` verbatim;
a parity test (tests/test_trace.py) pins that guarantee.

The sandbox is an UNVALIDATED display-only experiment: it never reads the
validated defaults, never writes the journal, never feeds the paper scan.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from .stack import factor_votes


def _fmt(x) -> str:
    """Compact human number: 63150.123 -> '63,150.1'; NaN/None -> 'n/a'."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "n/a"
    if math.isnan(v):
        return "n/a"
    return format(v, ",.6g")


def _num(row: pd.Series, col: str):
    """Float value of a column on a row, or None if absent/NaN."""
    if col not in row.index:
        return None
    try:
        v = float(row[col])
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _cmp(a, b) -> str:
    if a is None or b is None:
        return "vs"
    return ">" if a > b else ("<" if a < b else "=")


# --- per-factor detail builders (read-only on a levels row) -------------------


def _d_emastack(r: pd.Series) -> str:
    c, e50, e800 = _num(r, "close"), _num(r, "ema_50"), _num(r, "ema_800")
    if None in (c, e50, e800):
        return "EMA stack unavailable (insufficient history)"
    if c > e50 > e800:
        tag = "stacked bullish"
    elif c < e50 < e800:
        tag = "stacked bearish"
    else:
        tag = "mixed — no stack"
    return f"close {_fmt(c)} {_cmp(c, e50)} EMA50 {_fmt(e50)} {_cmp(e50, e800)} EMA800 {_fmt(e800)} — {tag}"


def _d_emafast(r: pd.Series) -> str:
    e13, e50 = _num(r, "ema_13"), _num(r, "ema_50")
    if None in (e13, e50):
        return "fast EMAs unavailable"
    word = "up" if e13 > e50 else ("down" if e13 < e50 else "flat")
    return f"EMA13 {_fmt(e13)} {_cmp(e13, e50)} EMA50 {_fmt(e50)} — fast momentum {word}"


def _d_cloud(r: pd.Series) -> str:
    e13, e50, pos = _num(r, "ema_13"), _num(r, "ema_50"), _num(r, "ema_cloud_pos")
    if pos is None:
        return "EMA cloud unavailable"
    lo, hi = (min(e13, e50), max(e13, e50)) if None not in (e13, e50) else (None, None)
    where = "above" if pos > 0 else ("below" if pos < 0 else "inside")
    return f"close {where} the 13/50 cloud [{_fmt(lo)} … {_fmt(hi)}]"


def _d_vwap(r: pd.Series) -> str:
    c, vw = _num(r, "close"), _num(r, "vwap")
    if vw is None:
        return "session VWAP unavailable (no volume on this feed)"
    return f"close {_fmt(c)} {_cmp(c, vw)} session VWAP {_fmt(vw)}"


def _d_dopen(r: pd.Series) -> str:
    c, do = _num(r, "close"), _num(r, "daily_open")
    if do is None:
        return "daily open unavailable"
    return f"close {_fmt(c)} {_cmp(c, do)} daily open {_fmt(do)}"


def _d_pivot(r: pd.Series) -> str:
    c, pp = _num(r, "close"), _num(r, "pivot_pp")
    if pp is None:
        return "floor pivot unavailable"
    return f"close {_fmt(c)} {_cmp(c, pp)} pivot PP {_fmt(pp)}"


def _d_pd(r: pd.Series) -> str:
    c, mid = _num(r, "close"), _num(r, "dealing_mid")
    if mid is None:
        return "dealing range unavailable"
    if c > mid:   # vote is INVERTED: premium favors shorts, discount favors longs
        return f"close in PREMIUM (above dealing mid {_fmt(mid)}) → short bias"
    if c < mid:
        return f"close in DISCOUNT (below dealing mid {_fmt(mid)}) → long bias"
    return f"close at the dealing mid {_fmt(mid)} — neutral"


def _d_sweep(r: pd.Series) -> str:
    sb = _num(r, "sweep_bias")
    if sb is None:
        return "sweep bias unavailable"
    if sb > 0:
        return "swept a prior LOW — bullish sweep bias"
    if sb < 0:
        return "swept a prior HIGH — bearish sweep bias"
    return "no liquidity sweep on this bar"


def _d_vector(r: pd.Series) -> str:
    v = r.get("vector") if "vector" in r.index else None
    if v == "bull_climax":
        return "PVSRA vector: BULL climax candle"
    if v == "bear_climax":
        return "PVSRA vector: BEAR climax candle"
    return f"no climax vector (vector: {v if isinstance(v, str) and v else 'none'})"


def _d_fvg(r: pd.Series) -> str:
    lo, hi = _num(r, "low"), _num(r, "high")
    bt, bb = _num(r, "bull_fvg_top"), _num(r, "bull_fvg_bottom")
    st, sb = _num(r, "bear_fvg_top"), _num(r, "bear_fvg_bottom")
    # Mirror the vote's precedence: bull-FVG touch wins over bear-FVG touch.
    if None not in (lo, hi, bt, bb) and lo <= bt and hi >= bb:
        return f"bar [{_fmt(lo)} … {_fmt(hi)}] tags bull FVG [{_fmt(bb)} … {_fmt(bt)}]"
    if None not in (lo, hi, st, sb) and hi >= sb and lo <= st:
        return f"bar [{_fmt(lo)} … {_fmt(hi)}] tags bear FVG [{_fmt(sb)} … {_fmt(st)}]"
    return "no FVG touch on this bar"


def _vals(*cols: str) -> Callable[[pd.Series], dict]:
    def get(r: pd.Series) -> dict:
        return {c: _num(r, c) for c in cols if c in r.index}
    return get


def _vals_vector(r: pd.Series) -> dict:
    v = r.get("vector") if "vector" in r.index else None
    return {"vector": v if isinstance(v, str) else None}


@dataclass(frozen=True)
class FactorSpec:
    key: str                              # vote column from factor_votes
    short: str                            # 3-char CLI column header
    label: str
    group: str                            # trend | level | smart_money
    requires: tuple[str, ...]             # mirrors the column guard in factor_votes
    detail: Callable[[pd.Series], str]
    values: Callable[[pd.Series], dict]


FACTOR_SPECS: tuple[FactorSpec, ...] = (
    FactorSpec("v_emastack", "stk", "EMA Stack (50/800)", "trend",
               ("close", "ema_50", "ema_800"), _d_emastack, _vals("close", "ema_50", "ema_800")),
    FactorSpec("v_emafast", "fst", "EMA Momentum (13/50)", "trend",
               ("ema_13", "ema_50"), _d_emafast, _vals("ema_13", "ema_50")),
    FactorSpec("v_cloud", "cld", "EMA Cloud (13-50)", "trend",
               ("ema_cloud_pos",), _d_cloud, _vals("close", "ema_13", "ema_50", "ema_cloud_pos")),
    FactorSpec("v_vwap", "vwp", "Session VWAP", "level",
               ("close", "vwap"), _d_vwap, _vals("close", "vwap")),
    FactorSpec("v_dopen", "dop", "Daily Open", "level",
               ("close", "daily_open"), _d_dopen, _vals("close", "daily_open")),
    FactorSpec("v_pivot", "piv", "Floor Pivot", "level",
               ("close", "pivot_pp"), _d_pivot, _vals("close", "pivot_pp")),
    FactorSpec("v_pd", "pd ", "Premium / Discount", "smart_money",
               ("dealing_mid",), _d_pd, _vals("close", "dealing_mid", "pd_pos")),
    FactorSpec("v_sweep", "swp", "Liquidity Sweep", "smart_money",
               ("sweep_bias",), _d_sweep, _vals("sweep_bias")),
    FactorSpec("v_vector", "vec", "PVSRA Vector", "smart_money",
               ("vector",), _d_vector, _vals_vector),
    FactorSpec("v_fvg", "fvg", "Fair Value Gap", "smart_money",
               ("bull_fvg_bottom", "bull_fvg_top", "bear_fvg_top", "bear_fvg_bottom"),
               _d_fvg, _vals("low", "high", "bull_fvg_bottom", "bull_fvg_top",
                             "bear_fvg_top", "bear_fvg_bottom")),
)

FACTOR_KEYS: tuple[str, ...] = tuple(s.key for s in FACTOR_SPECS)

_EMA_OVERRIDE_KEYS = ("ema_13", "ema_50", "ema_800")
EMA_SPAN_MIN, EMA_SPAN_MAX = 2, 2000


def _jsonable(obj):
    """Recursively convert numpy scalars / NaN so FastAPI can serialize."""
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return None if math.isnan(v) else v
    return obj


def factor_trace(levels: pd.DataFrame, bars: int = 1,
                 keys: list[str] | None = None,
                 votes: pd.DataFrame | None = None,
                 indices: list | None = None) -> list[dict]:
    """Per-bar factor breakdown for the last ``bars`` rows (or explicit indices).

    Votes come from ``factor_votes(levels)`` verbatim — this only decorates
    them with labels/details. A factor whose columns are absent on this feed
    is reported with ``vote: None`` and excluded from ``n_factors``, exactly
    matching ``confluence_score`` (which only counts present vote columns).
    """
    if votes is None:
        votes = factor_votes(levels)
    if keys is not None:
        votes = votes[[k for k in votes.columns if k in keys]]
    specs = FACTOR_SPECS if keys is None else tuple(s for s in FACTOR_SPECS if s.key in keys)
    n_factors = max(votes.shape[1], 1)
    net = votes.sum(axis=1)
    idx = list(indices) if indices is not None else list(levels.index[-bars:])

    rows = []
    for i in idx:
        row = levels.loc[i]
        factors = []
        for spec in specs:
            if spec.key in votes.columns:
                vote = int(votes.at[i, spec.key])
                factors.append({"key": spec.key, "label": spec.label, "group": spec.group,
                                "vote": vote, "detail": spec.detail(row),
                                "values": _jsonable(spec.values(row))})
            else:
                factors.append({"key": spec.key, "label": spec.label, "group": spec.group,
                                "vote": None, "detail": "not available for this symbol",
                                "values": {}})
        ns = int(net.loc[i])
        rows.append({
            "timestamp": str(row["timestamp"]) if "timestamp" in row.index else str(i),
            "close": _jsonable(row.get("close")),
            "atr": _jsonable(row.get("atr")),
            "factors": factors,
            "net_score": ns, "strength": abs(ns), "n_factors": n_factors,
            "confluence_pct": abs(ns) / n_factors,
            "direction": int(np.sign(ns)),
        })
    return rows


def apply_ema_overrides(levels: pd.DataFrame, spans: dict[str, int]) -> pd.DataFrame:
    """Copy of ``levels`` with chosen EMA columns recomputed at new spans.

    Same formula as levels/builder.py (close.ewm(span, adjust=False)), and the
    13/50 cloud position is rebuilt because it derives from those two EMAs.
    Column NAMES are kept so factor_votes works unchanged — callers display
    the effective spans separately. UNVALIDATED: for the sandbox only.
    """
    bad = set(spans) - set(_EMA_OVERRIDE_KEYS)
    if bad:
        raise ValueError(f"unknown EMA override keys: {sorted(bad)}")
    for k, v in spans.items():
        if not (isinstance(v, (int, np.integer)) and EMA_SPAN_MIN <= int(v) <= EMA_SPAN_MAX):
            raise ValueError(f"{k} span must be an int in [{EMA_SPAN_MIN}, {EMA_SPAN_MAX}]")
    out = levels.copy()
    if not spans:
        return out
    for k, span in spans.items():
        out[k] = out["close"].ewm(span=int(span), adjust=False).mean()
    if {"ema_13", "ema_50"} <= set(out.columns):
        cloud_hi = out[["ema_13", "ema_50"]].max(axis=1)
        cloud_lo = out[["ema_13", "ema_50"]].min(axis=1)
        out["ema_cloud_pos"] = np.where(out["close"] > cloud_hi, 1,
                                        np.where(out["close"] < cloud_lo, -1, 0))
    return out


def sandbox_score(levels: pd.DataFrame, *,
                  ema_spans: dict[str, int] | None = None,
                  enabled: list[str] | None = None,
                  min_pct: float = 0.5,
                  bars: int = 1) -> dict:
    """UNVALIDATED what-if recompute: overridden EMA spans and/or a factor
    subset. Pure — never reads validated defaults, never writes anything;
    ``min_pct`` is a DISPLAY gate for the sandbox graph only.
    """
    if enabled is not None:
        unknown = set(enabled) - set(FACTOR_KEYS)
        if unknown:
            raise ValueError(f"unknown factors: {sorted(unknown)}")
        if not enabled:
            raise ValueError("at least one factor must be enabled")
    df = apply_ema_overrides(levels, ema_spans or {})
    rows = factor_trace(df, bars=bars, keys=list(enabled) if enabled is not None else None)
    last = rows[-1]
    return {
        "bars": rows,
        "params": {"ema": dict(ema_spans or {}),
                   "factors": list(enabled) if enabled is not None else list(FACTOR_KEYS),
                   "min_pct": float(min_pct)},
        "gate": {"min_pct": float(min_pct),
                 "passed": bool(last["confluence_pct"] >= min_pct and last["direction"] != 0),
                 "direction": last["direction"]},
        "unvalidated": True,
    }
