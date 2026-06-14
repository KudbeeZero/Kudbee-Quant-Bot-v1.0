"""Near-miss autopsy + scenario re-simulation over the forward journal.

RESEARCH ONLY — reads data/journal.json, re-fetches the real bars each trade lived
through, and replays them. It NEVER changes live config and NEVER writes the
journal. Output: data/excursion_audit.json + a printed report; a config
recommendation is proposed for human approval, not applied.

Built on existing engine pieces (no re-implementation of trade logic):
  * journal/excursion-style MFE/MAE from real bars (here, inlined so we keep the
    forward-bar arrays for re-resolution too);
  * backtest/resolver.resolve_bracket — the single source of truth for "given a
    forward path, how did this bracket resolve in R?" — re-run at swept targets.

Reconciliation guard: re-resolving every trade at its ORIGINAL 3R must reproduce
the journal's recorded outcome sign; we print that match rate so the windowing is
auditable before any swept result is trusted.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from kudbee_quant.backtest.resolver import resolve_bracket
from kudbee_quant.ingest import RouterClient
from kudbee_quant.journal.journal import Prediction, fee_r_of

JOURNAL = "data/journal.json"
OUT = "data/excursion_audit.json"
SWEEP_TARGETS = [1.0, 1.5, 2.0, 2.5, 3.0]


def band_of(p: Prediction) -> str:
    m = re.search(r"confluence_r_(\d+)pct", p.setup or "")
    return f"{m.group(1)}%" if m else (p.setup or "?")


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


@dataclass
class TradeReplay:
    p: Prediction
    band: str
    mfe_r: float
    mae_r: float
    n_bars: int
    # gross R at each swept target (None if window unusable)
    swept: dict
    fee_r: float


def load_resolved() -> list[Prediction]:
    raw = json.loads(open(JOURNAL).read())
    ps = [Prediction(**d) for d in raw]
    return [p for p in ps
            if p.kind == "bracket" and p.status in ("hit", "miss")
            and p.outcome_r is not None and p.entry is not None
            and p.stop is not None and p.filled_at is not None
            and p.resolved_at is not None]


def replay_one(p: Prediction, client: RouterClient) -> TradeReplay | None:
    risk = abs(p.entry - p.stop)
    if risk <= 0:
        return None
    # Sub-hourly windows can predate the most-recent 1000 bars (5m*1000 ~ 3.5d but
    # the journal spans ~5d), so fetch deep enough to cover the trade's life.
    limit = 3000 if p.timeframe in ("1m", "3m", "5m", "15m") else 1000
    df = client.klines(p.symbol, interval=p.timeframe, limit=limit)
    if df is None or df.empty:
        return None
    ts = pd.to_datetime(df["timestamp"], utc=True)
    fill, res = _dt(p.filled_at), _dt(p.resolved_at)
    # MFE/MAE over [fill, resolved]; re-resolution over bars strictly AFTER the
    # fill bar (matches the journal resolver, which walks fwd = rows[fill_i+1:]).
    win = df[(ts >= fill) & (ts <= res)]
    fwd = df[(ts > fill) & (ts <= res)]
    if win.empty or fwd.empty:
        return None
    d = p.direction or 1.0
    hi, lo = win["high"].to_numpy(float), win["low"].to_numpy(float)
    r_hi, r_lo = d * (hi - p.entry) / risk, d * (lo - p.entry) / risk
    mfe_r = float(max(r_hi.max(), r_lo.max()))
    mae_r = float(min(r_hi.min(), r_lo.min()))

    fhi, flo, fcl = (fwd["high"].to_numpy(float), fwd["low"].to_numpy(float),
                     fwd["close"].to_numpy(float))
    swept = {}
    for R in SWEEP_TARGETS:
        target = p.entry + d * risk * R
        out = resolve_bracket(d, p.entry, p.stop, target, risk, R, fhi, flo, fcl,
                              force_close_at_end=True)
        swept[R] = out.outcome_r
    return TradeReplay(p=p, band=band_of(p), mfe_r=mfe_r, mae_r=mae_r,
                       n_bars=int(len(win)), swept=swept, fee_r=fee_r_of(p))


def run() -> list[TradeReplay]:
    client = RouterClient()
    trades = load_resolved()
    print(f"resolved bracket trades: {len(trades)}")
    reps: list[TradeReplay] = []
    failed = 0
    for p in trades:
        try:
            r = replay_one(p, client)
        except Exception as e:  # network / data hiccup — count, don't abort
            print(f"  ! {p.symbol} {p.timeframe} {p.id}: {type(e).__name__}: {e}")
            r = None
        if r is None:
            failed += 1
            continue
        reps.append(r)
    print(f"replayed OK: {len(reps)}  (window-unusable/failed: {failed})")
    return reps


def reconcile(reps: list[TradeReplay]) -> None:
    """Re-resolved 3R vs journal outcome — sign match is the windowing audit."""
    sign_ok = same = 0
    for r in reps:
        got = r.swept.get(3.0)
        rec = r.p.outcome_r
        if got is None:
            continue
        if (got > 0) == (rec > 0):
            sign_ok += 1
        if abs(got - rec) < 0.25:
            same += 1
    n = len(reps)
    print(f"\nRECONCILE @3R vs journal: sign-match {sign_ok}/{n} "
          f"({sign_ok/n*100:.0f}%), close(<0.25R) {same}/{n} ({same/n*100:.0f}%)")


def near_miss_table(reps: list[TradeReplay], top: int = 15) -> None:
    losses = [r for r in reps if r.p.outcome_r <= 0]
    losses.sort(key=lambda r: r.mfe_r, reverse=True)
    print(f"\nTOP {top} NEAR-MISS LOSSES (losses that ran furthest in our favour first)")
    print(f"{'sym':10}{'tf':4}{'dir':>4}{'band':>6}{'mfe_r':>7}{'mae_r':>7}{'outR':>6}")
    for r in losses[:top]:
        d = "L" if (r.p.direction or 1) > 0 else "S"
        print(f"{r.p.symbol:10}{r.p.timeframe:4}{d:>4}{r.band:>6}"
              f"{r.mfe_r:>7.2f}{r.mae_r:>7.2f}{r.p.outcome_r:>6.1f}")
    wins = [r for r in reps if r.p.outcome_r > 0]
    wins.sort(key=lambda r: r.mae_r)
    print("\nTOP 5 BARELY-SURVIVED WINS (deepest adverse excursion before winning)")
    for r in wins[:5]:
        d = "L" if (r.p.direction or 1) > 0 else "S"
        print(f"  {r.p.symbol:10}{r.p.timeframe:4}{d:>3}{r.band:>6}"
              f"  mae_r={r.mae_r:>6.2f}  mfe_r={r.mfe_r:>5.2f}  outR={r.p.outcome_r:>4.1f}")


def _stats(net_rs: list[float]) -> tuple:
    """(n, win_rate, expectancy, total, profit_factor) over a list of net R."""
    n = len(net_rs)
    if n == 0:
        return (0, 0.0, 0.0, 0.0, 0.0)
    wins = [r for r in net_rs if r > 0]
    losses = [r for r in net_rs if r < 0]
    pf = (sum(wins) / abs(sum(losses))) if losses else float("inf")
    return (n, len(wins) / n, sum(net_rs) / n, sum(net_rs), pf)


def _net_at(r: TradeReplay, R: float) -> float | None:
    g = r.swept.get(R)
    return None if g is None else g - r.fee_r


def target_sweep(reps: list[TradeReplay]) -> None:
    print("\n" + "=" * 70)
    print("STEP 2 — TARGET SWEEP (same trades, real bars, NET of fees)")
    print("=" * 70)
    bands = sorted({r.band for r in reps})
    for scope, subset in [("OVERALL", reps)] + [(b, [r for r in reps if r.band == b])
                                                for b in bands]:
        print(f"\n[{scope}]  n={len(subset)}")
        print(f"  {'target':>7}{'WR':>7}{'exp_r':>8}{'netR':>8}{'PF':>7}")
        for R in SWEEP_TARGETS:
            nets = [v for v in (_net_at(r, R) for r in subset) if v is not None]
            n, wr, exp, tot, pf = _stats(nets)
            pf_s = "inf" if pf == float("inf") else f"{pf:.2f}"
            print(f"  {R:>7.1f}{wr*100:>6.0f}%{exp:>8.2f}{tot:>8.1f}{pf_s:>7}")


def adaptive(reps: list[TradeReplay]) -> None:
    print("\n" + "=" * 70)
    print("STEP 3 — ADAPTIVE R:R BY BAND + 'drop 60%' comparison (NET of fees)")
    print("=" * 70)
    # Baseline: 3R flat (what the live config does today).
    base = [_net_at(r, 3.0) for r in reps]
    base = [v for v in base if v is not None]
    print(f"\n  baseline 3R-flat        : netR={sum(base):>7.1f}  exp={sum(base)/len(base):>6.2f}  n={len(base)}")

    # Adaptive map: lower target on the bleed bands, keep 3R where it works.
    amap = {"50%": 2.0, "60%": 1.5, "70%": 3.0, "80%": 3.0}
    adp = []
    for r in reps:
        R = amap.get(r.band, 3.0)
        v = _net_at(r, R)
        if v is not None:
            adp.append(v)
    print(f"  adaptive {amap}")
    print(f"    -> netR={sum(adp):>7.1f}  exp={sum(adp)/len(adp):>6.2f}  n={len(adp)}")

    # Frontrunner: simply DROP the 60% band, keep everyone else at 3R flat.
    drop60 = [_net_at(r, 3.0) for r in reps if r.band != "60%"]
    drop60 = [v for v in drop60 if v is not None]
    print(f"  drop 60% band (rest 3R) : netR={sum(drop60):>7.1f}  "
          f"exp={sum(drop60)/len(drop60):>6.2f}  n={len(drop60)}")

    # Best per-band single target (which fixed R maximises each band's net total).
    print("\n  best single target per band (net total R):")
    for b in sorted({r.band for r in reps}):
        sub = [r for r in reps if r.band == b]
        best_R, best_tot = None, None
        for R in SWEEP_TARGETS:
            nets = [v for v in (_net_at(r, R) for r in sub) if v is not None]
            tot = sum(nets)
            if best_tot is None or tot > best_tot:
                best_R, best_tot = R, tot
        base_b = sum(v for v in (_net_at(r, 3.0) for r in sub) if v is not None)
        print(f"    {b:>5}: best={best_R}R netR={best_tot:>6.1f}  (vs 3R {base_b:>6.1f})")


def save_json(reps: list[TradeReplay]) -> None:
    rows = []
    for r in reps:
        rows.append({
            "id": r.p.id, "symbol": r.p.symbol, "timeframe": r.p.timeframe,
            "direction": r.p.direction, "band": r.band, "setup": r.p.setup,
            "status": r.p.status, "outcome_r": r.p.outcome_r,
            "mfe_r": round(r.mfe_r, 4), "mae_r": round(r.mae_r, 4),
            "n_bars": r.n_bars, "fee_r": round(r.fee_r, 4),
            "filled_at": r.p.filled_at, "resolved_at": r.p.resolved_at,
            "swept_gross_r": {str(k): (None if v is None else round(v, 4))
                              for k, v in r.swept.items()},
        })
    json.dump(rows, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}  ({len(rows)} trades)")


if __name__ == "__main__":
    reps = run()
    reconcile(reps)
    near_miss_table(reps)
    target_sweep(reps)
    adaptive(reps)
    save_json(reps)
