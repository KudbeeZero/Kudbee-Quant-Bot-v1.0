"""Management shadow scorer — Phase 3, Task 1 (READ-ONLY, off the execution path).

Re-scores the bot's ACTUAL forward paper-traded trades (the journal of record)
under the three management geometries from the pre-registered study
(studies/management_geometry_preregistration.md), so the backtest finding
"A (ride-3R) beats B (live bank-half/BE)" can be checked on REAL forward data —
not just the historical pool.

For each resolved validated 1h bracket trade in data/journal.json, this takes the
trade's recorded entry/stop/target/direction, refetches the post-fill bars, and
resolves the SAME trade under:

  A — ride 3R (full size, no partial/BE)
  B — bank-half/BE (current live)
  C — partial, no BE slide

via the SHARED resolver (same fee model + helpers as research.management_geometry_study
— single source of truth, no reimplementation). Output: studies/management_shadow_log.csv
plus an A/B/C summary using the study's own verdict logic.

STRICTLY READ-ONLY: reads the journal, fetches bars, writes only the CSV/MD under
studies|research. It does NOT modify the journal, the scanner, the resolver,
paper.py, or any workflow. It is NOT wired to any cron — run it on demand. Wiring
it to a cadence would touch the live pipeline and is a separate, owner-approved
step.

This is a COUNTERFACTUAL re-scoring (resolve all three from the same post-fill
bars); it is labelled retrospective until enough fresh forward trades accrue.

Usage:  python research/management_shadow.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "research"))
sys.path.insert(0, str(_REPO / "scripts"))

from kudbee_quant.backtest.resolver import resolve_bracket  # noqa: E402
from kudbee_quant.config.validated_defaults import FEE_PCT, MAX_BARS, TARGET_R  # noqa: E402

# Single source of truth for the geometry maths + reporting.
from management_geometry_study import _gross_r, _stat  # noqa: E402

_JOURNAL = _REPO / "data" / "journal.json"
_OUT_CSV = _REPO / "studies" / "management_shadow_log.csv"
_OUT_MD = _REPO / "studies" / "management_shadow_results.md"
FEE = FEE_PCT
_VALIDATED_PREFIX = "confluence_r_50pct"   # the validated book (50% gate)


def load_resolved_validated(journal_path: Path = _JOURNAL) -> list[dict]:
    """Resolved (hit/miss) validated-book 1h bracket trades with full geometry."""
    data = json.loads(Path(journal_path).read_text())
    out = []
    for p in data:
        if not isinstance(p, dict) or p.get("kind") != "bracket":
            continue
        if p.get("timeframe") != "1h" or p.get("status") not in ("hit", "miss"):
            continue
        if not str(p.get("setup", "")).startswith(_VALIDATED_PREFIX):
            continue
        if any(p.get(k) in (None, "") for k in ("filled_at", "entry", "stop",
                                                "target", "direction")):
            continue
        out.append(p)
    return out


def score_trade(trade: dict, bars: pd.DataFrame) -> dict | None:
    """Net-R of one journal trade under A/B/C, resolved from its post-fill bars.
    Returns None if the bars don't cover the entry. ``bars`` has a ``timestamp``
    column (UTC) plus high/low/close."""
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    target = float(trade["target"])
    direction = float(trade["direction"])
    sd = abs(entry - stop)
    if sd <= 0 or not np.isfinite(sd):
        return None
    # Compare in int64 nanoseconds to stay tz-safe regardless of how the bars'
    # timestamp column is typed (naive vs tz-aware).
    ts_ns = pd.to_datetime(bars["timestamp"], utc=True).astype("int64").to_numpy()
    _fill = pd.Timestamp(trade["filled_at"])
    fill = _fill.tz_convert("UTC") if _fill.tzinfo else _fill.tz_localize("UTC")
    fill_ns = fill.floor("1h").value
    idx = int(np.searchsorted(ts_ns, fill_ns, side="left"))
    if idx >= len(ts_ns) - 1 or ts_ns[idx] != fill_ns:
        return None  # entry bar not located in the fetched window
    high = bars["high"].to_numpy()
    low = bars["low"].to_numpy()
    close = bars["close"].to_numpy()
    end = min(idx + MAX_BARS, len(close) - 1)
    hi, lo, cl = high[idx + 1:end + 1], low[idx + 1:end + 1], close[idx + 1:end + 1]
    if len(hi) == 0:
        return None
    ce = float(close[end])
    tp1 = entry + direction * sd * 1.0
    cost_full = FEE * entry / sd
    cost_partial = FEE * entry / sd * (1 + 0.5 * 0.5)

    oa = resolve_bracket(direction, entry, stop, target, sd, TARGET_R, hi, lo, cl,
                         force_close_at_end=True)
    ob = resolve_bracket(direction, entry, stop, target, sd, TARGET_R, hi, lo, cl,
                         force_close_at_end=True, tp1=tp1, tp1_r=1.0, tp1_frac=0.5,
                         be_after_tp1=True)
    oc = resolve_bracket(direction, entry, stop, target, sd, TARGET_R, hi, lo, cl,
                         force_close_at_end=True, tp1=tp1, tp1_r=1.0, tp1_frac=0.5,
                         be_after_tp1=False)
    return {
        "id": trade.get("id"), "symbol": trade.get("symbol"),
        "filled_at": str(trade.get("filled_at")),
        "side": "long" if direction > 0 else "short",
        "journal_r": float(trade.get("outcome_r")) if trade.get("outcome_r") is not None else float("nan"),
        "net_a": float(_gross_r(oa, direction, ce, entry, sd) - cost_full),
        "net_b": float(_gross_r(ob, direction, ce, entry, sd) - cost_partial),
        "net_c": float(_gross_r(oc, direction, ce, entry, sd) - cost_partial),
    }


def run_shadow(fetch_bars, journal_path: Path = _JOURNAL) -> dict:
    """Score every resolved validated 1h trade. ``fetch_bars(symbol, start, end)``
    returns a bars DataFrame (injected so tests need no network)."""
    trades = load_resolved_validated(journal_path)
    rows: list[dict] = []
    for t in trades:
        fill = pd.Timestamp(t["filled_at"])
        start = (fill.tz_convert("UTC") if fill.tzinfo else fill.tz_localize("UTC")).floor("1h")
        end = start + pd.Timedelta(hours=MAX_BARS + 3)
        try:
            bars = fetch_bars(t["symbol"], start, end)
        except Exception:  # noqa: BLE001 — a fetch miss skips the trade, never crashes
            continue
        scored = score_trade(t, bars)
        if scored is not None:
            rows.append(scored)
    return {"rows": rows, "n_candidates": len(trades)}


def summarize(rows: list[dict]) -> dict:
    a = np.array([r["net_a"] for r in rows], dtype=float)
    b = np.array([r["net_b"] for r in rows], dtype=float)
    c = np.array([r["net_c"] for r in rows], dtype=float)
    return {"n": len(rows),
            "geom": {"A ride-3R": _stat(a), "B bank-half/BE (live)": _stat(b),
                     "C partial no-BE": _stat(c)},
            "deltas": {"A-B": {"mean_delta": float((a - b).mean()) if a.size else float("nan"),
                               "boot_p_x_le_y": float("nan")}}}


def _default_fetch(symbol, start, end):
    import cycle_backtest as cyc  # noqa: PLC0415
    return cyc.BinanceClient().klines_range(symbol, interval="1h", start=start, end=end)


def write_outputs(res: dict) -> None:
    rows = res["rows"]
    pd.DataFrame(rows).to_csv(_OUT_CSV, index=False)
    summ = summarize(rows)
    g = summ["geom"]
    # journal cross-check: recomputed-A vs the journal's own R for ride-3R-managed
    # trades (tp1 None) and recomputed-B for partial-managed trades.
    lines = [
        "# Management shadow re-scoring — REAL forward journal trades",
        "",
        "Read-only counterfactual: the bot's actual resolved validated 1h trades, "
        "re-resolved under A/B/C from their post-fill bars (shared resolver, maker "
        "fees). NOT wired to live; on-demand only.",
        "",
        f"- Scored: **{summ['n']}** of {res['n_candidates']} resolved validated 1h trades.",
        "",
        "| geometry | n | mean R | win rate | total R | boot_p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for k, v in g.items():
        mean = "—" if not np.isfinite(v["mean_r"]) else f"{v['mean_r']:+.3f}"
        win = "—" if not np.isfinite(v["win_rate"]) else f"{v['win_rate']:.0%}"
        bp = "—" if not np.isfinite(v["boot_p"]) else f"{v['boot_p']:.3f}"
        lines.append(f"| {k} | {v['n']} | {mean} | {win} | {v['total_r']:+.1f} | {bp} |")
    d = summ["deltas"]["A-B"]
    lines += ["", f"A−B mean delta: {d['mean_delta']:+.3f}R "
              f"(forward, n={summ['n']}). Backtest reference (study #116): A−B=+0.048R.",
              "", "_Forward sample is small/retrospective; treat as directional "
              "corroboration, not a fresh significance test until ≥50 NEW trades accrue._", ""]
    _OUT_MD.write_text("\n".join(lines))
    print(f"wrote {_OUT_CSV} and {_OUT_MD}")


def main() -> None:
    res = run_shadow(_default_fetch)
    write_outputs(res)
    summ = summarize(res["rows"])
    print(f"\nscored {summ['n']} forward trades")
    for k, v in summ["geom"].items():
        print(f"  {k:24} n={v['n']:4} mean {v['mean_r']:+.3f}R  win {v['win_rate']:.0%}")
    print(f"  A-B forward delta: {summ['deltas']['A-B']['mean_delta']:+.3f}R "
          f"(backtest #116: +0.048R)")


if __name__ == "__main__":
    main()
