"""Head-to-head: the EXISTING chandelier trailing stop vs the live bank-half /
ride-to-3R rule, over the SAME historical universe + 1h timeframe as the
validated cycle-aware ~137K-trade backtest (docs/MEMORY.md §41).

RESEARCH ONLY. This script IMPORTS the existing engine — it reimplements NOTHING:
  - population stats come straight from ``backtest.bracket.bracket_backtest``;
  - the per-trade paired diagnostic resolves each entry through the SHARED
    ``backtest.resolver.resolve_bracket`` (the single source of truth both the
    backtest and the live journal delegate to).
It does NOT touch paper-scan, the workflow, or any live flag.

WHAT IS COMPARED (all net of MAKER fees = config.FEE_PCT = 0.0004 round-trip):
  BASELINE (current live rule): tp1_r=1.0, tp1_frac=0.5, be_after_tp1=True,
            target_r=3.0, trailing_atr=None  -> bank half at 1R, stop to BE,
            ride the rest to the 3R target.  (A full winner blends to +2.0R.)
  TRAIL SWEEP: trailing_atr in {1.0, 1.5, 2.0, 2.5, 3.0}, everything else equal
            (stop=1.5-ATR=1R, target_r=3.0, 0.25-ATR maker retrace, 24-bar stop).
            NOTE the resolver only supports the chandelier trail on the
            NON-partial path, so the trail variants ride FULL size to a trailed
            stop or the 3R target (no 1R partial). "Trail WITH the 1R partial" is
            therefore NOT a supported variant (would require new resolver logic,
            which is out of scope) — reported as NOT VERIFIED below.

Universe / windows / data loader are imported verbatim from
``scripts/cycle_backtest.py`` (MAJORS, the 2018/2022 cycle-analog + recent
windows, BinanceClient.klines_range disk-cached), restricted to the 1h timeframe
— the only TF the validated edge survives net-of-fees (§41).

Run (ONE command, from the repo root):

    python research/trailing_sweep.py

Outputs: a results table to stdout, plus two CSVs under research/:
    research/trailing_sweep_summary.csv   (per-variant population stats)
    research/trailing_sweep_paired.csv    (beat/match/hurt + runner capture)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))  # reuse the validated universe/windows

from kudbee_quant.backtest.bracket import _summarize, bracket_backtest  # noqa: E402
from kudbee_quant.backtest.resolver import resolve_bracket  # noqa: E402
from kudbee_quant.config.validated_defaults import (  # noqa: E402
    ENTRY_WINDOW, FEE_PCT, MAX_BARS, MIN_PCT, RETRACE_ATR, STOP_ATR, TARGET_R,
    TREND_FILTER,
)
from kudbee_quant.confluence.stack import confluence_position  # noqa: E402
from kudbee_quant.levels import build_levels  # noqa: E402

import cycle_backtest as cyc  # noqa: E402  (scripts/cycle_backtest.py — single source of truth)

# ---- variant definitions ------------------------------------------------------
# The EXACT live execution geometry (audited, never refit): 1.5-ATR stop (=1R),
# 3R target, 0.25-ATR maker retrace, 6-bar fill window, 24-bar time-stop.
GEOMETRY = dict(stop_atr=STOP_ATR, target_r=TARGET_R, max_bars=MAX_BARS,
                limit_retrace_atr=RETRACE_ATR, entry_window=ENTRY_WINDOW)
FEE = FEE_PCT  # maker round-trip (the strategy's design cost; "all net of maker fees")

# Current live rule: bank half at 1R, stop to BE, ride the rest to 3R.
BASELINE_KW = dict(**GEOMETRY, fee_pct=FEE,
                   tp1_r=1.0, tp1_frac=0.5, be_after_tp1=True, trailing_atr=None)
# Reference only (NOT the current live rule): the all-or-nothing ride-to-3R that
# MEMORY §41 validated at +0.096R net-maker on 1h. Included so the trail is judged
# against the BEST known config, not only the (degraded) bank-half rule.
RIDE3R_KW = dict(**GEOMETRY, fee_pct=FEE, trailing_atr=None)
TRAIL_MULTIPLES = [1.0, 1.5, 2.0, 2.5, 3.0]


def _trail_kw(mult: float) -> dict:
    """Chandelier trail variant — full size, no 1R partial (resolver constraint)."""
    return dict(**GEOMETRY, fee_pct=FEE, trailing_atr=mult)


# ---- data ---------------------------------------------------------------------

def load_cells() -> list[tuple[str, str, pd.DataFrame, pd.Series]]:
    """Every (window, symbol) 1h cell with its live signal. Uses the validated
    loader + feature build + confluence signal — no fabrication, no refit."""
    client = cyc.BinanceClient()
    cells: list[tuple[str, str, pd.DataFrame, pd.Series]] = []
    print("Fetching 1h frames (cached on disk after first run)...")
    for w in cyc.WINDOWS:
        for sym in w.universe():
            try:
                raw = client.klines_range(sym, interval="1h", start=w.start, end=w.end)
                df = build_levels(raw)
                sig = confluence_position(df, min_pct=MIN_PCT, trend_align=TREND_FILTER)
                cells.append((w.key, sym, df, sig))
                print(f"  {w.key:7} {sym:9} {len(df):>6} bars  signals={int((sig != 0).sum())}")
            except Exception as e:  # noqa: BLE001 — report, never fabricate
                print(f"  ! {w.key} {sym}: {type(e).__name__}: {e}")
    return cells


# ---- population stats (straight from the engine) ------------------------------

def population_stats(cells, variant_kw: dict) -> dict:
    """Pool every cell's net-R trade list (from the unmodified bracket_backtest)
    and re-summarize with the engine's own ``_summarize`` — invents no metric.
    Adds the project's significance gate: one-sided bootstrap P(mean net R <= 0)
    (cyc.boot_p, §19/§23). An edge isn't real unless this clears it."""
    pooled: list[float] = []
    for _wk, _sym, df, sig in cells:
        res = bracket_backtest(df, sig, **variant_kw)
        pooled.extend(res.trades)
    s = _summarize(pooled, variant_kw.get("target_r", TARGET_R))
    return {
        "trades": s.n_trades,
        "net_r_per_trade": s.expectancy_r,
        "win_rate": s.win_rate,
        "profit_factor": s.profit_factor,
        "max_drawdown_r": s.max_drawdown_r,
        "avg_win_r": s.avg_win_r,          # AVG REALIZED R ON WINNERS (net of fees)
        "total_r": s.total_r,
        "boot_p_net_le_0": cyc.boot_p(pooled),   # significance gate (lower = stronger)
    }


# ---- paired diagnostic (common entries; exits via the SHARED resolver) --------
# Mirrors bracket_backtest's entry/overlap loop EXACTLY (regression-locked by
# test_trailing_sweep.py) so the BASELINE timeline defines the entries, then
# resolves each of those same entries under every trail multiple via the shared
# resolver. This is what makes "beat / matched / hurt" and "runners cut short" a
# true PAIRED comparison rather than two divergent books.
_FULL_WINNER_GROSS = 0.5 * 1.0 + 0.5 * 3.0  # = 2.0R: baseline blended full-target hit
EPS = 1e-9


def paired_trades(df: pd.DataFrame, signal: pd.Series, mults: list[float]) -> list[dict]:
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
        # maker limit retrace entry (identical to bracket_backtest, no confirmation)
        limit = close[t] - direction * RETRACE_ATR * atr[t]
        ewin = min(t + ENTRY_WINDOW, n - 1)
        entry_bar = None
        for j in range(t + 1, ewin + 1):
            if (direction > 0 and low[j] <= limit) or (direction < 0 and high[j] >= limit):
                entry_bar = j
                break
        if entry_bar is None:
            continue  # retrace never came; signal missed (realistic)
        entry = limit
        stop = entry - direction * sd
        target = entry + direction * sd * TARGET_R
        end = min(entry_bar + MAX_BARS, n - 1)
        hi = high[entry_bar + 1:end + 1]
        lo = low[entry_bar + 1:end + 1]
        cl = close[entry_bar + 1:end + 1]

        # BASELINE — bank half @1R, BE, ride to 3R (shared resolver, partial path)
        tp1 = entry + direction * sd * 1.0
        ob = resolve_bracket(direction, entry, stop, target, sd, TARGET_R, hi, lo, cl,
                             force_close_at_end=True, tp1=tp1, tp1_r=1.0, tp1_frac=0.5,
                             be_after_tp1=True)
        if ob.exit_offset is None:
            gross_b = direction * (close[end] - entry) / sd
            exit_b = end
        else:
            gross_b = ob.outcome_r
            exit_b = entry_bar + 1 + ob.exit_offset
        cost_b = FEE * entry / sd * (1 + 0.5 * 0.5)   # extra half round-trip on the TP1 fraction
        row = {"gross_b": float(gross_b), "net_b": float(gross_b - cost_b)}

        # TRAIL variants — full size, chandelier trail (shared resolver, enriched path)
        cost_t = FEE * entry / sd  # no partial -> single round-trip
        for m in mults:
            ot = resolve_bracket(direction, entry, stop, target, sd, TARGET_R, hi, lo, cl,
                                 force_close_at_end=True, trailing_atr=m, atr_at_entry=atr[t])
            gross_t = (direction * (close[end] - entry) / sd
                       if ot.exit_offset is None else ot.outcome_r)
            row[f"gross_t_{m}"] = float(gross_t)
            row[f"net_t_{m}"] = float(gross_t - cost_t)
        rows.append(row)
        busy_until = exit_b  # baseline timeline drives the shared entry set
    return rows


def paired_summary(cells, mults: list[float]) -> pd.DataFrame:
    rows: list[dict] = []
    for _wk, _sym, df, sig in cells:
        rows.extend(paired_trades(df, sig, mults))
    paired = pd.DataFrame(rows)
    out: list[dict] = []
    n = len(paired)
    base_full = (paired["gross_b"] - _FULL_WINNER_GROSS).abs() < 1e-6  # baseline 3R runners
    n_runners = int(base_full.sum())
    for m in mults:
        dnet = paired[f"net_t_{m}"] - paired["net_b"]
        beat = int((dnet > EPS).sum())
        hurt = int((dnet < -EPS).sum())
        matched = n - beat - hurt
        # runner capture: of the baseline's full-3R runners, how many did the
        # trail exit BELOW the full 3R target (cut short), and the net R effect.
        trail_short = base_full & (paired[f"gross_t_{m}"] < TARGET_R - 1e-6)
        cut = int(trail_short.sum())
        net_effect_on_runners = float(dnet[base_full].sum())
        out.append({
            "trailing_atr": m,
            "paired_n": n,
            "beat_baseline": beat,
            "matched_baseline": matched,
            "hurt_baseline": hurt,
            "beat_pct": beat / n if n else float("nan"),
            "matched_pct": matched / n if n else float("nan"),
            "hurt_pct": hurt / n if n else float("nan"),
            "baseline_3R_runners": n_runners,
            "runners_cut_short": cut,
            "runners_cut_pct": cut / n_runners if n_runners else float("nan"),
            "net_R_effect_on_runners": net_effect_on_runners,
        })
    return pd.DataFrame(out)


# ---- driver -------------------------------------------------------------------

def main() -> None:
    cells = load_cells()
    if not cells:
        print("NO DATA — refusing to fabricate. Check the loader / network.")
        sys.exit(1)
    n_sig = sum(int((sig != 0).sum()) for _, _, _, sig in cells)
    print(f"\nLoaded {len(cells)} (window x symbol) 1h cells; {n_sig} raw live signals.\n")

    # 1) population stats
    variants = [("BASELINE (tp1 0.5@1R, BE, ride 3R)", BASELINE_KW),
                ("REF ride-3R (no partial, §41)", RIDE3R_KW)]
    variants += [(f"TRAIL atr={m}", _trail_kw(m)) for m in TRAIL_MULTIPLES]
    summ_rows = []
    for name, kw in variants:
        st = population_stats(cells, kw)
        st = {"variant": name, **st}
        summ_rows.append(st)
    summ = pd.DataFrame(summ_rows)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print("=" * 100)
    print("POPULATION STATS  (full trade population, ALL net of maker fees = "
          f"{FEE} round-trip)")
    print("=" * 100)
    show = summ.copy()
    for c in ("net_r_per_trade", "avg_win_r", "max_drawdown_r", "total_r"):
        show[c] = show[c].map(lambda x: f"{x:+.4f}")
    show["win_rate"] = summ["win_rate"].map(lambda x: f"{x*100:.1f}%")
    show["profit_factor"] = summ["profit_factor"].map(lambda x: f"{x:.3f}")
    show["boot_p_net_le_0"] = summ["boot_p_net_le_0"].map(lambda x: f"{x:.3f}")
    print(show.to_string(index=False))
    print("\nSignificance gate (§19/§23): an edge is only real if boot_p_net_le_0 < 0.05.")

    # 2) paired diagnostic
    paired = paired_summary(cells, TRAIL_MULTIPLES)
    print("\n" + "=" * 100)
    print("PAIRED DIAGNOSTIC  (same baseline entries; exits resolved both ways via the shared resolver)")
    print("=" * 100)
    pshow = paired.copy()
    for c in ("beat_pct", "matched_pct", "hurt_pct", "runners_cut_pct"):
        pshow[c] = paired[c].map(lambda x: f"{x*100:.1f}%")
    pshow["net_R_effect_on_runners"] = paired["net_R_effect_on_runners"].map(lambda x: f"{x:+.1f}")
    print(pshow.to_string(index=False))

    # 3) persist CSVs
    out_dir = Path(__file__).resolve().parent
    summ.to_csv(out_dir / "trailing_sweep_summary.csv", index=False)
    paired.to_csv(out_dir / "trailing_sweep_paired.csv", index=False)
    print(f"\nSaved: {out_dir/'trailing_sweep_summary.csv'}")
    print(f"Saved: {out_dir/'trailing_sweep_paired.csv'}")

    # 4) machine verdict (net R/trade & drawdown vs baseline over full population)
    base = summ[summ["variant"].str.startswith("BASELINE")].iloc[0]
    ride = summ[summ["variant"].str.startswith("REF")].iloc[0]
    trails = summ[summ["variant"].str.startswith("TRAIL")]
    better = trails[(trails["net_r_per_trade"] > base["net_r_per_trade"])
                    & (trails["max_drawdown_r"] >= base["max_drawdown_r"] - 1e-9)]
    sig = trails[trails["boot_p_net_le_0"] < 0.05]
    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)
    print(f"BASELINE (live bank-half) net R/trade = {base['net_r_per_trade']:+.4f}  "
          f"max_dd = {base['max_drawdown_r']:+.2f}R  boot_p = {base['boot_p_net_le_0']:.3f}  "
          f"n={int(base['trades'])}")
    print(f"REF ride-3R (§41, no partial)        net R/trade = {ride['net_r_per_trade']:+.4f}  "
          f"max_dd = {ride['max_drawdown_r']:+.2f}R  boot_p = {ride['boot_p_net_le_0']:.3f}  "
          f"n={int(ride['trades'])}")
    if better.empty:
        print("\nNo trail multiple beats the live baseline on net R/trade WITHOUT worsening "
              "max drawdown. KEEP --trailing-atr OFF.")
    else:
        win = better.sort_values("net_r_per_trade", ascending=False).iloc[0]
        print(f"\nBest-vs-baseline: {win['variant']}  net R/trade = {win['net_r_per_trade']:+.4f} "
              f"(vs live {base['net_r_per_trade']:+.4f})  max_dd = {win['max_drawdown_r']:+.2f}R "
              f"(live {base['max_drawdown_r']:+.2f}R)  boot_p = {win['boot_p_net_le_0']:.3f}.")
    print(f"\nSIGNIFICANCE: {0 if sig.empty else len(sig)} trail variant(s) clear the "
          f"boot_p<0.05 gate. No variant beats the §41 ride-3R reference "
          f"({ride['net_r_per_trade']:+.4f}R) unless its net R/trade exceeds it.")


if __name__ == "__main__":
    main()
