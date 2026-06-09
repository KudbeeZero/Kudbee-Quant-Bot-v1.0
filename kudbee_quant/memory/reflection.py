"""L6 — Reflective memory: the layer that critiques the other layers.

It does three honest things, none of which any single experiment does for itself:
  1. REGIME STATE — what market are we even in right now (trend / volatility /
     chop), so a result is read in context, not as a universal truth.
  2. OVERFIT ALARMS — cross-checks the experiment log (L3) against the
     multiple-testing ledger: how many "winners" survive multiplicity, and which
     winners are unstable across the split-halves (a classic overfit tell).
  3. FAILURE ROLLUP — groups the dead/null ideas by theme, so we can SEE the
     pattern ("every volume-confirmation idea has failed") instead of re-deriving
     it. This is how the project avoids re-testing dead ends (docs/MEMORY.md §2).

``reflect()`` writes ``data/reflection.json`` and appends a dated note to
docs/MEMORY.md — wiring L6 back into L1 so the lesson layer stays current.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .testing_ledger import family_ledger

REFLECTION_PATH = Path("data/reflection.json")
MEMORY_PATH = Path("docs/MEMORY.md")
_THEMES = {
    "volatility": ("vol", "atr", "coil", "contraction", "expansion", "shock"),
    "trend/regime": ("trend", "ema", "clean", "slope", "variance_ratio", "autocorr", "momentum"),
    "volume": ("vol_", "relvol", "volume", "climax", "dryup"),
    "execution": ("retrace", "timestop", "stop", "target", "trail", "decay", "entry_window", "giveup"),
    "structure/level": ("round", "swing", "structural", "near_high", "inside", "pullback", "streak", "jump"),
    "sizing": ("size", "voltarget", "confluence"),
}


def regime_state(df: pd.DataFrame) -> dict:
    """Classify the CURRENT regime from a feature frame (build_levels output)."""
    last = df.iloc[-1]
    atr_pct = (df["atr"] / df["close"]).replace([np.inf, -np.inf], np.nan)
    vol_rank = float((atr_pct.iloc[-1] >= atr_pct.tail(500)).mean())
    trend = "flat"
    if {"close", "ema_800"} <= set(df.columns):
        slope = df["ema_50"].diff().iloc[-1] if "ema_50" in df.columns else 0.0
        if last["close"] > last["ema_800"] and slope > 0:
            trend = "up"
        elif last["close"] < last["ema_800"] and slope < 0:
            trend = "down"
    choppy = False
    if {"ema_50", "ema_800", "atr"} <= set(df.columns):
        choppy = bool(abs(last["ema_50"] - last["ema_800"]) < last["atr"])
    return {"trend": trend,
            "vol_regime": "high" if vol_rank > 0.66 else ("low" if vol_rank < 0.33 else "mid"),
            "vol_percentile": round(vol_rank, 3),
            "choppy": choppy}


def overfit_alarms(ledger: dict, results_path: Path | str = "data/overnight_results.json") -> dict:
    """Cross-check naive winners vs FDR survivors + flag unstable winners."""
    summary = ledger.get("summary", {})
    unstable = []
    p = Path(results_path)
    if p.exists():
        latest = {r["name"]: r for r in json.loads(p.read_text()).get("results", [])}
        for name, r in latest.items():
            if r.get("verdict") == "WINNER":
                h1, h2 = r.get("h1_delta", 0), r.get("h2_delta", 0)
                # a "winner" whose two halves disagree wildly in magnitude is shaky
                if min(h1, h2) <= 0 or (max(abs(h1), abs(h2)) > 4 * (min(abs(h1), abs(h2)) + 1e-9)):
                    unstable.append({"name": name, "h1": h1, "h2": h2})
    n = summary.get("n_candidates", 0)
    naive = summary.get("naive_winners", 0)
    survivors = summary.get("fdr_survivors", 0)
    return {
        "n_candidates": n,
        "naive_winners": naive,
        "fdr_survivors": survivors,
        "expected_false_winners_if_all_null": round(0.05 * n, 1),
        "unstable_winners": unstable,
        "verdict": ("winners survive multiplicity" if survivors > 0
                    else "NO winner survives family-wide FDR — treat all as unproven"),
    }


def failure_rollup(results_path: Path | str = "data/overnight_results.json") -> dict:
    """Count failed/neutral ideas by theme — so the dead-end pattern is visible."""
    p = Path(results_path)
    if not p.exists():
        return {}
    latest = {r["name"]: r for r in json.loads(p.read_text()).get("results", [])}
    out = {t: {"failed": 0, "winner": 0} for t in _THEMES}
    for name, r in latest.items():
        themes = [t for t, keys in _THEMES.items() if any(k in name for k in keys)] or ["other"]
        for t in themes:
            out.setdefault(t, {"failed": 0, "winner": 0})
            if r.get("verdict") in ("HURTS", "NEUTRAL", "THIN"):
                out[t]["failed"] += 1
            elif r.get("verdict") == "WINNER":
                out[t]["winner"] += 1
    return out


def reflect(df: pd.DataFrame | None = None, write_memory: bool = True) -> dict:
    """Assemble the full reflection, persist it, and append a note to MEMORY.md."""
    ledger = family_ledger()
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "regime": regime_state(df) if df is not None else None,
        "ledger_summary": ledger.get("summary", {}),
        "overfit_alarms": overfit_alarms(ledger),
        "failure_rollup": failure_rollup(),
    }
    REFLECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    REFLECTION_PATH.write_text(json.dumps(report, indent=2))
    if write_memory and MEMORY_PATH.exists():
        oa = report["overfit_alarms"]
        note = (f"\n> _Reflection {report['generated_at']}_: "
                f"{oa['n_candidates']} candidates tried, {oa['naive_winners']} naive "
                f"winners, {oa['fdr_survivors']} survive family-wide FDR. "
                f"{oa['verdict']}."
                + (f" Regime: {report['regime']}." if report['regime'] else "") + "\n")
        with MEMORY_PATH.open("a") as fh:
            fh.write(note)
    return report
