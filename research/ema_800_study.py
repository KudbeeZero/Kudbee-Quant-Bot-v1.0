"""800-EMA gate study — Phase 2 backtest (pre-registered).

Tests studies/800_ema_study_preregistration.md (committed to main BEFORE this
ran): on the validated top-10/1h crypto population, do signals with price ABOVE
the 800-EMA at the signal candle deliver higher net-R than signals BELOW it?

Reuses the live engine end to end (Binance loader + build_levels + confluence +
shared resolve_bracket geometry). The 800-EMA comes straight from build_levels'
`ema_800` column — no external fetch. The trade enumerator is fidelity-locked to
bracket_backtest (net-R reproduced exactly) in tests/test_ema_800_study.py.

PRE-REGISTERED GATE: ACCEPT iff n_above>=30 AND n_below>=30 AND
boot_p(ABOVE)<0.05 AND (mean_above - mean_baseline) > 0.02R. Else REJECT, inert.

Usage:  python research/ema_800_study.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "research"))
sys.path.insert(0, str(_REPO / "scripts"))

from kudbee_quant.backtest.resolver import resolve_bracket  # noqa: E402
from kudbee_quant.config.validated_defaults import (  # noqa: E402
    FEE_PCT,
    MAX_BARS,
    STOP_ATR,
    TARGET_R,
)

RETRACE_ATR = 0.25
ENTRY_WINDOW = 6
FEE = FEE_PCT

# Pre-registered gate constants (do NOT tune).
MIN_N = 30
IMPROVEMENT_MIN_R = 0.02

_OUT_MD = _REPO / "research" / "ema_800_study_results.md"
_OUT_CSV = _REPO / "research" / "ema_800_study_summary.csv"


def ema800_trades(df: pd.DataFrame, signal: pd.Series) -> list[dict]:
    """Enumerate validated baseline trades (bank-half@1R + BE + ride-3R via the
    shared resolver — net-R identical to bracket_backtest), tagging each with
    whether price was ABOVE/BELOW the 800-EMA at the signal candle."""
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    atr = df["atr"].to_numpy()
    ema = df["ema_800"].to_numpy()
    sig = pd.Series(signal, index=df.index).fillna(0.0).to_numpy()
    n = len(df)
    rows: list[dict] = []
    busy_until = -1
    for t in range(n - 1):
        if sig[t] == 0 or t <= busy_until:
            continue
        direction = 1.0 if sig[t] > 0 else -1.0
        sd = STOP_ATR * atr[t]
        if not np.isfinite(sd) or sd <= 0:
            continue
        limit = close[t] - direction * RETRACE_ATR * atr[t]
        ewin = min(t + ENTRY_WINDOW, n - 1)
        entry_bar = None
        for j in range(t + 1, ewin + 1):
            if (direction > 0 and low[j] <= limit) or (direction < 0 and high[j] >= limit):
                entry_bar = j
                break
        if entry_bar is None:
            continue
        entry = limit
        stop = entry - direction * sd
        target = entry + direction * sd * TARGET_R
        end = min(entry_bar + MAX_BARS, n - 1)
        hi = high[entry_bar + 1:end + 1]
        lo = low[entry_bar + 1:end + 1]
        cl = close[entry_bar + 1:end + 1]

        tp1 = entry + direction * sd * 1.0
        ob = resolve_bracket(direction, entry, stop, target, sd, TARGET_R, hi, lo, cl,
                             force_close_at_end=True, tp1=tp1, tp1_r=1.0, tp1_frac=0.5,
                             be_after_tp1=True)
        if ob.exit_offset is None:
            gross = direction * (close[end] - entry) / sd
            exit_b = end
        else:
            gross = ob.outcome_r
            exit_b = entry_bar + 1 + ob.exit_offset
        cost = FEE * entry / sd * (1 + 0.5 * 0.5)

        e = ema[t]
        if not np.isfinite(e):
            bucket = "excluded"          # 800-EMA warm-up
        elif close[t] > e:
            bucket = "above"
        elif close[t] < e:
            bucket = "below"
        else:
            bucket = "excluded"          # exactly on the EMA (degenerate)
        rows.append({
            "side": "long" if direction > 0 else "short",
            "net_r": float(gross - cost),
            "bucket": bucket,
        })
        busy_until = exit_b
    return rows


def _block(net: list[float], boot_p) -> dict:
    arr = np.asarray(net, dtype=float)
    if arr.size == 0:
        return {"n": 0, "mean_r": float("nan"), "win_rate": float("nan"),
                "total_r": 0.0, "boot_p": float("nan")}
    return {"n": int(arr.size), "mean_r": float(arr.mean()),
            "win_rate": float((arr > 0).mean()), "total_r": float(arr.sum()),
            "boot_p": float(boot_p(list(arr)))}


def study(cells, boot_p) -> dict:
    trades: list[dict] = []
    for _wk, _sym, df, sig in cells:
        trades.extend(ema800_trades(df, sig))
    tdf = pd.DataFrame(trades)
    above = tdf[tdf["bucket"] == "above"]["net_r"].tolist()
    below = tdf[tdf["bucket"] == "below"]["net_r"].tolist()
    base = tdf[tdf["bucket"] != "excluded"]["net_r"].tolist()  # baseline = all classified
    return {
        "cells": {
            "baseline (all classified)": _block(base, boot_p),
            "ABOVE 800-EMA": _block(above, boot_p),
            "BELOW 800-EMA": _block(below, boot_p),
            "ABOVE — long": _block(tdf[(tdf["bucket"] == "above") & (tdf["side"] == "long")]["net_r"].tolist(), boot_p),
            "ABOVE — short": _block(tdf[(tdf["bucket"] == "above") & (tdf["side"] == "short")]["net_r"].tolist(), boot_p),
            "BELOW — long": _block(tdf[(tdf["bucket"] == "below") & (tdf["side"] == "long")]["net_r"].tolist(), boot_p),
            "BELOW — short": _block(tdf[(tdf["bucket"] == "below") & (tdf["side"] == "short")]["net_r"].tolist(), boot_p),
        },
        "n_total": len(tdf),
        "n_excluded": int((tdf["bucket"] == "excluded").sum()) if len(tdf) else 0,
    }


def verdict(res: dict) -> str:
    base = res["cells"]["baseline (all classified)"]
    above = res["cells"]["ABOVE 800-EMA"]
    below = res["cells"]["BELOW 800-EMA"]
    if above["n"] == 0 or below["n"] == 0:
        return "REJECT — an empty bucket. 800-EMA gate NOT wired."
    improvement = above["mean_r"] - base["mean_r"]
    checks = [
        (above["n"] >= MIN_N, f"n_above={above['n']} (need >= {MIN_N})"),
        (below["n"] >= MIN_N, f"n_below={below['n']} (need >= {MIN_N})"),
        (np.isfinite(above["boot_p"]) and above["boot_p"] < 0.05,
         f"boot_p(ABOVE)={above['boot_p']:.3f} (need < 0.05)"),
        (improvement > IMPROVEMENT_MIN_R,
         f"improvement={improvement:+.3f}R vs baseline {base['mean_r']:+.3f}R (need > {IMPROVEMENT_MIN_R}R)"),
    ]
    passed = all(c for c, _ in checks)
    head = ("ACCEPT — all pre-registered gates pass. Next: wire as a READ-ONLY log "
            "flag in a SEPARATE PR (never an execution filter without further sign-off)."
            if passed else
            "REJECT — at least one pre-registered gate fails. 800-EMA gate NOT wired "
            "(hard rule; no post-hoc rescue).")
    body = "\n".join(f"  [{'PASS' if c else 'FAIL'}] {m}" for c, m in checks)
    extra = f"\n  (context) ABOVE-BELOW spread = {above['mean_r'] - below['mean_r']:+.3f}R"
    return head + "\n" + body + extra


def write_outputs(res: dict) -> None:
    cells = res["cells"]
    pd.DataFrame([{"cell": k, **v} for k, v in cells.items()]).to_csv(_OUT_CSV, index=False)
    lines = [
        "# 800-EMA gate study — results (pre-registered)",
        "",
        "Pre-registration: `studies/800_ema_study_preregistration.md` (merged to "
        "main before this run). Population = validated top-10/1h confluence trades, "
        "live bank-half/BE/ride-3R geometry, net of maker fees. 800-EMA from "
        "build_levels' `ema_800` column.",
        "",
        f"- Total trades: **{res['n_total']}** (excluded, 800-EMA warm-up/on-EMA: {res['n_excluded']})",
        "",
        "| bucket | n | mean R | win rate | total R | boot_p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for k, v in cells.items():
        mean = "—" if not np.isfinite(v["mean_r"]) else f"{v['mean_r']:+.3f}"
        win = "—" if not np.isfinite(v["win_rate"]) else f"{v['win_rate']:.0%}"
        bp = "—" if not np.isfinite(v["boot_p"]) else f"{v['boot_p']:.3f}"
        lines.append(f"| {k} | {v['n']} | {mean} | {win} | {v['total_r']:+.1f} | {bp} |")
    lines += ["", "## Verdict (pre-registered gate)", "", "```", verdict(res), "```", ""]
    _OUT_MD.write_text("\n".join(lines))
    print(f"wrote {_OUT_MD} and {_OUT_CSV}")


def main() -> None:
    import cycle_backtest as cyc  # noqa: PLC0415
    import trailing_sweep as ts  # noqa: PLC0415

    cells = ts.load_cells()
    res = study(cells, cyc.boot_p)
    write_outputs(res)
    print("\n" + verdict(res))


if __name__ == "__main__":
    main()
