"""Micro-stake / high-leverage / break-even viability study (READ-ONLY, offline analysis).

Forward-test observation: a high share of entries go briefly green before their
final outcome. The idea under test: enter TINY stake, use HIGH leverage, and move
the stop to break-even once the trade has "proved" direction — does that survive
real fees, spread, slippage, funding, and (the killer) liquidation?

This script does NOT touch the journal, the engine, or any live path. It:
  1. loads resolved bracket trades from data/journal.json,
  2. re-fetches each trade's post-fill bar PATH (shared RouterClient; paged so it
     reaches back far enough), and builds a per-bar R path,
  3. derives the per-trade metrics the study needs (MFE/MAE in R, time-to-+XR,
     1R/2R/3R touches, green-then-stopped, BE-would-save / BE-cuts-a-winner),
  4. simulates BE triggers × management policies (path-dependent, intrabar
     ADVERSE-FIRST so we never over-credit break-even),
  5. runs a leverage-aware liquidation + friction + risk-of-ruin simulation, and
  6. prints the 12-point report.

Honesty rails (see the project thesis): expectancy and drawdown beat "percent
green"; liquidation cases are shown, not hidden; nothing is called viable unless
it survives the realistic AND harsh friction models. All friction/MMR numbers are
EXPLICIT ASSUMPTIONS, labelled as such.

Run:  PYTHONPATH=. python scripts/leverage_be_study.py            # text report
      PYTHONPATH=. python scripts/leverage_be_study.py --json out.json
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime

import numpy as np
import pandas as pd

from kudbee_quant.ingest import RouterClient
from kudbee_quant.journal.journal import DEFAULT_PATH, Prediction

# ----------------------------------------------------------------------------
# Assumptions (all explicit; change here, not buried in code).
# ----------------------------------------------------------------------------
TRIGGERS = [("first_green", 1e-9), ("+0.10R", 0.10), ("+0.25R", 0.25),
            ("+0.50R", 0.50), ("+1.00R", 1.00)]
LEVERAGES = [1, 10, 25, 50]   # 1 = no leverage (spot-equivalent) baseline
# Exit-geometry sweep: stop distance as a MULTIPLE of today's stop (1.0 = current).
# Target is held at 3R of the (scaled) stop and break-even arms at trigger_R of it.
STOP_WIDTHS = [0.5, 1.0, 1.5, 2.0]
MMR = 0.005          # maintenance-margin rate assumption (~0.5%); liq ≈ 1/L − MMR
STAKE_USD = 1.0      # micro margin posted per trade ($1)
BANKROLL_UNITS = 100  # ruin sim: bankroll = 100 stakes ($100); each trade risks ≤1 stake

TF_MIN = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "2h": 120, "4h": 240}

# Round-trip friction as a fraction of PRICE (entry+exit combined), + funding/day.
FRICTION = {
    "low":   {"roundtrip_pct": 0.0002, "funding_per_day": 0.0},      # maker/zero-fee, tight
    "real":  {"roundtrip_pct": 0.0015, "funding_per_day": 0.0001},   # taker + avg spread + small slip
    "harsh": {"roundtrip_pct": 0.0030, "funding_per_day": 0.0003},   # taker both sides + worse spread/slip + funding
}

MAJORS = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
          "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT", "DOTUSDT",
          "TRXUSDT", "MATICUSDT"}


def market_class(symbol: str) -> str:
    if symbol.lower().startswith("yahoo:"):
        return "tradfi (index/metal/oil/fx)"
    return "crypto major" if symbol in MAJORS else "crypto alt"


# ----------------------------------------------------------------------------
# Per-trade path + metrics
# ----------------------------------------------------------------------------
@dataclass
class TradePath:
    p: Prediction
    rhi: np.ndarray          # per-bar favourable-extreme R (direction-aware high)
    rlo: np.ndarray          # per-bar adverse-extreme R (direction-aware low)
    rclose: np.ndarray       # per-bar close R
    stop_pct: float          # stop distance as % of entry (1R in price%)
    target_r: float
    has_path: bool = True

    # filled lazily
    mfe_r: float = 0.0
    mae_r: float = 0.0
    mae_pct: float = 0.0     # worst adverse excursion in PRICE % (for liquidation)
    first_green_bar: int | None = None
    bars_to: dict = field(default_factory=dict)
    hit: dict = field(default_factory=dict)
    green_then_stopped: bool = False


def _need_bars(tf: str, span_days: float) -> int:
    per_day = 1440 / TF_MIN.get(tf, 60)
    return int(min(5000, max(300, (span_days + 2) * per_day)))


def build_path(p: Prediction, client: RouterClient, klcache: dict) -> TradePath | None:
    if p.kind != "bracket" or p.entry is None or p.stop is None:
        return None
    risk = abs(p.entry - p.stop)
    if risk <= 0:
        return None
    stop_pct = risk / p.entry * 100.0
    start = datetime.fromisoformat(p.filled_at or p.created_at)
    end = datetime.fromisoformat(p.resolved_at) if p.resolved_at else None
    span_days = ((end or start) - start).total_seconds() / 86400 if end else 5

    key = (p.symbol, p.timeframe)
    if key not in klcache:
        try:
            klcache[key] = client.klines(p.symbol, interval=p.timeframe,
                                         limit=_need_bars(p.timeframe, 11))
        except Exception:
            klcache[key] = None
    df = klcache[key]
    tp = TradePath(p=p, rhi=np.array([]), rlo=np.array([]), rclose=np.array([]),
                   stop_pct=stop_pct, target_r=p.target_r or 3.0, has_path=False)
    if df is None or df.empty:
        return tp
    ts = pd.to_datetime(df["timestamp"], utc=True)
    mask = ts >= start
    if end is not None:
        mask &= ts <= end
    w = df[mask]
    if w.empty:
        return tp
    d = p.direction or 1.0
    hi = w["high"].to_numpy(float)
    lo = w["low"].to_numpy(float)
    cl = w["close"].to_numpy(float)
    # direction-aware favourable / adverse extremes per bar
    fav = d * (np.where(d > 0, hi, lo) - p.entry) / risk
    adv = d * (np.where(d > 0, lo, hi) - p.entry) / risk
    tp.rhi, tp.rlo, tp.rclose = fav, adv, d * (cl - p.entry) / risk
    tp.has_path = True
    tp.mfe_r = float(fav.max())
    tp.mae_r = float(adv.min())
    tp.mae_pct = abs(tp.mae_r) * stop_pct          # worst adverse move, % of price
    green = np.where(fav > 0)[0]
    tp.first_green_bar = int(green[0]) if len(green) else None
    for label, thr in [("0.10", 0.10), ("0.25", 0.25), ("0.50", 0.50),
                       ("1.00", 1.00), ("2.00", 2.0), ("3.00", 3.0)]:
        idx = np.where(fav >= thr)[0]
        tp.bars_to[label] = int(idx[0]) if len(idx) else None
    for r in (1.0, 2.0, 3.0):
        tp.hit[r] = bool(tp.mfe_r >= r)
    tp.green_then_stopped = bool(tp.mfe_r > 0 and p.status == "miss")
    return tp


# ----------------------------------------------------------------------------
# Management-policy simulation over a path (gross R, intrabar adverse-first).
# ----------------------------------------------------------------------------
def sim_policy(tp: TradePath, *, be_trigger: float | None, be_level: float,
               partial_at: float | None = None, partial_frac: float = 0.5,
               rest_target: float | None = None, trail_after: float | None = None,
               trail_dist: float = 1.0) -> float:
    """Replay the path bar by bar and return realized GROSS R for one policy.

    be_trigger: arm a stop at ``be_level`` (in R) once favourable R >= trigger
        (armed from the NEXT bar). None = stop stays at −1R.
    partial_at / partial_frac / rest_target: bank ``partial_frac`` at ``partial_at`` R,
        move stop to BE on the remainder, run remainder to ``rest_target`` R.
    trail_after / trail_dist: once favourable R >= trail_after, trail stop at
        (running max R − trail_dist), updated at each bar close.
    Intrabar: adverse extreme is checked BEFORE the favourable one (conservative).
    """
    rhi, rlo = tp.rhi, tp.rlo
    if len(rhi) == 0:
        return float("nan")
    target = tp.target_r
    stop = -1.0
    armed = False
    banked = 0.0
    frac_open = 1.0
    run_max = -np.inf
    for i in range(len(rhi)):
        # adverse first
        if rlo[i] <= stop:
            return banked + frac_open * stop
        # favourable: partial / final target
        if partial_at is not None and frac_open == 1.0 and rhi[i] >= partial_at:
            banked += partial_frac * partial_at
            frac_open = 1.0 - partial_frac
            stop = max(stop, be_level)        # remainder protected at BE
            target = rest_target if rest_target is not None else target
        if rhi[i] >= target:
            return banked + frac_open * target
        run_max = max(run_max, rhi[i])
        # arm break-even (from next bar) once trigger reached
        if be_trigger is not None and not armed and rhi[i] >= be_trigger:
            stop = max(stop, be_level)
            armed = True
        # trailing
        if trail_after is not None and run_max >= trail_after:
            stop = max(stop, run_max - trail_dist)
    # ran out of bars: mark to last close R on the still-open fraction
    return banked + frac_open * float(tp.rclose[-1])


VARIANTS = {}  # name -> kwargs for sim_policy


def _register_variants():
    VARIANTS["original"] = dict(be_trigger=None, be_level=-1.0)
    for label, thr in TRIGGERS:
        VARIANTS[f"BE@{label}"] = dict(be_trigger=thr, be_level=0.0)
        VARIANTS[f"BE+fee@{label}"] = dict(be_trigger=thr, be_level=0.05)
        VARIANTS[f"lock+0.1R@{label}"] = dict(be_trigger=thr, be_level=0.10)
    VARIANTS["partial@1R→2R,BE"] = dict(be_trigger=None, be_level=0.0,
                                        partial_at=1.0, rest_target=2.0)
    VARIANTS["partial@1R→3R,BE"] = dict(be_trigger=None, be_level=0.0,
                                        partial_at=1.0, rest_target=3.0)
    VARIANTS["partial@0.5R,BE"] = dict(be_trigger=None, be_level=0.0,
                                       partial_at=0.5, rest_target=None)
    VARIANTS["trail_after_1R"] = dict(be_trigger=None, be_level=-1.0,
                                      trail_after=1.0, trail_dist=1.0)


_register_variants()


# ----------------------------------------------------------------------------
# Friction (price % -> R via stop distance) and leverage/liquidation.
# ----------------------------------------------------------------------------
def hold_days_of(tp: TradePath) -> float:
    """Approx holding time (days) for the funding-cost term. Uses bars-to-+1R as a
    proxy, falling back to the full path length. Explicit ``is None`` check — a +1R
    touch on bar 0 (bars_to==0) is a REAL fast touch, not 'never reached'."""
    b = tp.bars_to.get("1.00")
    bars = b if b is not None else len(tp.rhi)
    return bars * TF_MIN.get(tp.p.timeframe, 60) / 1440.0


def friction_r(tp: TradePath, model: str, hold_days: float) -> float:
    f = FRICTION[model]
    cost_pct = f["roundtrip_pct"] * 100 + f["funding_per_day"] * 100 * hold_days
    return cost_pct / tp.stop_pct           # price % -> R via 1R = stop_pct%


def liquidated(tp: TradePath, leverage: int) -> bool:
    """Did the position's worst adverse PRICE move breach the liquidation band
    (≈ 1/L − MMR) at any point before it resolved? If so the stake is wiped
    regardless of the eventual bracket outcome."""
    liq_pct = (1.0 / leverage - MMR) * 100.0
    return liq_pct <= 0 or tp.mae_pct >= liq_pct


# ----------------------------------------------------------------------------
# Report helpers
# ----------------------------------------------------------------------------
def pct(x):
    return f"{100*x:.0f}%"


def expectancy(rs):
    rs = [r for r in rs if r == r]
    return (sum(rs) / len(rs)) if rs else float("nan"), len(rs)


def risk_of_ruin(net_usd: list[float], horizons=(100, 500, 1000), trials=2000,
                 bankroll=None, seed=7):
    """Monte-Carlo bootstrap of per-trade $ outcomes. Ruin = bankroll hits 0."""
    arr = np.array([x for x in net_usd if x == x])
    if len(arr) == 0:
        return {h: float("nan") for h in horizons}
    bankroll = bankroll if bankroll is not None else BANKROLL_UNITS * STAKE_USD
    rng = np.random.default_rng(seed)
    out = {}
    for h in horizons:
        ruined = 0
        for _ in range(trials):
            draws = arr[rng.integers(0, len(arr), size=h)]
            if (bankroll + np.cumsum(draws)).min() <= 0:
                ruined += 1
        out[h] = ruined / trials
    return out


# ----------------------------------------------------------------------------
# EXIT-GEOMETRY SWEEP (5m) — read-only offline study (research/exit-geometry-sweep)
#
# Sweeps the STOP WIDTH (a multiple of today's stop) x the BREAK-EVEN TRIGGER,
# holding the target at 3R of the (scaled) stop, on 5m trades only. Everything is
# re-walked ADVERSE-FIRST via the SAME tested sim_policy: we just rescale each
# path's R arrays by 1/w so that 1 NEW-R == w * (original stop distance). Outcomes
# and expectancy are reported in NEW-R, i.e. normalised to the risk actually taken
# at that width, so widths are directly comparable. Friction (a price% cost) maps
# to NEW-R as friction_r_original / w, since a wider stop dilutes a fixed % cost.
#
# NOTHING here changes the engine, the journal, the workflow, or any live path.
# ----------------------------------------------------------------------------
def _scaled(tp: TradePath, w: float) -> TradePath:
    """A view of the path at stop width ``w``: R arrays rescaled to NEW-R (1 NEW-R
    = w*original stop) and the target pinned at 3R. Reuses sim_policy unchanged."""
    return replace(tp, rhi=tp.rhi / w, rlo=tp.rlo / w, rclose=tp.rclose / w,
                   target_r=3.0)


def _session(p: Prediction) -> str:
    """UTC session bucket from the fill hour (the §48 toxic-window lens)."""
    try:
        h = datetime.fromisoformat(p.filled_at or p.created_at).hour
    except Exception:
        return "unknown"
    if 0 <= h < 8:
        return "asia_00-08"
    if 8 <= h < 13:
        return "london_08-13"
    if 13 <= h < 21:
        return "ny_13-21"
    return "late_21-24"


def _band(p: Prediction) -> str:
    """Confluence-pct band from the setup label (e.g. confluence_r_60pct_tf -> 60pct)."""
    s = p.setup or ""
    for b in ("50pct", "60pct", "70pct", "80pct", "90pct"):
        if b in s:
            return b
    return "other"


def sizing_sim(per_trade_r, risks=(0.02, 0.03, 0.05), n_trades=100,
               start=1000.0, trials=4000, seed=11):
    """Bootstrap the best combo's per-trade R outcomes and COMPOUND at a fixed
    fraction-of-balance risk (risk*R per trade; -1R loses the full risk fraction).
    Returns median ending balance and median worst drawdown for each risk %.
    (Same i.i.d. bootstrap spirit as risk_of_ruin; treat as a floor — real streaks
    autocorrelate.)"""
    arr = np.array([r for r in per_trade_r if r == r])
    out = {}
    if len(arr) == 0:
        return {r: {"median_end": float("nan"), "median_maxdd": float("nan")} for r in risks}
    rng = np.random.default_rng(seed)
    for risk in risks:
        ends, dds = [], []
        for _ in range(trials):
            draws = arr[rng.integers(0, len(arr), size=n_trades)]
            bal = peak = start
            mdd = 0.0
            for r in draws:
                bal *= (1.0 + risk * r)
                if bal <= 0:
                    bal = 0.0
                peak = max(peak, bal)
                mdd = max(mdd, (peak - bal) / peak if peak > 0 else 1.0)
                if bal == 0.0:
                    break
            ends.append(bal)
            dds.append(mdd)
        out[risk] = {"median_end": float(np.median(ends)),
                     "median_maxdd": float(np.median(dds))}
    return out


def quarter_kelly_pct(per_trade_r) -> float:
    """Approx growth-optimal risk fraction f* ~= mean(R)/E[R^2] (continuous-Kelly
    small-edge form), then quarter-Kelly. <=0 means the edge says DON'T BET."""
    arr = np.array([r for r in per_trade_r if r == r])
    if len(arr) < 2:
        return float("nan")
    e_r2 = float(np.mean(arr ** 2))
    if e_r2 <= 0:
        return float("nan")
    return (float(np.mean(arr)) / e_r2) / 4.0 * 100.0


def exit_geometry_5m(argv):
    """STEP 4-6: stop-width x BE-trigger sweep on 5m, best combo, condition
    breakdown, and the 2/3/5% + quarter-Kelly sizing answer. Writes the two
    committed reports. Read-only over the journal; no engine/live change."""
    import os

    path = DEFAULT_PATH
    trades = [Prediction(**d) for d in json.loads(path.read_text())]
    resolved = [p for p in trades
                if p.status in ("hit", "miss") and p.kind == "bracket"
                and p.timeframe == "5m"]                     # 5m ONLY (STEP 4)
    client = RouterClient()
    klcache: dict = {}
    print(f"[exit-geometry] building paths for {len(resolved)} resolved 5m trades...",
          file=sys.stderr)
    paths = []
    for i, p in enumerate(resolved):
        tp = build_path(p, client, klcache)
        if tp is not None and tp.has_path and len(tp.rhi) > 0:
            paths.append(tp)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(resolved)}", file=sys.stderr)
    n = len(paths)
    if n == 0:
        print("No 5m paths with OHLCV coverage — cannot run the sweep.")
        return

    hold = {id(t): hold_days_of(t) for t in paths}
    triggers = [("no_BE", None)] + TRIGGERS     # baseline + each BE trigger (NEW-R)

    # ---- the sweep: per (stop_width x BE_trigger), target fixed at 3R ----------
    combos = []
    # cache per (w, trigger) the per-trade gross so we can also do save/cut + sizing
    gross_cache: dict = {}
    for w in STOP_WIDTHS:
        nobe = [sim_policy(_scaled(t, w), be_trigger=None, be_level=0.0) for t in paths]
        gross_cache[(w, "no_BE")] = nobe
        for tlabel, thr in triggers:
            gross = (nobe if tlabel == "no_BE"
                     else [sim_policy(_scaled(t, w), be_trigger=thr, be_level=0.0)
                           for t in paths])
            gross_cache[(w, tlabel)] = gross
            net_real = [g - friction_r(t, "real", hold[id(t)]) / w
                        for g, t in zip(gross, paths)]
            net_harsh = [g - friction_r(t, "harsh", hold[id(t)]) / w
                         for g, t in zip(gross, paths)]
            er, _ = expectancy(net_real)
            eh, _ = expectancy(net_harsh)
            wins = sum(1 for x in net_real if x > 1e-9)
            saved = sum(1 for a, b in zip(gross, nobe) if a > b + 1e-6)
            cut = sum(1 for a, b in zip(gross, nobe) if a < b - 1e-6)
            combos.append({
                "stop_width": w, "be_trigger": tlabel, "target_r": 3.0,
                "n": n, "exp_net_real": er, "exp_net_harsh": eh,
                "win_rate": wins / n,
                "be_would_save": saved, "be_cuts_winner": cut,
            })

    combos.sort(key=lambda c: c["exp_net_real"], reverse=True)
    best = combos[0]

    # ---- best combo per-trade NET-real R distribution (for sizing) ------------
    bw, bt = best["stop_width"], best["be_trigger"]
    best_gross = gross_cache[(bw, bt)]
    best_net_real = [g - friction_r(t, "real", hold[id(t)]) / bw
                     for g, t in zip(best_gross, paths)]

    # ---- condition breakdown at the BEST combo (cells shown with counts) ------
    def breakdown(keyfn):
        cells = {}
        for t, r in zip(paths, best_net_real):
            k = keyfn(t.p)
            cells.setdefault(k, []).append(r)
        rows = []
        for k, rs in cells.items():
            e, _ = expectancy(rs)
            rows.append({"cell": k, "n": len(rs), "exp_net_real": e,
                         "seed": len(rs) < 20})
        return sorted(rows, key=lambda x: (-x["n"]))
    cond = {
        "direction": breakdown(lambda p: "long" if (p.direction or 0) > 0 else "short"),
        "band": breakdown(_band),
        "session": breakdown(_session),
        "symbol": breakdown(lambda p: p.symbol),
    }

    # ---- STEP 6: sizing sim on the best combo's real edge --------------------
    sizing = sizing_sim(best_net_real)
    qk = quarter_kelly_pct(best_net_real)

    out = {
        "scope": "5m resolved bracket trades, exit-geometry sweep (read-only)",
        "n_5m_resolved": len(resolved), "n_with_path": n,
        "axes": {"stop_widths": STOP_WIDTHS,
                 "be_triggers": [t[0] for t in triggers],
                 "target_r": 3.0, "note": "target held at 3R of the scaled stop (STEP 4)"},
        "friction_models": {"real": FRICTION["real"], "harsh": FRICTION["harsh"]},
        "combos": combos,
        "best": best,
        "condition_breakdown_at_best": cond,
        "sizing_sim": {f"{int(r*100)}pct": v for r, v in sizing.items()},
        "quarter_kelly_pct": qk,
        "caveats": [
            "cells under ~20 trades are hypothesis seeds, confirm out-of-sample before trusting.",
            "R is normalised to the risk taken at each stop width (1 NEW-R = w*original stop).",
            "intrabar resolved ADVERSE-FIRST (reused sim_policy); BE never over-credited.",
            "expectancy is net of the labelled friction model; touches are not guaranteed fills.",
            "5m sample pools the §44 VWAP-flip regime; descriptive, not causal.",
        ],
    }

    # ---- write committed reports ---------------------------------------------
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    with open("data/exit_geometry_5m.json", "w") as fh:
        json.dump(out, fh, indent=2, default=str)

    _write_geometry_md("reports/exit_geometry_5m.md", out)

    # ---- console summary ------------------------------------------------------
    print("\n" + "=" * 78)
    print("EXIT-GEOMETRY SWEEP — 5m ONLY (read-only; no live change)")
    print("=" * 78)
    print(f"5m resolved: {len(resolved)}  |  with usable path: {n}")
    print("\n[STEP 5] stop_width x BE_trigger (target = 3R of scaled stop), "
          "expectancy in R net of real & harsh fees:\n")
    print(f"    {'width':>6}{'BE_trig':>12}{'n':>5}{'win%':>7}"
          f"{'net_real':>10}{'net_harsh':>11}{'BE_save':>9}{'BE_cut':>8}")
    for c in combos:
        print(f"    {c['stop_width']:>6.1f}{c['be_trigger']:>12}{c['n']:>5}"
              f"{100*c['win_rate']:>6.0f}%{c['exp_net_real']:>10.3f}"
              f"{c['exp_net_harsh']:>11.3f}{c['be_would_save']:>9}{c['be_cuts_winner']:>8}")
    print(f"\n  BEST by net-of-real: stop_width={best['stop_width']}x  "
          f"BE_trigger={best['be_trigger']}  target=3R  ->  "
          f"{best['exp_net_real']:+.3f}R/trade (net real), "
          f"{best['exp_net_harsh']:+.3f}R (harsh), win {100*best['win_rate']:.0f}%, n={best['n']}.")

    print("\n[STEP 5] Condition breakdown at the best combo "
          "(net-real R; * = <20 trades = hypothesis seed):")
    for dim, rows in cond.items():
        print(f"  by {dim}:")
        for r in rows[:12]:
            mark = " *" if r["seed"] else ""
            print(f"      {str(r['cell']):<14} n={r['n']:<4} {r['exp_net_real']:+.3f}R{mark}")
    print("  cells under ~20 trades are hypothesis seeds, confirm out-of-sample "
          "before trusting.")

    print(f"\n[STEP 6] Sizing on the BEST combo's REAL edge "
          f"({best['exp_net_real']:+.3f}R/trade), 100 trades, $1,000 start:")
    print(f"    {'risk/trade':>11}{'median end $':>14}{'median worst DD':>18}")
    for r in (0.02, 0.03, 0.05):
        s = sizing[r]
        print(f"    {int(r*100):>10}%{s['median_end']:>14.0f}{100*s['median_maxdd']:>17.0f}%")
    qk_txt = (f"{qk:.2f}% risk/trade" if qk == qk and qk > 0
              else "<= 0% (edge says DO NOT BET)")
    print(f"    Quarter-Kelly suggested: {qk_txt}")
    print("\nNot financial advice. Offline analysis only — no live changes made.")
    return out


def _write_geometry_md(fpath: str, out: dict) -> None:
    best = out["best"]
    L = []
    L.append("# Exit-geometry sweep — 5m (read-only study)\n")
    L.append("> Offline replay over resolved **5m** bracket trades. Sweeps the **stop "
             "width** (a multiple of today's stop) against the **break-even trigger**, "
             "target held at **3R** of the scaled stop. R is normalised to the risk "
             "taken at each width (1 NEW-R = w x original stop), so widths compare "
             "directly. Intrabar resolved **adverse-first** (reused `sim_policy`). "
             "**No engine / journal / workflow / live change.**\n")
    L.append(f"- 5m resolved bracket trades: **{out['n_5m_resolved']}** "
             f"(usable path: **{out['n_with_path']}**)")
    L.append(f"- Axes: stop_widths {out['axes']['stop_widths']} x BE_triggers "
             f"{out['axes']['be_triggers']}, target=3R\n")
    L.append(f"## Best combo (by expectancy net of **real** fees)\n")
    L.append(f"**stop_width = {best['stop_width']}x, BE_trigger = {best['be_trigger']}, "
             f"target = 3R** -> **{best['exp_net_real']:+.3f} R/trade** net-real "
             f"({best['exp_net_harsh']:+.3f} harsh), win {100*best['win_rate']:.0f}%, "
             f"n={best['n']}, BE saved {best['be_would_save']} / cut {best['be_cuts_winner']}.\n")
    L.append("## Full sweep (net-of-real / net-of-harsh expectancy in R)\n")
    L.append("| stop_width | BE_trigger | n | win% | net_real | net_harsh | BE_save | BE_cut |")
    L.append("|---:|---|---:|---:|---:|---:|---:|---:|")
    for c in out["combos"]:
        L.append(f"| {c['stop_width']:.1f}x | {c['be_trigger']} | {c['n']} | "
                 f"{100*c['win_rate']:.0f}% | {c['exp_net_real']:+.3f} | "
                 f"{c['exp_net_harsh']:+.3f} | {c['be_would_save']} | {c['be_cuts_winner']} |")
    L.append("\n## Condition breakdown at the best combo (net-real R)\n")
    L.append("> `*` marks cells under ~20 trades — **hypothesis seeds, confirm "
             "out-of-sample before trusting.**\n")
    for dim, rows in out["condition_breakdown_at_best"].items():
        L.append(f"### by {dim}\n")
        L.append("| cell | n | net_real R |")
        L.append("|---|---:|---:|")
        for r in rows:
            mark = " *" if r["seed"] else ""
            L.append(f"| {r['cell']}{mark} | {r['n']} | {r['exp_net_real']:+.3f} |")
        L.append("")
    sz = out["sizing_sim"]
    L.append("## Sizing on the best combo's real edge (100 trades, $1,000 start)\n")
    L.append("| risk/trade | median ending $ | median worst drawdown |")
    L.append("|---:|---:|---:|")
    for key in ("2pct", "3pct", "5pct"):
        if key in sz:
            v = sz[key]
            L.append(f"| {key.replace('pct','%')} | {v['median_end']:.0f} | "
                     f"{100*v['median_maxdd']:.0f}% |")
    qk = out["quarter_kelly_pct"]
    qk_txt = (f"{qk:.2f}% risk/trade" if isinstance(qk, (int, float)) and qk == qk and qk > 0
              else "<= 0% (edge says DO NOT BET)")
    L.append(f"\n**Quarter-Kelly suggested risk:** {qk_txt}\n")
    L.append("## Caveats\n")
    for c in out["caveats"]:
        L.append(f"- {c}")
    L.append("\n_Not financial advice. Offline analysis/simulation only — no live "
             "changes made._\n")
    with open(fpath, "w") as fh:
        fh.write("\n".join(L))


def main(argv):
    if "--exit-geometry" in argv:
        exit_geometry_5m(argv)
        return
    path = DEFAULT_PATH
    trades = [Prediction(**d) for d in json.loads(path.read_text())]
    resolved = [p for p in trades if p.status in ("hit", "miss") and p.kind == "bracket"]
    client = RouterClient()
    klcache: dict = {}

    paths: list[TradePath] = []
    print(f"Fetching paths for {len(resolved)} resolved bracket trades "
          f"({len(set((p.symbol, p.timeframe) for p in resolved))} series)...",
          file=sys.stderr)
    for i, p in enumerate(resolved):
        tp = build_path(p, client, klcache)
        if tp is not None:
            paths.append(tp)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(resolved)}", file=sys.stderr)

    withp = [t for t in paths if t.has_path and len(t.rhi) > 0]
    n_all, n_path = len(paths), len(withp)

    # ---- 1-3: coverage, percent green, threshold hit-rates -----------------
    ever_green = [t for t in withp if t.mfe_r > 0]
    def reach(thr):
        return sum(1 for t in withp if t.mfe_r >= thr) / n_path if n_path else float("nan")

    out = {}
    print("\n" + "=" * 78)
    print("MICRO-STAKE / HIGH-LEVERAGE / BREAK-EVEN VIABILITY STUDY")
    print("=" * 78)
    print(f"\n[1] Trades analyzed: {n_all} resolved bracket trades; "
          f"{n_path} have usable bar paths "
          f"({n_all-n_path} lacked OHLCV coverage — mostly old 5m, reported honestly).")
    print(f"[2] Percent EVER green (MFE>0): {pct(len(ever_green)/n_path)} "
          f"({len(ever_green)}/{n_path})")
    print("[3] Reached favourable excursion of:")
    for label, thr in [("+0.10R", .1), ("+0.25R", .25), ("+0.50R", .5),
                       ("+1.00R", 1.), ("+2.00R", 2.), ("+3.00R", 3.)]:
        print(f"      {label}: {pct(reach(thr))}")
    out["coverage"] = {"resolved": n_all, "with_path": n_path}
    out["pct_ever_green"] = len(ever_green) / n_path if n_path else None
    out["reach"] = {k: reach(v) for k, v in
                    [("0.10", .1), ("0.25", .25), ("0.50", .5), ("1.0", 1.), ("2.0", 2.), ("3.0", 3.)]}

    # ---- BE "would have saved / cut a winner" diagnostics ------------------
    base = {id(t): sim_policy(t, **VARIANTS["original"]) for t in withp}
    be25 = {id(t): sim_policy(t, **VARIANTS["BE@+0.25R"]) for t in withp}
    saved = sum(1 for t in withp if be25[id(t)] > base[id(t)] + 1e-6)
    cut = sum(1 for t in withp if be25[id(t)] < base[id(t)] - 1e-6)
    print(f"\n  BE@+0.25R vs original (path-replayed): saved {saved} trades from a "
          f"deeper loss; cut {cut} eventual winners short.")

    # ---- timing: how fast does the favourable move arrive? -----------------
    def med_hours(label):
        hrs = [t.bars_to[label] * TF_MIN.get(t.p.timeframe, 60) / 60.0
               for t in withp if t.bars_to.get(label) is not None]
        return float(np.median(hrs)) if hrs else float("nan")
    print("  Time to favourable excursion (median hours, among trades that reached it):")
    for label in ("0.10", "0.25", "0.50", "1.00"):
        print(f"      +{label}R: {med_hours(label):.1f}h", end="   ")
    print()

    # ---- per-trade export (every Required-metric, one row per trade) -------
    recs = []
    for t in withp:
        b, b25 = base[id(t)], be25[id(t)]
        tfm = TF_MIN.get(t.p.timeframe, 60) / 60.0
        recs.append({
            "id": t.p.id, "symbol": t.p.symbol, "market": market_class(t.p.symbol),
            "timeframe": t.p.timeframe,
            "direction": "long" if (t.p.direction or 0) > 0 else "short",
            "entry": t.p.entry, "stop": t.p.stop, "target": t.p.target,
            "target_r": t.target_r, "stop_pct": round(t.stop_pct, 4),
            "mfe_r": round(t.mfe_r, 4), "mae_r": round(t.mae_r, 4),
            "mae_pct": round(t.mae_pct, 4),
            "hrs_first_green": (t.first_green_bar * tfm) if t.first_green_bar is not None else None,
            "hrs_0.10R": (t.bars_to["0.10"] * tfm) if t.bars_to.get("0.10") is not None else None,
            "hrs_0.25R": (t.bars_to["0.25"] * tfm) if t.bars_to.get("0.25") is not None else None,
            "hrs_0.50R": (t.bars_to["0.50"] * tfm) if t.bars_to.get("0.50") is not None else None,
            "hrs_1.00R": (t.bars_to["1.00"] * tfm) if t.bars_to.get("1.00") is not None else None,
            "hit_1R": t.hit[1.0], "hit_2R": t.hit[2.0], "hit_3R": t.hit[3.0],
            "green_then_stopped": t.green_then_stopped,
            "final_r": round(b, 4), "be25_r": round(b25, 4),
            "be_would_save": bool(b25 > b + 1e-6),
            "be_cuts_winner": bool(b25 < b - 1e-6),
        })
    if "--csv" in argv:
        cp = argv[argv.index("--csv") + 1]
        pd.DataFrame(recs).to_csv(cp, index=False)
        print(f"  Wrote per-trade table ({len(recs)} rows) -> {cp}", file=sys.stderr)
    out["per_trade_sample"] = recs[:5]


    # ---- 4-5: variant expectancy, gross + each friction model -------------
    hold_days = {id(t): hold_days_of(t) for t in withp}
    rows = []
    for name, kw in VARIANTS.items():
        gross = [sim_policy(t, **kw) for t in withp]
        rec = {"variant": name}
        rec["gross"], _ = expectancy(gross)
        for m in ("low", "real", "harsh"):
            net = [g - friction_r(t, m, hold_days[id(t)]) for g, t in zip(gross, withp) if g == g]
            rec[m], _ = expectancy(net)
        rows.append(rec)
    rows.sort(key=lambda r: r["real"], reverse=True)
    out["variants"] = rows
    print("\n[4-5] Management variants — expectancy in R (mean), gross then net of "
          "each friction model. Sorted by REALISTIC net:\n")
    print(f"    {'variant':<22}{'gross':>9}{'low':>9}{'real':>9}{'harsh':>9}")
    for r in rows:
        print(f"    {r['variant']:<22}{r['gross']:>9.3f}{r['low']:>9.3f}"
              f"{r['real']:>9.3f}{r['harsh']:>9.3f}")
    best = rows[0]
    print(f"\n    Best variant by realistic-net expectancy: {best['variant']} "
          f"({best['real']:+.3f}R/trade).")

    # ---- 6: long vs short --------------------------------------------------
    print("\n[6] Expectancy by direction (original strategy, gross / realistic-net):")
    for d, lbl in [(1.0, "long"), (-1.0, "short")]:
        sub = [t for t in withp if (t.p.direction or 0) > 0] if d > 0 else \
              [t for t in withp if (t.p.direction or 0) < 0]
        g, n = expectancy([base[id(t)] for t in sub])
        nr, _ = expectancy([base[id(t)] - friction_r(t, "real", hold_days[id(t)]) for t in sub])
        print(f"      {lbl:<6} n={n:<4} gross {g:+.3f}R   real-net {nr:+.3f}R")

    # ---- 7: by market class (each at its NATIVE venue friction) -----------
    # TradFi (Yahoo) is the zero-fee promo venue -> read at LOW friction; crypto
    # pays taker -> read at REALISTIC. Applying crypto fees to the zero-fee book
    # would understate it, so we use each venue's own model.
    native = {"crypto major": "real", "crypto alt": "real",
              "tradfi (index/metal/oil/fx)": "low"}
    print("\n[7] Expectancy by market class (original; gross / NATIVE-venue net):")
    out["by_market"] = {}
    for cls in ("crypto major", "crypto alt", "tradfi (index/metal/oil/fx)"):
        sub = [t for t in withp if market_class(t.p.symbol) == cls]
        if not sub:
            continue
        m = native[cls]
        g, n = expectancy([base[id(t)] for t in sub])
        nr, _ = expectancy([base[id(t)] - friction_r(t, m, hold_days[id(t)]) for t in sub])
        med_stop = float(np.median([t.stop_pct for t in sub]))
        print(f"      {cls:<30} n={n:<4} gross {g:+.3f}R  {m}-net {nr:+.3f}R  "
              f"(median stop {med_stop:.2f}%)")
        out["by_market"][cls] = {"n": n, "gross": g, "native_model": m, "native_net": nr}

    # ---- best variant, does it survive BY VENUE? --------------------------
    print(f"\n[7b] Best BE variant ({best['variant']}) net expectancy by venue model:")
    bg = {id(t): sim_policy(t, **VARIANTS[best["variant"]]) for t in withp}
    for venue, model in [("zero-fee / maker (low)", "low"), ("taker crypto (real)", "real"),
                         ("harsh", "harsh")]:
        e, _ = expectancy([bg[id(t)] - friction_r(t, model, hold_days[id(t)]) for t in withp])
        verdict = "POSITIVE" if e > 0 else "negative"
        print(f"      {venue:<26} {e:+.3f}R/trade  -> {verdict}")

    # ---- 8 & 10: leverage / liquidation / EV$ / risk-of-ruin --------------
    maep = np.array([t.mae_pct for t in withp])
    print(f"\n[8/10] Leverage simulation (stake ${STAKE_USD:.0f} margin/trade, "
          f"MMR {MMR*100:.1f}%, liq ≈ 1/L−MMR). Best variant = {best['variant']}.")
    print(f"    Worst-adverse move (MAE, % of price): median {np.median(maep):.2f}%  "
          f"p75 {np.percentile(maep,75):.2f}%  p90 {np.percentile(maep,90):.2f}%  "
          f"(this vs the liq band below decides survival).")
    best_gross = {id(t): sim_policy(t, **VARIANTS[best["variant"]]) for t in withp}
    print(f"    {'lev':>4}{'liq%':>7}{'%liq':>7}{'maxloss$':>10}"
          f"{'EV$/trade(real)':>17}{'RoR@100':>9}{'@500':>8}{'@1000':>9}")
    out["leverage"] = []
    for L in LEVERAGES:
        liq_pct = (1.0 / L - MMR) * 100
        net_usd = []
        nliq = 0
        for t in withp:
            r_dollars = STAKE_USD * L * (t.stop_pct / 100.0)   # $ value of 1R at this leverage
            if liquidated(t, L):
                nliq += 1
                net_usd.append(-STAKE_USD)                     # stake wiped (bounded by micro size)
            else:
                gr = best_gross[id(t)]
                net_r = gr - friction_r(t, "real", hold_days[id(t)])
                net_usd.append(net_r * r_dollars)
        ev = float(np.nanmean(net_usd))
        ror = risk_of_ruin(net_usd)
        print(f"    {L:>4}{liq_pct:>6.1f}%{pct(nliq/n_path):>7}{-STAKE_USD:>9.2f}"
              f"{ev:>17.4f}{pct(ror[100]):>9}{pct(ror[500]):>8}{pct(ror[1000]):>9}")
        out["leverage"].append({"L": L, "liq_pct": liq_pct, "pct_liquidated": nliq / n_path,
                                "ev_usd": ev, "ror": ror})

    # ---- 9: min win rate needed -------------------------------------------
    print(f"\n[9] Break-even win rate needed (reward:risk, with realistic friction "
          f"at the MEDIAN stop {np.median([t.stop_pct for t in withp]):.2f}%):")
    med_stop = float(np.median([t.stop_pct for t in withp]))
    c = FRICTION["real"]["roundtrip_pct"] * 100 / med_stop   # friction in R at median stop
    for k in (1, 2, 3):
        p_be = (1 + c) / (k + 1 + c)  # solve p(k−c) = (1−p)(1+c)
        actual = reach(float(k))
        print(f"      {k}R target: need win rate ≥ {pct(p_be)}  "
              f"(actual MFE-touch rate {pct(actual)} — touch ≠ fill)")

    print("\n" + "-" * 78)
    print("HONEST READ / ASSUMPTIONS")
    print("-" * 78)
    for line in [
        f"- Friction is price% → R via the stop: cost_R = roundtrip% / stop%. Tight "
        f"stops (median {med_stop:.2f}%) amplify friction — that is the core risk.",
        "- Intrabar conflicts resolved ADVERSE-FIRST, so BE/trailing are NOT over-credited.",
        "- Liquidation = worst adverse PRICE move ever breached 1/L−MMR; on liquidation "
        "the whole micro-stake is lost regardless of the bracket's eventual outcome.",
        f"- MMR fixed at {MMR*100:.1f}% (real Binance MMR is tier/size dependent — alts are worse).",
        "- 'percent green' and MFE-touch rates are TOUCHES, not guaranteed fills at the wick.",
        "- Risk-of-ruin bootstraps observed per-trade $ outcomes (i.i.d. assumption; "
        f"bankroll = {BANKROLL_UNITS}×stake). Real streaks are autocorrelated → treat as a floor.",
        f"- TradFi (Yahoo) n is small ({sum(1 for t in withp if market_class(t.p.symbol).startswith('tradfi'))}) "
        "— directional, not conclusive. Index/oil/metal/FX are the zero-fee venue.",
        "- Sample pools the pre/post VWAP-flip regime (§44); descriptive, not causal.",
    ]:
        print(line)
    print("\nNot financial advice. Analysis/simulation only — no live changes made.")

    if "--json" in argv:
        jp = argv[argv.index("--json") + 1]
        # make ror keys strings for json
        for L in out["leverage"]:
            L["ror"] = {str(k): v for k, v in L["ror"].items()}
        with open(jp, "w") as fh:
            json.dump(out, fh, indent=2, default=str)
        print(f"\nWrote {jp}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
