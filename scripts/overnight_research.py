"""Overnight research harness — honestly test candidate edges while you sleep.

WHAT THIS IS
------------
An autonomous, repeatable research loop that takes candidate ideas for lifting
the validated strategy's expectancy (scripts/overnight_candidates.py), runs each
through the SAME honest backtest the rest of the project uses, and records a
verdict — so by morning you have *tested* improvements, not *believed* ones.

It is the project's honesty contract (docs/PHILOSOPHY.md) turned into a nightly
worker: every candidate is a hypothesis; it must beat the SHIPPING baseline,
pooled across the top-10 majors, AND survive a split-half robustness check
before it is called a WINNER. Dead ends are logged so they are never re-tested
(docs/MEMORY.md §2).

THE BASELINE (what every candidate must beat) — docs/MEMORY.md §1:
    1h · confluence_position(min_pct=0.50, trend_align=True) · LIMIT entry on a
    0.25-ATR retrace (maker) · stop 1.5*ATR (=1R) · target 3R · 24-bar time stop
    · both sides · realistic maker cost.

HOW A CANDIDATE IS JUDGED
-------------------------
  delta    = pooled mean-R(candidate) − pooled mean-R(baseline)   [full history]
  h1/h2    = the same delta computed on the FIRST / SECOND half of each
             symbol's history (out-of-sample robustness, no parameter fitting)
  verdict  : WINNER     delta ≥ +0.015R AND both halves positive AND enough trades
             SUGGESTIVE delta ≥ +0.015R but not robust in both halves
             NEUTRAL    |delta| < 0.015R
             HURTS      delta ≤ −0.015R
             THIN       too few trades to judge

Features are computed on the FULL frame (so rolling windows are causal — only
trailing data), then sliced for the half-tests; the bracket backtest is
path-local, so slicing the signal is lookahead-safe.

USAGE
-----
    python scripts/overnight_research.py --batch 3      # test next 3 queued
    python scripts/overnight_research.py --enqueue all   # queue every candidate
    python scripts/overnight_research.py --enqueue vol_regime_mid clean_trend
    python scripts/overnight_research.py --status         # show queue + winners

Outputs (committed by the hourly loop so progress survives the container):
    data/overnight_queue.json      pending / done candidate names
    data/overnight_results.json    machine-readable results + run log
    docs/research/overnight_findings.md   the human-readable report
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))        # for overnight_candidates
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # for kudbee_quant
from overnight_candidates import REGISTRY  # noqa: E402

# DMN: merge the generated candidates into REGISTRY so any queued `gen__*` name
# resolves to its (deterministic) callable. Generation only PROPOSES; the gate below
# still judges. See scripts/idea_generator.py + docs/BRAIN.md Part II.
import idea_generator  # noqa: E402
idea_generator.register_generated(REGISTRY)

from kudbee_quant.backtest.bracket import bracket_backtest  # noqa: E402
from kudbee_quant.confluence.stack import confluence_position, confluence_score  # noqa: E402
from kudbee_quant.ingest import load_ohlcv  # noqa: E402
from kudbee_quant.levels import build_levels  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "_overnight_cache"
QUEUE_PATH = DATA / "overnight_queue.json"
RESULTS_PATH = DATA / "overnight_results.json"
FINDINGS_PATH = ROOT / "docs" / "research" / "overnight_findings.md"

from kudbee_quant.config.validated_defaults import BRACKET_KW  # noqa: E402
from kudbee_quant.universe import TOP_10_CRYPTO  # noqa: E402

UNIVERSE = list(TOP_10_CRYPTO)

# The shipping execution defaults — every candidate is measured against these.
BASE_KW = dict(BRACKET_KW)

MIN_TRADES = 120          # below this the candidate sample is too thin to trust
DELTA_GATE = 0.015        # R/trade improvement that counts as real
SIG_P = 0.05              # bootstrap p-value a WINNER must clear (no more luck)


def _bootstrap_p(base: list, cand: list, n_boot: int = 2000, seed: int = 0) -> float:
    """One-sided bootstrap p-value that the candidate's mean R exceeds the
    baseline's. Resamples each pooled trade set with replacement and reports the
    fraction of resamples where the candidate does NOT beat the baseline. This is
    the gate that stops us crowning a lucky +0.05R as a 'winner' ever again."""
    b = np.asarray(base, dtype=float)
    c = np.asarray(cand, dtype=float)
    if b.size < 30 or c.size < 30:
        return 1.0
    rng = np.random.default_rng(seed)
    bm = rng.choice(b, size=(n_boot, b.size), replace=True).mean(axis=1)
    cm = rng.choice(c, size=(n_boot, c.size), replace=True).mean(axis=1)
    return float(((cm - bm) <= 0).mean())


# --- data --------------------------------------------------------------------


def _load_frames(interval: str, limit: int) -> dict[str, pd.DataFrame]:
    """Load + feature-build every symbol, with a parquet cache fallback so a
    transient network blip doesn't abort a whole overnight cycle."""
    CACHE.mkdir(parents=True, exist_ok=True)
    frames = {}
    for sym in UNIVERSE:
        cache_file = CACHE / f"binance_{sym}_{interval}.parquet"
        try:
            raw = load_ohlcv(sym, interval=interval, limit=limit)
            raw.to_parquet(cache_file)
        except Exception as exc:  # network/exchange hiccup — fall back to cache
            if cache_file.exists():
                print(f"  [{sym}] live fetch failed ({exc}); using cache")
                raw = pd.read_parquet(cache_file)
            else:
                print(f"  [{sym}] live fetch failed and no cache; skipping")
                continue
        frames[sym] = build_levels(raw)
    return frames


# --- evaluation --------------------------------------------------------------


def _trades(df: pd.DataFrame, sig: pd.Series, size, overrides: dict) -> list:
    kw = {**BASE_KW, **overrides}
    res = bracket_backtest(df, sig, size=size, **kw)
    return list(res.trades)


def _slice_overrides(overrides: dict, lo: int, hi: int) -> dict:
    """Slice any per-bar (array-like) override value to the [lo:hi] window so a
    candidate's per-bar ``target_price`` lines up with the sliced split-half frame.
    Scalar overrides (target_r, stop_atr, …) pass through unchanged."""
    out = {}
    for k, v in overrides.items():
        if isinstance(v, pd.Series):
            out[k] = v.to_numpy()[lo:hi]
        elif isinstance(v, np.ndarray):
            out[k] = v[lo:hi]
        else:
            out[k] = v
    return out


def _pool_expectancy(trades: list) -> tuple[int, float, float]:
    arr = np.asarray(trades, dtype=float)
    if arr.size == 0:
        return 0, 0.0, 0.0
    return arr.size, float(arr.mean()), float((arr > 0).mean())


def _risk_metrics(trades: list) -> tuple[float, float, float]:
    """Per-trade Sharpe-like ratio (mean/std), return std, and max drawdown in R.
    These are the RISK-ADJUSTED lenses — a variance-reducer can be flat on mean-R
    yet clearly better here, which a leverage trader cares about most (§22)."""
    arr = np.asarray(trades, dtype=float)
    if arr.size < 2:
        return 0.0, 0.0, 0.0
    std = float(arr.std())
    sharpe = float(arr.mean() / std) if std > 0 else 0.0
    equity = np.cumsum(arr)
    maxdd = float((equity - np.maximum.accumulate(equity)).min())
    return sharpe, std, maxdd


def evaluate(name: str, frames: dict) -> dict:
    """Run baseline vs candidate pooled across the universe + split-half."""
    fn, desc = REGISTRY[name]
    base_full, cand_full = [], []
    base_h1, cand_h1, base_h2, cand_h2 = [], [], [], []

    for df in frames.values():
        scored = confluence_score(df)
        base_sig = confluence_position(df, min_pct=0.50, trend_align=True)
        cand_sig, size, overrides = fn(df, scored, base_sig)
        cand_sig = pd.Series(cand_sig, index=df.index).fillna(0.0)
        size = None if size is None else pd.Series(size, index=df.index).fillna(0.0)

        base_full += _trades(df, base_sig, None, {})
        cand_full += _trades(df, cand_sig, size, overrides)

        mid = len(df) // 2
        for lo, hi, bbin, cbin in ((0, mid, base_h1, cand_h1), (mid, len(df), base_h2, cand_h2)):
            d = df.iloc[lo:hi].reset_index(drop=True)
            bs = base_sig.iloc[lo:hi].reset_index(drop=True)
            cs = cand_sig.iloc[lo:hi].reset_index(drop=True)
            sz = None if size is None else size.iloc[lo:hi].reset_index(drop=True)
            bbin += _trades(d, bs, None, {})
            cbin += _trades(d, cs, sz, _slice_overrides(overrides, lo, hi))

    bn, bexp, bwin = _pool_expectancy(base_full)
    cn, cexp, cwin = _pool_expectancy(cand_full)
    _, bexp1, _ = _pool_expectancy(base_h1)
    _, cexp1, _ = _pool_expectancy(cand_h1)
    _, bexp2, _ = _pool_expectancy(base_h2)
    _, cexp2, _ = _pool_expectancy(cand_h2)

    delta = cexp - bexp
    h1, h2 = cexp1 - bexp1, cexp2 - bexp2
    p_value = _bootstrap_p(base_full, cand_full)
    robust = h1 > 0 and h2 > 0
    significant = p_value < SIG_P
    b_sharpe, b_std, b_dd = _risk_metrics(base_full)
    c_sharpe, c_std, c_dd = _risk_metrics(cand_full)
    if cn < MIN_TRADES:
        verdict = "THIN"
    elif delta <= -DELTA_GATE:
        verdict = "HURTS"
    elif delta < DELTA_GATE:
        # Flat on mean-R — but if it cuts variance AND lifts Sharpe AND shallows the
        # drawdown, it's a RISK-REDUCER (the §22 lesson: variance-reducers are worth
        # keeping for leverage even at flat expectancy; don't bury them in NEUTRAL).
        if b_std and c_std < 0.95 * b_std and c_sharpe > b_sharpe and c_dd > b_dd:
            verdict = "RISK-REDUCER"
        else:
            verdict = "NEUTRAL"
    elif robust and significant:
        verdict = "WINNER"          # beats baseline, robust BOTH halves, AND p<0.05
    else:
        verdict = "SUGGESTIVE"      # positive but not robust+significant -> not luck-proof

    return {
        "name": name, "desc": desc,
        "tested_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "n_trades": cn, "base_n": bn,
        "keep_pct": round(cn / bn, 3) if bn else None,
        "base_exp": round(bexp, 4), "cand_exp": round(cexp, 4),
        "delta": round(delta, 4), "h1_delta": round(h1, 4), "h2_delta": round(h2, 4),
        "p_value": round(p_value, 4),
        "base_win": round(bwin, 3), "cand_win": round(cwin, 3),
        "base_sharpe": round(b_sharpe, 4), "cand_sharpe": round(c_sharpe, 4),
        "sharpe_delta": round(c_sharpe - b_sharpe, 4),
        "base_maxdd_r": round(b_dd, 2), "cand_maxdd_r": round(c_dd, 2),
        "base_std": round(b_std, 4), "cand_std": round(c_std, 4),
        "verdict": verdict,
    }


# --- state -------------------------------------------------------------------


def _read_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def _queue() -> dict:
    return _read_json(QUEUE_PATH, {"pending": [], "done": []})


def _results() -> dict:
    return _read_json(RESULTS_PATH, {"runs": [], "results": []})


def enqueue(names: list[str]) -> None:
    q = _queue()
    done = set(q["done"])
    if names == ["all"]:
        names = list(REGISTRY)
    added = []
    for n in names:
        if n not in REGISTRY:
            print(f"  unknown candidate: {n}")
            continue
        if n in q["pending"] or n in done:
            continue
        q["pending"].append(n)
        added.append(n)
    QUEUE_PATH.write_text(json.dumps(q, indent=2))
    print(f"Enqueued {len(added)}: {added}")


def _write_findings(results: dict) -> None:
    """Regenerate the human-readable report from the machine results."""
    recs = results["results"]
    by_name = {r["name"]: r for r in recs}            # keep the latest per name
    latest = list(by_name.values())
    winners = sorted([r for r in latest if r["verdict"] == "WINNER"],
                     key=lambda r: r["delta"], reverse=True)
    others = sorted([r for r in latest if r["verdict"] != "WINNER"],
                    key=lambda r: r["delta"], reverse=True)

    L = []
    L.append("# Overnight research findings\n")
    L.append("> Auto-generated by `scripts/overnight_research.py`. Each candidate "
             "is tested against the shipping baseline (1h, ≥50% confluence + trend "
             "filter, 0.25-ATR limit retrace, 1.5-ATR stop, 3R, maker cost), pooled "
             "across the top-10 majors, with a split-half robustness check. A "
             "**WINNER** beats baseline by ≥+0.015R AND in *both* halves. This file "
             "is the honest scoreboard — failures are recorded as loudly as wins.\n")
    L.append(f"_Last run: {results['runs'][-1]['ts'] if results['runs'] else 'n/a'} "
             f"· {len(latest)} candidates tested · {len(winners)} winners._\n")

    def row(r):
        return (f"| `{r['name']}` | {r['verdict']} | {r['delta']:+.3f} | "
                f"{r.get('p_value', float('nan'))} | "
                f"{r.get('sharpe_delta', 0):+.3f} | {r.get('cand_maxdd_r', 0):.1f} | "
                f"{r['cand_exp']:+.3f} | {r['base_exp']:+.3f} | "
                f"{r['n_trades']} ({r['keep_pct']}) | {r['cand_win']:.2f} | {r['desc']} |")

    head = ("| candidate | verdict | ΔR | boot p | ΔSharpe | candDD(R) | cand R | base R | "
            "trades (keep) | win | idea |\n|---|---|---|---|---|---|---|---|---|---|---|")

    L.append("\n## 🏆 Winners (beat baseline, robust both halves)\n")
    L.append(head if winners else "_None yet._")
    L += [row(r) for r in winners]

    L.append("\n## All results (latest per candidate)\n")
    L.append(head)
    L += [row(r) for r in others if r["verdict"] != "WINNER"]
    L += [row(r) for r in winners]

    L.append("\n## Run log\n")
    for run in results["runs"][-24:]:
        L.append(f"- **{run['ts']}** — tested {run['tested']} "
                 f"(baseline pooled {run['baseline_exp']:+.3f}R over {run['baseline_n']} trades)")

    FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FINDINGS_PATH.write_text("\n".join(L) + "\n")


def run_batch(batch: int, interval: str, limit: int) -> list[dict]:
    q = _queue()
    todo = q["pending"][:batch]
    if not todo:
        print("Queue empty — nothing to test. Use --enqueue to add candidates.")
        return []
    print(f"Loading {len(UNIVERSE)} symbols @ {interval} ...")
    frames = _load_frames(interval, limit)
    if not frames:
        print("No data loaded; aborting this cycle.")
        return []

    results = _results()
    new = []
    for name in todo:
        print(f"Testing {name} ...", flush=True)
        try:
            rec = evaluate(name, frames)
        except Exception as exc:  # a broken candidate must not kill the cycle
            print(f"  -> ERROR {exc}")
            rec = {"name": name, "desc": REGISTRY.get(name, (None, "?"))[1],
                   "tested_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                   "n_trades": 0, "base_n": 0, "keep_pct": None,
                   "base_exp": 0.0, "cand_exp": 0.0, "delta": 0.0,
                   "h1_delta": 0.0, "h2_delta": 0.0, "base_win": 0.0,
                   "cand_win": 0.0, "verdict": "ERROR", "error": str(exc)}
            results["results"].append(rec)
            new.append(rec)
            continue
        rec["interval"] = interval
        results["results"].append(rec)
        new.append(rec)
        print(f"  -> {rec['verdict']}  ΔR={rec['delta']:+.4f}  "
              f"(h1 {rec['h1_delta']:+.4f}, h2 {rec['h2_delta']:+.4f})  "
              f"n={rec['n_trades']}  cand={rec['cand_exp']:+.4f} base={rec['base_exp']:+.4f}")

    # advance the queue
    q["pending"] = q["pending"][len(todo):]
    q["done"] += todo
    QUEUE_PATH.write_text(json.dumps(q, indent=2))

    # The pooled baseline is identical for every candidate this cycle (same
    # frames), so record it once from the first non-errored result.
    ok = [r for r in new if r["base_n"]]
    base_exp = ok[0]["base_exp"] if ok else 0.0
    base_n = ok[0]["base_n"] if ok else 0
    results["runs"].append({
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tested": todo, "interval": interval,
        "baseline_exp": base_exp, "baseline_n": base_n,
    })
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    _write_findings(results)
    return new


def status() -> None:
    q, r = _queue(), _results()
    latest = {x["name"]: x for x in r["results"]}
    winners = [x for x in latest.values() if x["verdict"] == "WINNER"]
    print(f"Queue: {len(q['pending'])} pending, {len(q['done'])} done")
    print(f"Pending: {q['pending']}")
    print(f"Tested:  {len(latest)} candidates, {len(winners)} winners")
    for w in sorted(winners, key=lambda x: x["delta"], reverse=True):
        print(f"  WINNER {w['name']}: ΔR={w['delta']:+.4f} (h1 {w['h1_delta']:+.4f}, h2 {w['h2_delta']:+.4f})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch", type=int, default=3, help="how many queued candidates to test")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--limit", type=int, default=4000)
    ap.add_argument("--enqueue", nargs="+", metavar="NAME", help="add candidates to the queue ('all' for every one)")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    DATA.mkdir(exist_ok=True)
    if args.enqueue:
        enqueue(args.enqueue)
        return
    if args.status:
        status()
        return
    run_batch(args.batch, args.interval, args.limit)


if __name__ == "__main__":
    main()
