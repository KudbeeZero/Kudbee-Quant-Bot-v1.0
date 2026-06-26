"""VAH trap-reversal study — read-only, PRE-REGISTERED.

Tests the hypothesis in docs/research/vah_trap_reversal_preregistration.md (locked
BEFORE this code/results existed): on the validated top-10/1h population, signals
within 0.5*ATR of the PRIOR session's Value Area High AND showing a VAH rejection
candle (poke above, close back below) deliver higher net-R than the full
population baseline.

Reuses the live engine end to end (Binance loader + build_levels +
confluence_position + the shared resolve_bracket geometry). The trade enumerator
is fidelity-locked to bracket_backtest in tests/test_vah_trap_reversal.py — the
per-trade net-R reproduces the engine baseline EXACTLY; this file only *tags*
each trade with its VAH context.

GATE (pre-registered): ACCEPT iff n_qualifying>=30 AND boot_p<0.05 AND
(mean_qualifying - mean_baseline) > 0.02R. Else REJECT and do NOT wire.

Usage:  python research/vah_trap_reversal.py
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

# Entry geometry (mirror the live bracket exactly).
RETRACE_ATR = 0.25
ENTRY_WINDOW = 6
FEE = FEE_PCT

# Pre-registered parameters (see the pre-registration doc — do NOT tune).
PROFILE_BINS = 50
VALUE_AREA_FRAC = 0.70
PROXIMITY_ATR = 0.5
IMPROVEMENT_MIN_R = 0.02
MIN_N = 30

_OUT_MD = _REPO / "research" / "vah_trap_reversal_results.md"
_OUT_CSV = _REPO / "research" / "vah_trap_reversal_summary.csv"


# ── volume profile → VAH ──────────────────────────────────────────────────────

def session_vah(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                vol: np.ndarray, bins: int = PROFILE_BINS,
                va_frac: float = VALUE_AREA_FRAC) -> float:
    """Value Area High of one session's 1h bars (volume at typical price, 70%
    value area expanded from the POC). NaN if the session is degenerate."""
    lo, hi = float(np.min(low)), float(np.max(high))
    total = float(np.sum(vol))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo or total <= 0:
        return float("nan")
    edges = np.linspace(lo, hi, bins + 1)
    tp = (high + low + close) / 3.0
    idx = np.clip(np.digitize(tp, edges) - 1, 0, bins - 1)
    vol_bins = np.zeros(bins)
    np.add.at(vol_bins, idx, vol)
    poc = int(np.argmax(vol_bins))
    lo_i = hi_i = poc
    cum = vol_bins[poc]
    target = va_frac * total
    while cum < target:
        left = vol_bins[lo_i - 1] if lo_i > 0 else -1.0
        right = vol_bins[hi_i + 1] if hi_i < bins - 1 else -1.0
        if left < 0 and right < 0:
            break
        if right >= left:
            hi_i += 1
            cum += vol_bins[hi_i]
        else:
            lo_i -= 1
            cum += vol_bins[lo_i]
    return float(edges[hi_i + 1])   # upper edge of the value-area band


def prior_session_vah_array(df: pd.DataFrame) -> np.ndarray:
    """Per-bar prior-session VAH: each bar gets the VAH of the previous UTC day.
    Bars on the first day (no prior) get NaN."""
    day = df["utc_date"].astype(str).to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    vol = df["volume"].to_numpy()
    order = list(dict.fromkeys(day.tolist()))           # unique days, first-seen order
    vah_by_day: dict[str, float] = {}
    for d in order:
        m = day == d
        vah_by_day[d] = session_vah(high[m], low[m], close[m], vol[m])
    prev_vah = {d: vah_by_day[order[i - 1]] for i, d in enumerate(order) if i >= 1}
    return np.array([prev_vah.get(d, float("nan")) for d in day], dtype=float)


# ── trade enumeration with VAH tagging (fidelity-locked baseline) ─────────────

def vah_trades(df: pd.DataFrame, signal: pd.Series, prior_vah: np.ndarray) -> list[dict]:
    """Enumerate validated baseline trades (bank-half@1R + BE + ride-3R via the
    SHARED resolver — identical net-R to bracket_backtest), tagging each with its
    prior-session-VAH context at the signal bar."""
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    atr = df["atr"].to_numpy()
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
        net = float(gross - cost)

        pv = float(prior_vah[t])
        proximity = np.isfinite(pv) and abs(entry - pv) <= PROXIMITY_ATR * atr[t]
        rejection = np.isfinite(pv) and high[t] > pv and close[t] < pv
        rows.append({
            "side": "long" if direction > 0 else "short",
            "net_r": net,
            "near_vah": bool(proximity),
            "rejection": bool(proximity and rejection),   # qualifying = proximity AND rejection
        })
        busy_until = exit_b
    return rows


# ── stats + verdict ───────────────────────────────────────────────────────────

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
        pv = prior_session_vah_array(df)
        trades.extend(vah_trades(df, sig, pv))
    tdf = pd.DataFrame(trades)
    base = tdf["net_r"].tolist()
    qual = tdf[tdf["rejection"]]["net_r"].tolist()
    near_only = tdf[tdf["near_vah"] & ~tdf["rejection"]]["net_r"].tolist()  # specificity cell
    cells_out = {
        "baseline_all": _block(base, boot_p),
        "qualifying (near VAH + rejection)": _block(qual, boot_p),
        "near VAH, NO rejection (specificity)": _block(near_only, boot_p),
        "qualifying — long": _block(tdf[(tdf["rejection"]) & (tdf["side"] == "long")]["net_r"].tolist(), boot_p),
        "qualifying — short": _block(tdf[(tdf["rejection"]) & (tdf["side"] == "short")]["net_r"].tolist(), boot_p),
    }
    return {"cells": cells_out, "n_total": len(tdf)}


def verdict(res: dict) -> str:
    base = res["cells"]["baseline_all"]
    q = res["cells"]["qualifying (near VAH + rejection)"]
    if q["n"] == 0:
        return "REJECT — 0 qualifying signals. VAH filter NOT wired."
    improvement = q["mean_r"] - base["mean_r"]
    checks = [
        (q["n"] >= MIN_N, f"n_qualifying={q['n']} (need >= {MIN_N})"),
        (np.isfinite(q["boot_p"]) and q["boot_p"] < 0.05, f"boot_p={q['boot_p']:.3f} (need < 0.05)"),
        (improvement > IMPROVEMENT_MIN_R,
         f"improvement={improvement:+.3f}R vs baseline {base['mean_r']:+.3f}R (need > {IMPROVEMENT_MIN_R}R)"),
    ]
    passed = all(c for c, _ in checks)
    head = "ACCEPT — all pre-registered gates pass." if passed else \
        "REJECT — at least one pre-registered gate fails. VAH filter NOT wired (hard rule; no post-hoc rescue)."
    return head + "\n" + "\n".join(f"  [{'PASS' if c else 'FAIL'}] {m}" for c, m in checks)


def write_outputs(res: dict) -> None:
    cells = res["cells"]
    rows = [{"cell": k, **v} for k, v in cells.items()]
    pd.DataFrame(rows).to_csv(_OUT_CSV, index=False)
    lines = [
        "# VAH trap-reversal — results (pre-registered)",
        "",
        "Pre-registration: `docs/research/vah_trap_reversal_preregistration.md` "
        "(committed before this run). Population = validated top-10/1h confluence "
        "trades, live bank-half/BE/ride-3R geometry, net of maker fees.",
        "",
        f"- Total trades: **{res['n_total']}**",
        f"- Qualifying = entry within {PROXIMITY_ATR}·ATR of prior-session VAH "
        f"AND rejection candle (high>VAH & close<VAH).",
        "",
        "| cell | n | mean R | win rate | total R | boot_p |",
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
