"""Cycle-aware historical backtest of the confluence-R strategy.

PURPOSE (the task): reach a 1,000+ trade, out-of-sample, fee-modeled sample AND
test whether the live edge survives the CURRENT cycle regime. We are ~786 days
(~2.15 yrs) past the 2024-04-19 halving; the equivalent phase in the prior two
cycles was choppy/bearish (our problem regime). So we score the EXACT live rules
over the two cycle-analog windows plus a broad recent span, sliced four ways.

WHAT IS THE "LIVE RULES" (audited against config/validated_defaults.py + MEMORY §1):
  - signal:  confluence_position(min_pct=0.50, trend_align=True)  (>=50% of ~10
             factors aligned AND with the 800-EMA HTF trend)
  - bracket: bracket_backtest(stop_atr=1.5, target_r=3.0, max_bars=24,
             limit_retrace_atr=0.25, entry_window=6, fee_pct=...)  i.e. a
             0.25-ATR MAKER limit retrace, 1.5-ATR stop (=1R), 3R target, 24-bar
             time-stop. This is exactly BRACKET_KW + MIN_PCT + TREND_FILTER.

OUT-OF-SAMPLE: confluence_position is STATELESS — its parameters are frozen at the
validated defaults and are NEVER refit to any window here. The 2018 and 2022
cycle-analog windows are unseen regimes; the recent span post-dates the validation.
So every trade is out-of-sample w.r.t. parameter selection. We also report fold
robustness (fraction of time-folds positive) within each slice.

FEES (realistic, modeled): the strategy ENTERS maker (limit retrace) but its exits
(stop/target) can be taker. We report GROSS (0) and NET at three honest cost
levels (round-trip fraction of price), converted per-trade to R by the engine via
fee_pct*entry/stop_distance (so tiny sub-hourly stops correctly cost more R):
  - maker  0.0004  (config FEE_PCT — maker-only round-trip assumption)
  - mixed  0.00065 (maker entry 0.0002 + taker exit 0.00045 — MEMORY §25)
  - taker  0.0009  (full taker round-trip — MEASURED on live BTCC fills, §25)
NET headline = MAKER (the strategy's design); the mixed/taker columns are the
honest stress that especially bites the cost-sensitive sub-hourly timeframes.

Run:  python scripts/cycle_backtest.py
Output: docs/research/cycle_backtest.md  (+ console summary)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from kudbee_quant.backtest.bracket import bracket_backtest
from kudbee_quant.config.validated_defaults import (
    ENTRY_WINDOW, MAX_BARS, MIN_PCT, RETRACE_ATR, STOP_ATR, TARGET_R, TREND_FILTER,
)
from kudbee_quant.confluence.stack import confluence_position, confluence_score
from kudbee_quant.ingest.binance import BinanceClient
from kudbee_quant.levels import build_levels

# ---- the EXACT live execution config (audited; no refitting) -----------------
LIVE_BRACKET = dict(stop_atr=STOP_ATR, target_r=TARGET_R, max_bars=MAX_BARS,
                    limit_retrace_atr=RETRACE_ATR, entry_window=ENTRY_WINDOW)
FEES = {"gross": 0.0, "maker": 0.0004, "mixed": 0.00065, "taker": 0.0009}
NET_HEADLINE = "maker"  # the strategy's design cost; mixed/taker are the stress

# ---- the crypto majors the live bot trades (MEMORY §1) -----------------------
MAJORS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
          "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]
# Listing dates (verified vs Binance) gate the 2018 window to coins that existed.
LISTED = {"BTCUSDT": "2017-08", "ETHUSDT": "2017-08", "BNBUSDT": "2017-11",
          "ADAUSDT": "2018-04", "XRPUSDT": "2018-05", "LINKUSDT": "2019-01",
          "DOGEUSDT": "2019-07", "SOLUSDT": "2020-08", "AVAXUSDT": "2020-09",
          "DOTUSDT": "2020-08"}

TIMEFRAMES = ["5m", "15m", "1h"]


@dataclass(frozen=True)
class Window:
    key: str
    label: str
    start: str
    end: str
    regime: str  # "cycle-analog" | "recent"

    def universe(self) -> list[str]:
        return [s for s in MAJORS if LISTED[s] <= self.start[:7]]


WINDOWS = [
    Window("w2018", "2016-cycle analog (2018 chop)", "2018-07-15", "2018-10-31", "cycle-analog"),
    Window("w2022", "2020-cycle analog (2022 chop)", "2022-05-15", "2022-08-31", "cycle-analog"),
    Window("recent", "Recent span", "2024-06-01", "2026-06-14", "recent"),
]


# ---- per-trade extraction with confluence band + fee passes ------------------

def trades_for(df: pd.DataFrame, signal: pd.Series, fee_pct: float) -> list[float]:
    """Net-R list for one (frame, signal) at one cost. Uses the live engine."""
    res = bracket_backtest(df, signal, fee_pct=fee_pct, **LIVE_BRACKET)
    return list(res.trades)


def band_signal(df: pd.DataFrame, base_sig: pd.Series, lo: float, hi: float) -> pd.Series:
    """The live signal restricted to bars whose confluence_pct is in [lo, hi).

    base_sig already carries the >=50% gate + trend filter + direction, so this
    isolates a single confluence band without changing any execution logic.
    """
    pct = confluence_score(df)["confluence_pct"]
    mask = (pct >= lo - 1e-9) & (pct < hi - 1e-9)
    return base_sig.where(mask, 0.0)


# ---- pooled statistics on a net-R trade list ---------------------------------

def stats(trades: list[float]) -> dict:
    arr = np.asarray(trades, dtype=float)
    n = arr.size
    if n == 0:
        return dict(n=0, win=float("nan"), exp=float("nan"), total=0.0,
                    pf=float("nan"), maxdd=0.0)
    wins, losses = arr[arr > 0], arr[arr < 0]
    eq = np.cumsum(arr)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    pf = float(wins.sum() / -losses.sum()) if losses.sum() < 0 else float("inf")
    return dict(n=int(n), win=float((arr > 0).mean()), exp=float(arr.mean()),
                total=float(arr.sum()), pf=pf, maxdd=dd)


def boot_p(trades: list[float], iters: int = 5000, seed: int = 7) -> float:
    """One-sided bootstrap P(mean<=0) — the project's significance gate (§19/§23)."""
    arr = np.asarray(trades, dtype=float)
    if arr.size < 10:
        return float("nan")
    rng = np.random.default_rng(seed)
    means = rng.choice(arr, size=(iters, arr.size), replace=True).mean(axis=1)
    return float((means <= 0).mean())


# ---- data ---------------------------------------------------------------------

def load_frames(client: BinanceClient) -> dict:
    """Fetch + feature-build every (window, symbol, tf). Returns nested dict and a
    data-integrity report (bars, gaps)."""
    frames: dict = {}
    integrity: list[dict] = []
    for w in WINDOWS:
        frames[w.key] = {}
        for tf in TIMEFRAMES:
            frames[w.key][tf] = {}
            step = pd.Timedelta(tf)
            for sym in w.universe():
                try:
                    raw = client.klines_range(sym, interval=tf, start=w.start, end=w.end)
                    gaps = int((raw["timestamp"].diff().dropna() != step).sum())
                    lv = build_levels(raw)
                    frames[w.key][tf][sym] = lv
                    integrity.append(dict(window=w.key, tf=tf, symbol=sym,
                                          bars=len(raw), gaps=gaps,
                                          start=str(raw["timestamp"].min().date()),
                                          end=str(raw["timestamp"].max().date())))
                    print(f"  {w.key:7} {tf:4} {sym:9} {len(raw):>7} bars  gaps={gaps}")
                except Exception as e:  # noqa: BLE001 — report, never fabricate
                    print(f"  ! {w.key} {tf} {sym}: {type(e).__name__}: {e}")
                    integrity.append(dict(window=w.key, tf=tf, symbol=sym,
                                          bars=0, gaps=-1, start="", end="",
                                          error=f"{type(e).__name__}: {e}"))
    return frames, integrity


# ---- the four slices ----------------------------------------------------------

def fold_frac_pos(trade_lists: list[list[float]]) -> float:
    """Robustness: fraction of (symbol) cells with positive net expectancy."""
    cells = [np.mean(t) for t in trade_lists if len(t) >= 10]
    return float(np.mean([c > 0 for c in cells])) if cells else float("nan")


def run() -> dict:
    client = BinanceClient()
    print("Fetching + building features (cached on disk after first run)...")
    frames, integrity = load_frames(client)

    report: dict = {"integrity": integrity, "config": {
        "min_pct": MIN_PCT, "trend_filter": TREND_FILTER, **LIVE_BRACKET,
        "fees": FEES, "net_headline": NET_HEADLINE,
    }}

    # Precompute base live signals once per (window, tf, symbol).
    base_sig: dict = {}
    for w in WINDOWS:
        for tf in TIMEFRAMES:
            for sym, df in frames[w.key][tf].items():
                base_sig[(w.key, tf, sym)] = confluence_position(
                    df, min_pct=MIN_PCT, trend_align=TREND_FILTER)

    def collect(window_keys, tfs, fee, gate=None, band=None) -> tuple[list[float], list[list[float]]]:
        """Pool net-R trades over the given windows/tfs at one fee.

        gate:  cumulative min_pct (e.g. 0.6) — rebuild the signal at that floor.
        band:  (lo, hi) — isolate a single confluence band off the live signal.
        Returns (pooled_trades, per_symbol_trade_lists)."""
        pooled: list[float] = []
        per_cell: list[list[float]] = []
        for wk in window_keys:
            for tf in tfs:
                for sym, df in frames[wk][tf].items():
                    if gate is not None:
                        sig = confluence_position(df, min_pct=gate, trend_align=TREND_FILTER)
                    else:
                        sig = base_sig[(wk, tf, sym)]
                    if band is not None:
                        sig = band_signal(df, sig, band[0], band[1])
                    t = trades_for(df, sig, fee)
                    pooled.extend(t)
                    if t:
                        per_cell.append(t)
        return pooled, per_cell

    all_wk = [w.key for w in WINDOWS]

    # ---- SLICE 1: OVERALL (all windows, all TFs, live gate) ----
    overall = {}
    for fee_name, fee in FEES.items():
        pooled, cells = collect(all_wk, TIMEFRAMES, fee)
        s = stats(pooled)
        s["frac_pos_cells"] = fold_frac_pos(cells)
        s["boot_p"] = boot_p(pooled) if fee_name == NET_HEADLINE else None
        overall[fee_name] = s
    report["overall"] = overall

    # ---- SLICE 2: BY REGIME (per window) at gross + headline net ----
    by_regime = {}
    for w in WINDOWS:
        row = {}
        for fee_name in ("gross", NET_HEADLINE, "taker"):
            pooled, cells = collect([w.key], TIMEFRAMES, FEES[fee_name])
            s = stats(pooled)
            s["frac_pos_cells"] = fold_frac_pos(cells)
            if fee_name == NET_HEADLINE:
                s["boot_p"] = boot_p(pooled)
            row[fee_name] = s
        by_regime[w.key] = {"label": w.label, "regime": w.regime, **row}
    report["by_regime"] = by_regime

    # ---- SLICE 3: BY CONFLUENCE BAND, per regime, net headline ----
    bands = [("50", 0.5, 0.6), ("60", 0.6, 0.7), ("70", 0.7, 0.8), ("80+", 0.8, 1.01)]
    by_band = {}
    scopes = [("ALL", all_wk)] + [(w.key, [w.key]) for w in WINDOWS]
    for scope_name, wks in scopes:
        by_band[scope_name] = {}
        for bname, lo, hi in bands:
            pooled, _ = collect(wks, TIMEFRAMES, FEES[NET_HEADLINE], band=(lo, hi))
            by_band[scope_name][bname] = stats(pooled)
    report["by_band"] = by_band

    # ---- SLICE 3b: CUMULATIVE GATE (live 0.5 vs proposed 0.6 vs 0.7), per regime ----
    by_gate = {}
    for scope_name, wks in scopes:
        by_gate[scope_name] = {}
        for g in (0.5, 0.6, 0.7):
            row = {}
            for fee_name in (NET_HEADLINE, "taker"):
                pooled, _ = collect(wks, TIMEFRAMES, FEES[fee_name], gate=g)
                row[fee_name] = stats(pooled)
            by_gate[scope_name][f"{g:.1f}"] = row
    report["by_gate"] = by_gate

    # ---- SLICE 4: BY TIMEFRAME (all windows), gross + net costs ----
    by_tf = {}
    for tf in TIMEFRAMES:
        row = {}
        for fee_name, fee in FEES.items():
            pooled, cells = collect(all_wk, [tf], fee)
            s = stats(pooled)
            s["frac_pos_cells"] = fold_frac_pos(cells)
            if fee_name == NET_HEADLINE:
                s["boot_p"] = boot_p(pooled)
            row[fee_name] = s
        by_tf[tf] = row
    report["by_tf"] = by_tf

    return report


# ---- reporting ----------------------------------------------------------------

def _fmt(s: dict) -> str:
    if not s or s.get("n", 0) == 0:
        return f"{'—':>6} (n=0)"
    pf = "inf" if math.isinf(s["pf"]) else f"{s['pf']:.2f}"
    return (f"n={s['n']:>5}  win={s['win']*100:4.1f}%  exp={s['exp']:+.3f}R  "
            f"tot={s['total']:+7.1f}R  pf={pf:>4}  maxDD={s['maxdd']:+6.1f}R")


def write_markdown(report: dict, path: Path) -> None:
    L: list[str] = []
    cfg = report["config"]
    L.append("# Cycle-aware backtest of the confluence-R strategy\n")
    L.append("_Offline validation only — no live-trading change. Generated by "
             "`scripts/cycle_backtest.py`._\n")
    L.append("## Config (the EXACT live rules, audited; not refit)\n")
    L.append(f"- signal: `confluence_position(min_pct={cfg['min_pct']}, "
             f"trend_align={cfg['trend_filter']})` — ≥50% of ~10 factors + 800-EMA trend\n")
    L.append(f"- bracket: `stop_atr={cfg['stop_atr']}` (=1R), `target_r={cfg['target_r']}`, "
             f"`limit_retrace_atr={cfg['limit_retrace_atr']}` (maker), "
             f"`max_bars={cfg['max_bars']}`, `entry_window={cfg['entry_window']}`\n")
    L.append(f"- fees (round-trip, fraction of price): {cfg['fees']}; "
             f"NET headline = **{cfg['net_headline']}**\n")
    L.append("- out-of-sample: parameters frozen at validated defaults, never refit "
             "to any window; the 2018/2022 analogs and the recent span are all unseen regimes.\n")

    # data integrity
    L.append("\n## Data integrity\n")
    tot_bars = sum(r["bars"] for r in report["integrity"])
    bad = [r for r in report["integrity"] if r.get("gaps", 0) and r["gaps"] > 0]
    errs = [r for r in report["integrity"] if r.get("error")]
    L.append(f"- {len(report['integrity'])} (window×tf×symbol) cells, "
             f"{tot_bars:,} total bars fetched.\n")
    L.append(f"- bars with non-contiguous steps (gaps): "
             f"{'none' if not bad else f'{len(bad)} cells — '+', '.join(b['symbol']+'/'+b['tf']+'/'+b['window'] for b in bad)}\n")
    if errs:
        L.append(f"- fetch errors: {', '.join(e['symbol']+'/'+e['tf']+'/'+e['window'] for e in errs)}\n")
    L.append("- 2018 window universe is limited to coins listed by then "
             "(BTC/ETH/BNB/ADA/XRP); SOL/AVAX/DOT/LINK/DOGE did not exist.\n")

    # Slice 1
    L.append("\n## 1. Overall (full sample, live gate, all TFs/windows)\n")
    L.append("| cost | n | win% | exp R | total R | PF | maxDD R | frac+ cells |")
    L.append("|---|---|---|---|---|---|---|---|")
    for fee_name in ("gross", "maker", "mixed", "taker"):
        s = report["overall"][fee_name]
        pf = "inf" if math.isinf(s["pf"]) else f"{s['pf']:.2f}"
        L.append(f"| {fee_name} | {s['n']} | {s['win']*100:.1f}% | {s['exp']:+.3f} | "
                 f"{s['total']:+.1f} | {pf} | {s['maxdd']:+.1f} | {s['frac_pos_cells']*100:.0f}% |")
    bp = report["overall"][NET_HEADLINE].get("boot_p")
    L.append(f"\nBootstrap P(net≤0) at headline ({NET_HEADLINE}) cost: "
             f"**{bp:.3f}**" + (" (significant)" if bp is not None and bp < 0.05 else "") + "\n")

    # Slice 2
    L.append("\n## 2. By regime — does the edge survive the choppy cycle-analog?\n")
    L.append("| window | regime | gross exp | net exp | net total | net PF | net maxDD | boot p | taker exp |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in report["by_regime"].values():
        g, nh, tk = r["gross"], r[NET_HEADLINE], r["taker"]
        pf = "inf" if math.isinf(nh["pf"]) else f"{nh['pf']:.2f}"
        L.append(f"| {r['label']} | {r['regime']} | {g['exp']:+.3f} | {nh['exp']:+.3f} "
                 f"(n={nh['n']}) | {nh['total']:+.1f} | {pf} | {nh['maxdd']:+.1f} | "
                 f"{nh.get('boot_p', float('nan')):.3f} | {tk['exp']:+.3f} |")

    # Slice 3 band
    L.append("\n## 3. By confluence band (net headline cost) — does the 60% band leak?\n")
    L.append("Each band is ISOLATED (only bars whose confluence_pct is in that band). "
             "50=[50,60), 60=[60,70), 70=[70,80), 80+=[80,100].\n")
    L.append("| scope | 50 band | 60 band | 70 band | 80+ band |")
    L.append("|---|---|---|---|---|")
    def _bandcell(s):
        return "n=0" if s["n"] == 0 else f"{s['exp']:+.3f} (n={s['n']})"
    for scope, bands_d in report["by_band"].items():
        L.append(f"| {scope} | {_bandcell(bands_d['50'])} | {_bandcell(bands_d['60'])} "
                 f"| {_bandcell(bands_d['70'])} | {_bandcell(bands_d['80+'])} |")

    # Slice 3b gate
    L.append("\n## 3b. Cumulative gate — live 0.5 vs proposed 0.6 vs 0.7 (does raising the floor help in EVERY regime?)\n")
    L.append("| scope | gate | net exp | net total | net n | taker exp |")
    L.append("|---|---|---|---|---|---|")
    for scope, gates_d in report["by_gate"].items():
        for g, row in gates_d.items():
            nh, tk = row[NET_HEADLINE], row["taker"]
            L.append(f"| {scope} | {g} | {nh['exp']:+.3f} | {nh['total']:+.1f} | "
                     f"{nh['n']} | {tk['exp']:+.3f} |")

    # Slice 4 tf
    L.append("\n## 4. By timeframe — which TF carries net-of-fees edge at size?\n")
    L.append("| TF | gross exp | net(maker) exp | net(taker) exp | net total | net n | boot p | frac+ |")
    L.append("|---|---|---|---|---|---|---|---|")
    for tf, row in report["by_tf"].items():
        g, mk, tk = row["gross"], row["maker"], row["taker"]
        L.append(f"| {tf} | {g['exp']:+.3f} | {mk['exp']:+.3f} | {tk['exp']:+.3f} | "
                 f"{mk['total']:+.1f} | {mk['n']} | {mk.get('boot_p', float('nan')):.3f} | "
                 f"{mk['frac_pos_cells']*100:.0f}% |")

    path.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    report = run()
    out = Path("docs/research/cycle_backtest.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(report, out)
    Path("data/cycle_backtest_results.json").write_text(json.dumps(report, indent=2, default=str))
    print("\n=== OVERALL (net headline) ===")
    print(" ", _fmt(report["overall"][NET_HEADLINE]))
    print(f"\nReport -> {out}")
