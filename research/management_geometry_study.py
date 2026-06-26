"""Management-geometry study — Phase 2 backtest (pre-registered).

Tests studies/management_geometry_preregistration.md (merged to main BEFORE this
ran): does the live bank-half/BE management (B) cost net-R vs plain ride-3R (A),
and is the BE slide specifically the drag (isolated by C, partial-without-BE)?

PAIRED design (apples-to-apples): a single common entry set drives all three
geometries — entries + overlap are taken from the live geometry B's timeline
(exactly as research.trailing_sweep.paired_trades does, and fidelity-locked the
same way: pooled B net-R reproduces bracket_backtest's baseline EXACTLY). Each of
those same entries is then resolved under A, B and C via the shared resolver, so
the per-entry deltas are a true counterfactual ("same trades, different
management"), not two divergent books.

  A — ride 3R (no partial, no BE): full size to 3R / -1R stop.
  B — bank-half/BE (current live): 50% at 1R, stop->BE, rest to 3R.
  C — partial, NO BE slide: 50% at 1R, rest to 3R, stop stays at -1R.

GATE (pre-registered): n>=50 AND boot_p<0.05 AND |delta|>0.015R. No live change
under any outcome — a positive finding yields only a governance-proposal PR.

Usage:  python research/management_geometry_study.py
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
MIN_N = 50
DELTA_MIN_R = 0.015
_BOOT_ITERS = 5000
_BOOT_SEED = 7

_OUT_MD = _REPO / "research" / "management_geometry_results.md"
_OUT_CSV = _REPO / "research" / "management_geometry_summary.csv"


def _gross_r(ob, direction: float, close_end: float, entry: float, sd: float) -> float:
    """Outcome in R: the resolver's value, or a forced mark-out at the window end."""
    if ob.exit_offset is None:
        return direction * (close_end - entry) / sd
    return ob.outcome_r


def paired_geometries(df: pd.DataFrame, signal: pd.Series) -> list[dict]:
    """Per common entry (B-timeline driven), the net-R under A, B, C."""
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    atr = df["atr"].to_numpy()
    sig = pd.Series(signal, index=df.index).fillna(0.0).to_numpy()
    n = len(df)
    rows: list[dict] = []
    busy_until = -1
    cost_partial_mult = 1 + 0.5 * 0.5   # 1.5 round-trips (half out at TP1)
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
        cost_full = FEE * entry / sd
        cost_partial = FEE * entry / sd * cost_partial_mult

        # B — bank-half + BE (drives the entry timeline)
        ob = resolve_bracket(direction, entry, stop, target, sd, TARGET_R, hi, lo, cl,
                             force_close_at_end=True, tp1=tp1, tp1_r=1.0, tp1_frac=0.5,
                             be_after_tp1=True)
        exit_b = end if ob.exit_offset is None else entry_bar + 1 + ob.exit_offset
        # A — ride 3R, full size, no partial/BE
        oa = resolve_bracket(direction, entry, stop, target, sd, TARGET_R, hi, lo, cl,
                             force_close_at_end=True)
        # C — partial, NO BE slide (stop stays at -1R on the remainder)
        oc = resolve_bracket(direction, entry, stop, target, sd, TARGET_R, hi, lo, cl,
                             force_close_at_end=True, tp1=tp1, tp1_r=1.0, tp1_frac=0.5,
                             be_after_tp1=False)
        ce = close[end]
        rows.append({
            "net_a": float(_gross_r(oa, direction, ce, entry, sd) - cost_full),
            "net_b": float(_gross_r(ob, direction, ce, entry, sd) - cost_partial),
            "net_c": float(_gross_r(oc, direction, ce, entry, sd) - cost_partial),
        })
        busy_until = exit_b
    return rows


def _boot_mean_le0(arr: np.ndarray) -> float:
    """One-sided bootstrap P(mean <= 0)."""
    if arr.size < 10:
        return float("nan")
    rng = np.random.default_rng(_BOOT_SEED)
    means = rng.choice(arr, size=(_BOOT_ITERS, arr.size), replace=True).mean(axis=1)
    return float((means <= 0).mean())


def _stat(arr: np.ndarray) -> dict:
    if arr.size == 0:
        return {"n": 0, "mean_r": float("nan"), "win_rate": float("nan"),
                "total_r": 0.0, "boot_p": float("nan")}
    return {"n": int(arr.size), "mean_r": float(arr.mean()),
            "win_rate": float((arr > 0).mean()), "total_r": float(arr.sum()),
            "boot_p": _boot_mean_le0(arr)}


def study(cells) -> dict:
    rows: list[dict] = []
    for _wk, _sym, df, sig in cells:
        rows.extend(paired_geometries(df, sig))
    tdf = pd.DataFrame(rows)
    a = tdf["net_a"].to_numpy() if len(tdf) else np.array([])
    b = tdf["net_b"].to_numpy() if len(tdf) else np.array([])
    c = tdf["net_c"].to_numpy() if len(tdf) else np.array([])

    def _paired_delta(x: np.ndarray, y: np.ndarray) -> dict:
        d = x - y
        return {"mean_delta": float(d.mean()) if d.size else float("nan"),
                "boot_p_x_le_y": _boot_mean_le0(d)}  # P(mean(x-y) <= 0)

    return {
        "geom": {"A ride-3R": _stat(a), "B bank-half/BE (live)": _stat(b),
                 "C partial no-BE": _stat(c)},
        "deltas": {"A-B": _paired_delta(a, b), "A-C": _paired_delta(a, c),
                   "C-B": _paired_delta(c, b)},
        "n": int(len(tdf)),
    }


def verdict(res: dict) -> str:
    g = res["geom"]
    a, b, c = g["A ride-3R"], g["B bank-half/BE (live)"], g["C partial no-BE"]
    d_ab = res["deltas"]["A-B"]
    n_ok = a["n"] >= MIN_N and b["n"] >= MIN_N and c["n"] >= MIN_N
    if not n_ok:
        return f"REJECT — n<{MIN_N} in some geometry (n={res['n']}). No change."
    ab = a["mean_r"] - b["mean_r"]
    cb = c["mean_r"] - b["mean_r"]
    ac = a["mean_r"] - c["mean_r"]
    sig_ab = np.isfinite(d_ab["boot_p_x_le_y"]) and d_ab["boot_p_x_le_y"] < 0.05
    meaningful_ab = abs(ab) > DELTA_MIN_R

    lines = [f"n={res['n']} per geometry (paired).",
             f"A ride-3R   mean {a['mean_r']:+.3f}R  boot_p {a['boot_p']:.3f}",
             f"B live      mean {b['mean_r']:+.3f}R  boot_p {b['boot_p']:.3f}",
             f"C no-BE     mean {c['mean_r']:+.3f}R  boot_p {c['boot_p']:.3f}",
             f"A-B delta {ab:+.3f}R (paired boot_p A<=B {d_ab['boot_p_x_le_y']:.3f}); "
             f"A-C {ac:+.3f}R; C-B {cb:+.3f}R"]

    if not (sig_ab and meaningful_ab):
        # A does not significantly+meaningfully beat B
        head = ("RESULT: B (current management) NOT shown inferior to A by the gate "
                "(need A-B>0.015R AND paired boot_p<0.05). Current management stands; "
                "no change proposed.")
    else:
        # A beats B significantly & meaningfully -> which mechanism? Per the locked
        # pre-registration matrix, attribution keys on C-vs-A: removing the BE slide
        # (C) either recovers ride-3R (slide was the drag) or it does NOT (the partial
        # close itself is the drag). cb (=C-B) is reported as the slide's contribution,
        # ac (=A-C) as the partial's contribution.
        if abs(ac) <= DELTA_MIN_R:
            mech = (f"C ≈ A (A-C={ac:+.3f}R, within noise): removing the BE slide "
                    f"recovers ride-3R — the BE SLIDE is the drag (slide piece C-B="
                    f"{cb:+.3f}R). Governance proposal: drop be_after_tp1, KEEP the partial.")
        else:
            mech = (f"C < A (A-C={ac:+.3f}R, meaningful): dropping the BE slide alone "
                    f"does NOT recover ride-3R — the PARTIAL CLOSE itself is the larger "
                    f"drag (slide piece C-B={cb:+.3f}R; partial piece A-C={ac:+.3f}R). "
                    f"Governance proposal: move toward ride-3R (A).")
        head = ("RESULT: A (ride-3R) beats B (current live) significantly & meaningfully. "
                + mech +
                " NOTE: research only — a SEPARATE governance PR with human approval "
                "is required before any live management change.")
    return head + "\n  " + "\n  ".join(lines)


def write_outputs(res: dict) -> None:
    g = res["geom"]
    pd.DataFrame([{"geometry": k, **v} for k, v in g.items()]).to_csv(_OUT_CSV, index=False)
    lines = [
        "# Management-geometry study — results (pre-registered)",
        "",
        "Pre-registration: `studies/management_geometry_preregistration.md` (merged "
        "to main before this run). PAIRED design — one common entry set (live "
        "geometry B's timeline) resolved under A/B/C via the shared resolver. "
        "Population = validated top-10/1h, net of maker fees.",
        "",
        f"- Paired entries: **{res['n']}**",
        "",
        "| geometry | n | mean R | win rate | total R | boot_p (mean≤0) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for k, v in g.items():
        mean = "—" if not np.isfinite(v["mean_r"]) else f"{v['mean_r']:+.3f}"
        win = "—" if not np.isfinite(v["win_rate"]) else f"{v['win_rate']:.0%}"
        bp = "—" if not np.isfinite(v["boot_p"]) else f"{v['boot_p']:.3f}"
        lines.append(f"| {k} | {v['n']} | {mean} | {win} | {v['total_r']:+.1f} | {bp} |")
    d = res["deltas"]
    lines += ["", "## Paired deltas", "",
              "| comparison | mean delta R | paired boot_p (first≤second) |",
              "|---|---:|---:|"]
    for k, v in d.items():
        md = "—" if not np.isfinite(v["mean_delta"]) else f"{v['mean_delta']:+.3f}"
        bp = "—" if not np.isfinite(v["boot_p_x_le_y"]) else f"{v['boot_p_x_le_y']:.3f}"
        lines.append(f"| {k} | {md} | {bp} |")
    lines += ["", "## Verdict (pre-registered gate)", "", "```", verdict(res), "```", ""]
    _OUT_MD.write_text("\n".join(lines))
    print(f"wrote {_OUT_MD} and {_OUT_CSV}")


def main() -> None:
    import trailing_sweep as ts  # noqa: PLC0415
    cells = ts.load_cells()
    res = study(cells)
    write_outputs(res)
    print("\n" + verdict(res))


if __name__ == "__main__":
    main()
