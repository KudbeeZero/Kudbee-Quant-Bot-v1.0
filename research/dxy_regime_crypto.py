"""DXY-regime effect on the VALIDATED crypto book — read-only research study.

Question (adapted from Tino's "always watch the dollar" to the bot's ACTUAL
universe): does the DXY regime *at trade entry* have a statistically significant
effect on the net-R outcome of our validated top-10 / 1h confluence trades —
and in particular, do SHORTS do better (and LONGS worse) when the dollar is
strong, as the intermarket thesis predicts?

  H0 (null): DXY regime at entry has no significant effect on net-R per trade.
  H1: net-R differs by DXY regime — directionally, USD-strong regimes favour
      crypto shorts and hurt crypto longs.

METHOD (no refit, no fabrication — reuses the live engine end to end):
  1. Build the EXACT validated signal population: cycle_backtest.WINDOWS x
     top-10 majors on 1h, build_levels -> confluence_position(min_pct=0.50,
     trend_align) — identical to research/trailing_sweep.load_cells().
  2. Enumerate trades with the SAME entry/overlap/exit geometry as the live
     bracket (bank-half @1R + BE + ride-to-3R), recording each trade's ENTRY
     TIMESTAMP, side and net-R. This baseline enumerator is fidelity-locked to
     bracket_backtest in tests/test_dxy_regime_crypto.py.
  3. For each trade, look up the DXY daily close AS-OF the entry date (last close
     <= entry; forward-filled over weekends/holidays) and classify the regime
     with the SHIPPED classifier kudbee_quant.intelligence.macro_context.get_dxy_regime.
  4. Bucket net-R by regime (overall / longs / shorts); report n, mean net-R,
     win rate, total R, and the project's one-sided bootstrap gate boot_p
     (P(mean<=0), cyc.boot_p, §19/§23).

GATE: a regime/side cell is only "edge" if boot_p < 0.05 AND n >= 30. Anything
else is INCONCLUSIVE and the macro layer stays INERT (the correct, no-shame
result). Nothing here wires into the live book.

DXY data: research/dxy_daily.csv (daily ICE DXY, DX-Y.NYB), refreshable via
``python -m research.dxy_regime_crypto --refresh-dxy`` (Yahoo chart API over
urllib — the proxy-safe transport). Daily resolution is deliberate: a DXY
*regime* is a slow macro state, not an intraday signal.

Usage:
  python research/dxy_regime_crypto.py            # run the study, write outputs
  python research/dxy_regime_crypto.py --refresh-dxy   # re-pull the DXY cache
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
from kudbee_quant.intelligence.macro_context import get_dxy_regime  # noqa: E402

# Entry geometry constants (mirror trailing_sweep / the live bracket exactly).
RETRACE_ATR = 0.25
ENTRY_WINDOW = 6
FEE = FEE_PCT

_DXY_CSV = _REPO / "research" / "dxy_daily.csv"
_OUT_MD = _REPO / "research" / "dxy_regime_crypto_results.md"
_OUT_CSV = _REPO / "research" / "dxy_regime_crypto_summary.csv"

REGIME_ORDER = ["USD_BULL_CONFIRMED", "USD_APPROACHING_KEY", "USD_BASE_BUILDING", "USD_WEAK"]


# ── DXY data ──────────────────────────────────────────────────────────────────

def refresh_dxy_cache(start_year: int = 2018, end_year: int = 2027) -> Path:
    """Re-pull daily ICE DXY (DX-Y.NYB) into the CSV cache via the Yahoo chart
    API over urllib (proxy-safe). Network-only; not exercised by the test."""
    import csv
    import datetime as dt
    import json
    import urllib.request

    p1 = int(dt.datetime(start_year, 1, 1).timestamp())
    p2 = int(dt.datetime(end_year, 1, 1).timestamp())
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB"
        f"?period1={p1}&period2={p2}&interval=1d"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (trusted host)
        data = json.load(r)
    res = data["chart"]["result"][0]
    ts, close = res["timestamp"], res["indicators"]["quote"][0]["close"]
    rows = [
        (dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"), round(c, 4))
        for t, c in zip(ts, close, strict=False)
        if c is not None
    ]
    with open(_DXY_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "dxy_close"])
        w.writerows(rows)
    print(f"wrote {_DXY_CSV} ({len(rows)} rows, {rows[0][0]}..{rows[-1][0]})")
    return _DXY_CSV


def load_dxy(path: Path = _DXY_CSV) -> pd.Series:
    """Daily DXY close indexed by (tz-naive) date, sorted ascending."""
    df = pd.read_csv(path, parse_dates=["date"])
    s = df.set_index("date")["dxy_close"].sort_index()
    return s


def dxy_asof(dxy: pd.Series, when: pd.Timestamp) -> float:
    """Last DXY close on or before ``when`` (forward-fill across weekends/holidays).
    Returns NaN if ``when`` precedes the series."""
    ts = pd.Timestamp(when)
    if ts.tzinfo is not None:                 # tz-aware (live frames are UTC) -> naive UTC
        ts = ts.tz_convert("UTC").tz_localize(None)
    day = ts.normalize()
    idx = dxy.index.searchsorted(day, side="right") - 1
    if idx < 0:
        return float("nan")
    return float(dxy.iloc[idx])


# ── trade enumeration (fidelity-locked mirror of the live baseline) ───────────

def baseline_trades_with_times(df: pd.DataFrame, signal: pd.Series) -> list[dict]:
    """Enumerate validated baseline trades, recording (entry_ts, side, net_r).

    Identical entry/overlap/exit path to research.trailing_sweep.paired_trades'
    BASELINE branch — bank half @1R, stop->BE, ride to 3R via the SHARED
    resolver. Locked to bracket_backtest in the test suite (no reimplementation
    of exit logic; resolve_bracket does the work). The only addition here is the
    entry timestamp, which the engine's float-only trade list doesn't expose.
    """
    # Live frames carry a tz-aware UTC "timestamp" column with a RangeIndex;
    # .to_numpy() yields naive-UTC datetime64. Fall back to the index only if a
    # frame has no timestamp column (e.g. a bare synthetic DatetimeIndex).
    times = (df["timestamp"].to_numpy() if "timestamp" in df.columns
             else df.index.to_numpy())
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
        rows.append({
            "entry_ts": pd.Timestamp(times[entry_bar]),
            "side": "long" if direction > 0 else "short",
            "net_r": float(gross - cost),
        })
        busy_until = exit_b
    return rows


# ── bucketing + stats ─────────────────────────────────────────────────────────

def _stat_block(net: list[float], boot_p) -> dict:
    arr = np.asarray(net, dtype=float)
    if arr.size == 0:
        return {"n": 0, "mean_r": float("nan"), "win_rate": float("nan"),
                "total_r": 0.0, "boot_p": float("nan")}
    return {
        "n": int(arr.size),
        "mean_r": float(arr.mean()),
        "win_rate": float((arr > 0).mean()),
        "total_r": float(arr.sum()),
        "boot_p": float(boot_p(list(arr))),
    }


def study(cells, dxy: pd.Series, boot_p) -> pd.DataFrame:
    """Pool every cell's baseline trades, tag DXY regime at entry, bucket by
    regime x side, and summarize with the project's bootstrap gate."""
    trades: list[dict] = []
    skipped_no_dxy = 0
    for _wk, _sym, df, sig in cells:
        for tr in baseline_trades_with_times(df, sig):
            d = dxy_asof(dxy, tr["entry_ts"])
            if not np.isfinite(d):
                skipped_no_dxy += 1
                continue
            tr["dxy"] = d
            tr["regime"] = get_dxy_regime(d)["regime"]
            trades.append(tr)
    tdf = pd.DataFrame(trades)
    rows: list[dict] = []
    for regime in REGIME_ORDER:
        sub = tdf[tdf["regime"] == regime] if len(tdf) else tdf
        for side in ("all", "long", "short"):
            net = (sub if side == "all" else sub[sub["side"] == side])["net_r"].tolist() \
                if len(sub) else []
            block = {"regime": regime, "side": side, **_stat_block(net, boot_p)}
            rows.append(block)
    out = pd.DataFrame(rows)
    out.attrs["skipped_no_dxy"] = skipped_no_dxy
    out.attrs["n_trades"] = len(tdf)
    return out


def _verdict(summary: pd.DataFrame) -> str:
    """A cell is 'edge' only if boot_p < 0.05 AND n >= 30 (the user's gate)."""
    hits = summary[(summary["boot_p"] < 0.05) & (summary["n"] >= 30)]
    if len(hits) == 0:
        return ("INCONCLUSIVE — no regime/side cell clears boot_p<0.05 AND n>=30. "
                "Macro layer stays INERT (correct result; do not wire).")
    lines = ["SIGNIFICANT cells (boot_p<0.05 AND n>=30):"]
    for _, r in hits.iterrows():
        lines.append(f"  {r['regime']}/{r['side']}: n={r['n']} mean_r={r['mean_r']:+.3f} "
                     f"win={r['win_rate']:.0%} boot_p={r['boot_p']:.3f}")
    lines.append("NOTE: positive expectancy in a cell is necessary but NOT sufficient "
                 "to wire — confirm it is a stable DIFFERENCE across regimes, not a "
                 "level-1 artifact, before any live change.")
    return "\n".join(lines)


def write_outputs(summary: pd.DataFrame) -> None:
    summary.to_csv(_OUT_CSV, index=False)
    n_trades = summary.attrs.get("n_trades", "?")
    skipped = summary.attrs.get("skipped_no_dxy", 0)
    lines = [
        "# DXY-regime effect on the validated crypto book — results",
        "",
        "Read-only study. Population = validated top-10/1h confluence trades "
        "(`cycle_backtest.WINDOWS`), live bank-half/BE/ride-3R geometry, net of "
        "maker fees. DXY regime = `get_dxy_regime()` over daily ICE DXY as-of entry.",
        "",
        f"- Trades analyzed: **{n_trades}** (skipped, no DXY as-of: {skipped})",
        "- Significance gate: one-sided bootstrap `boot_p < 0.05` AND `n >= 30` per cell.",
        "",
        "## Net-R by DXY regime x side",
        "",
        "| regime | side | n | mean R | win rate | total R | boot_p |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in summary.iterrows():
        mean = "—" if not np.isfinite(r["mean_r"]) else f"{r['mean_r']:+.3f}"
        win = "—" if not np.isfinite(r["win_rate"]) else f"{r['win_rate']:.0%}"
        bp = "—" if not np.isfinite(r["boot_p"]) else f"{r['boot_p']:.3f}"
        lines.append(f"| {r['regime']} | {r['side']} | {int(r['n'])} | {mean} | {win} "
                     f"| {r['total_r']:+.1f} | {bp} |")
    # Directional read: long-minus-short mean-R spread per regime. The thesis
    # predicts this spread goes NEGATIVE as the dollar strengthens (shorts favoured
    # in USD-strong, longs in USD-weak). Reported for the record; significance is
    # the gate above, not this sign pattern.
    lines += ["", "## Directional lean (descriptive only — NOT a significance result)", "",
              "| regime | long mean R | short mean R | long−short |",
              "|---|---:|---:|---:|"]
    for regime in REGIME_ORDER:
        lo = summary[(summary["regime"] == regime) & (summary["side"] == "long")]
        sh = summary[(summary["regime"] == regime) & (summary["side"] == "short")]
        lm = lo["mean_r"].iloc[0] if len(lo) else float("nan")
        sm = sh["mean_r"].iloc[0] if len(sh) else float("nan")
        spread = lm - sm if np.isfinite(lm) and np.isfinite(sm) else float("nan")
        fmt = lambda x: "—" if not np.isfinite(x) else f"{x:+.3f}"  # noqa: E731
        lines.append(f"| {regime} | {fmt(lm)} | {fmt(sm)} | {fmt(spread)} |")
    lines += ["", "## Verdict", "", "```", _verdict(summary), "```", ""]
    _OUT_MD.write_text("\n".join(lines))
    print(f"wrote {_OUT_MD} and {_OUT_CSV}")


def main() -> None:
    if "--refresh-dxy" in sys.argv:
        refresh_dxy_cache()
        return
    import cycle_backtest as cyc  # noqa: PLC0415
    import trailing_sweep as ts  # noqa: PLC0415

    dxy = load_dxy()
    print(f"DXY cache: {dxy.index.min().date()}..{dxy.index.max().date()} ({len(dxy)} days)")
    cells = ts.load_cells()
    summary = study(cells, dxy, cyc.boot_p)
    write_outputs(summary)
    print("\n" + _verdict(summary))


if __name__ == "__main__":
    main()
