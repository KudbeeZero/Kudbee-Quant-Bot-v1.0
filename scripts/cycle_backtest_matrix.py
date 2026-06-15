"""Supplement to scripts/cycle_backtest.py: the REGIME x TIMEFRAME matrix.

The main report's by-regime slice pools all timeframes, so it is dominated by the
high-trade-count 5m book (net-dead on cost). The task's central question — does
the edge survive the CHOPPY cycle-analog regime, or only trending spans? — must be
asked on the timeframe that actually carries net-of-fees edge (1h). This computes
net expectancy per (regime window x timeframe) at maker AND taker cost, plus the
1h-only confluence-band and cumulative-gate breakdowns. All data is already cached
by the main run, so this is fast and uses the identical live engine.
"""
from __future__ import annotations

import json
from pathlib import Path


from kudbee_quant.confluence.stack import confluence_position
from kudbee_quant.ingest.binance import BinanceClient

from cycle_backtest import (  # same dir on sys.path; reuse the audited config + helpers
    FEES, MIN_PCT, TIMEFRAMES, TREND_FILTER, WINDOWS,
    band_signal, boot_p, stats, trades_for,
)


def load() -> dict:
    client = BinanceClient()
    from kudbee_quant.levels import build_levels
    frames: dict = {}
    for w in WINDOWS:
        frames[w.key] = {}
        for tf in TIMEFRAMES:
            frames[w.key][tf] = {}
            for sym in w.universe():
                raw = client.klines_range(sym, interval=tf, start=w.start, end=w.end)
                frames[w.key][tf][sym] = build_levels(raw)
    return frames


def pool(frames, wks, tfs, fee, gate=None, band=None):
    out = []
    for wk in wks:
        for tf in tfs:
            for df in frames[wk][tf].values():
                sig = (confluence_position(df, min_pct=gate, trend_align=TREND_FILTER)
                       if gate is not None
                       else confluence_position(df, min_pct=MIN_PCT, trend_align=TREND_FILTER))
                if band is not None:
                    sig = band_signal(df, sig, band[0], band[1])
                out.extend(trades_for(df, sig, fee))
    return out


def main():
    print("loading cached frames...")
    frames = load()
    report = {}

    # 1) regime x timeframe matrix (maker + taker).
    matrix = {}
    for w in WINDOWS:
        matrix[w.key] = {"label": w.label, "regime": w.regime, "tf": {}}
        for tf in TIMEFRAMES:
            mk = stats(pool(frames, [w.key], [tf], FEES["maker"]))
            tk = stats(pool(frames, [w.key], [tf], FEES["taker"]))
            mk["boot_p"] = boot_p(pool(frames, [w.key], [tf], FEES["maker"]))
            matrix[w.key]["tf"][tf] = {"maker": mk, "taker": tk}
            print(f"  {w.key:7} {tf:4} maker={mk['exp']:+.3f} (n={mk['n']}, p={mk['boot_p']:.3f}) "
                  f"taker={tk['exp']:+.3f}")
    report["regime_tf"] = matrix

    # 2) 1h-only: bands per regime + ALL.
    bands = [("50", 0.5, 0.6), ("60", 0.6, 0.7), ("70", 0.7, 0.8), ("80+", 0.8, 1.01)]
    all_wk = [w.key for w in WINDOWS]
    band1h = {}
    for scope, wks in [("ALL", all_wk)] + [(w.key, [w.key]) for w in WINDOWS]:
        band1h[scope] = {b: stats(pool(frames, wks, ["1h"], FEES["maker"], band=(lo, hi)))
                         for b, lo, hi in bands}
    report["band_1h"] = band1h

    # 3) 1h-only: cumulative gate per regime (maker + taker).
    gate1h = {}
    for scope, wks in [("ALL", all_wk)] + [(w.key, [w.key]) for w in WINDOWS]:
        gate1h[scope] = {}
        for g in (0.5, 0.6, 0.7):
            gate1h[scope][f"{g:.1f}"] = {
                "maker": stats(pool(frames, wks, ["1h"], FEES["maker"], gate=g)),
                "taker": stats(pool(frames, wks, ["1h"], FEES["taker"], gate=g)),
            }
    report["gate_1h"] = gate1h

    Path("data/cycle_backtest_matrix.json").write_text(json.dumps(report, indent=2, default=str))

    # ---- append markdown to the main report ----
    L = ["\n\n## 5. Regime × timeframe matrix (the honest cycle verdict)\n",
         "The by-regime table (§2) pools all TFs and is dominated by the net-dead 5m "
         "book. Here is net expectancy per (window × TF), maker / taker cost.\n",
         "| window | regime | 5m maker | 15m maker | 1h maker | 1h taker | 1h n | 1h boot p |",
         "|---|---|---|---|---|---|---|---|"]
    for w in WINDOWS:
        tfd = matrix[w.key]["tf"]
        h = tfd["1h"]["maker"]
        L.append(f"| {w.label} | {w.regime} | {tfd['5m']['maker']['exp']:+.3f} | "
                 f"{tfd['15m']['maker']['exp']:+.3f} | {h['exp']:+.3f} | "
                 f"{tfd['1h']['taker']['exp']:+.3f} | {h['n']} | {h['boot_p']:.3f} |")

    L += ["\n### 5b. 1h-only confluence bands (does the 60% band leak on the edge-carrying TF?)\n",
          "| scope | 50 | 60 | 70 | 80+ |", "|---|---|---|---|---|"]
    for scope, bd in band1h.items():
        def c(s):
            return "n=0" if s["n"] == 0 else f"{s['exp']:+.3f} (n={s['n']})"
        L.append(f"| {scope} | {c(bd['50'])} | {c(bd['60'])} | {c(bd['70'])} | {c(bd['80+'])} |")

    L += ["\n### 5c. 1h-only cumulative gate (live 0.5 vs 0.6 vs 0.7), per regime\n",
          "| scope | gate | net maker | net n | net taker |", "|---|---|---|---|---|"]
    for scope, gd in gate1h.items():
        for g, row in gd.items():
            mk, tk = row["maker"], row["taker"]
            L.append(f"| {scope} | {g} | {mk['exp']:+.3f} | {mk['n']} | {tk['exp']:+.3f} |")

    p = Path("docs/research/cycle_backtest.md")
    p.write_text(p.read_text() + "\n".join(L) + "\n")
    print(f"\nappended matrix to {p}")


if __name__ == "__main__":
    main()
