"""Head-to-head EXECUTION backtest — maker-retrace vs market-at-signal vs hybrid.

OFFLINE research (TASK 2026-06-15). Does NOT touch the live trading path. Answers:
of the three ways to ENTER a confluence signal, which has the best NET-OF-FEES
out-of-sample expectancy per timeframe (5m / 15m / 1h), and does it survive the
chop regimes?

Method
------
* Universe: the walk-forward-validated majors (MEMORY §1). Symbols that did not
  exist on Binance in an early window simply return no data and are skipped (logged).
* Signal: the REAL production signal — ``confluence_position(min_pct=0.50,
  trend_align=True)`` (the 800-EMA HTF filter the live paper scan applies).
* Data: 5m klines from the public Binance data mirror, fetched once per symbol x
  window (plus a 50-day warmup prefix so the 800-EMA is converged), then RESAMPLED
  up to 15m and 1h so all three timeframes share identical source bars and windows.
  Signals before the window start are excluded (warmup only).
* Variants (see backtest/execution_modes.py): A maker_retrace (current live),
  B market (next-bar-open, taker), C hybrid (1-bar limit then market chase).
* Geometry held constant: stop = 1.5*ATR (=1R), target = 3R, max_bars = 24,
  retrace = 0.25*ATR, entry_window = 6 — the validated defaults.
* Fees: per-leg, measured (MEMORY §25). taker 0.00045/side, maker 0.0002/side.
  Stops/time-stops pay taker (market out); targets pay maker (resting limit).
* STEP 3: every signal the maker retrace CANCELLED, resolved as a market entry —
  were the missed trades net winners or losers (the adverse-selection test)?

Output: full results -> data/execution_backtest_results.json, plus a printed verdict.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
from pathlib import Path

import pandas as pd
import requests

from kudbee_quant.backtest.execution_modes import (
    adverse_selection, run_variant, summarize,
)
from kudbee_quant.confluence.stack import confluence_position
from kudbee_quant.ingest.resample import resample_ohlcv
from kudbee_quant.levels import build_levels

# ---- configuration -----------------------------------------------------------
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]

# OOS regimes (UTC). 2018/2022 are documented chop/bear windows; "recent" is the
# trailing 5 months. Defined here (MEMORY had no canonical dates) and reported.
WINDOWS = {
    "2018_chop": (dt.datetime(2018, 5, 1, tzinfo=dt.timezone.utc),
                  dt.datetime(2018, 10, 1, tzinfo=dt.timezone.utc)),
    "2022_chop": (dt.datetime(2022, 5, 1, tzinfo=dt.timezone.utc),
                  dt.datetime(2022, 10, 1, tzinfo=dt.timezone.utc)),
    "recent":    (dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
                  dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)),
}
WARMUP_DAYS = 50
TIMEFRAMES = {"5m": None, "15m": "15min", "1h": "1h"}  # rule=None -> native 5m
MIN_PCT = 0.50
VARIANTS = {"A_maker_retrace": "maker_retrace", "B_market": "market", "C_hybrid": "hybrid"}
GEOM = dict(stop_atr=1.5, target_r=3.0, max_bars=24, retrace_atr=0.25, entry_window=6)

BASE = "https://data-api.binance.vision"
_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
         "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]
CACHE = Path("/tmp/exec_bt_cache")
CACHE.mkdir(parents=True, exist_ok=True)
_SESSION = requests.Session()


def fetch_5m(symbol: str, start: dt.datetime, end: dt.datetime) -> pd.DataFrame:
    """Page 5m klines [start, end) forward from the public mirror, with disk cache."""
    key = hashlib.sha256(f"{symbol}:5m:{start.isoformat()}:{end.isoformat()}".encode()).hexdigest()
    path = CACHE / f"{key}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    rows: list[list] = []
    cur = start_ms
    while cur < end_ms:
        params = {"symbol": symbol, "interval": "5m", "startTime": cur,
                  "endTime": end_ms, "limit": 1000}
        r = _SESSION.get(BASE + "/api/v3/klines", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        rows += data
        cur = data[-1][0] + 1
        if len(data) < 1000:
            break
        time.sleep(0.08)
    df = pd.DataFrame(rows, columns=_COLS)
    if df.empty:
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close",
                                   "volume", "quote_volume", "trades",
                                   "taker_buy_base", "taker_buy_quote"])
        df.to_parquet(path, index=False)
        return df
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume", "quote_volume", "trades",
              "taker_buy_base", "taker_buy_quote"]:
        df[c] = df[c].astype(float)
    keep = ["timestamp", "open", "high", "low", "close", "volume", "quote_volume",
            "trades", "taker_buy_base", "taker_buy_quote"]
    df = df[keep].drop_duplicates(subset="timestamp").reset_index(drop=True)
    df.to_parquet(path, index=False)
    return df


def prepare_frame(raw: pd.DataFrame, rule: str | None) -> pd.DataFrame:
    f = raw if rule is None else resample_ohlcv(raw, rule)
    return build_levels(f)


def start_index(df: pd.DataFrame, window_start: dt.datetime) -> int:
    ts = pd.to_datetime(df["timestamp"], utc=True)
    mask = ts >= window_start
    if not mask.any():
        return len(df)
    return int(mask.values.argmax())


def main() -> None:
    # net-R pools: net[variant][tf][window] = list of per-trade net R
    net: dict = {v: {tf: {} for tf in TIMEFRAMES} for v in VARIANTS}
    fills: dict = {v: {tf: {} for tf in TIMEFRAMES} for v in VARIANTS}  # (filled, attempts)
    adv: dict = {tf: {} for tf in TIMEFRAMES}        # adverse-selection net-R lists
    coverage: dict = {w: [] for w in WINDOWS}        # symbols with usable data

    for wname, (wstart, wend) in WINDOWS.items():
        fetch_start = wstart - dt.timedelta(days=WARMUP_DAYS)
        print(f"\n=== window {wname}  {wstart.date()}..{wend.date()} "
              f"(warmup from {fetch_start.date()}) ===", flush=True)
        for sym in SYMBOLS:
            try:
                raw = fetch_5m(sym, fetch_start, wend)
            except Exception as e:  # network / endpoint hiccup — log and continue
                print(f"  ! {sym}: fetch failed {type(e).__name__}: {e}", flush=True)
                continue
            # Need enough 5m history that the resampled 1h 800-EMA is converged.
            if len(raw) < 20_000:
                print(f"  - {sym}: only {len(raw)} 5m bars (not listed / thin) — skip", flush=True)
                continue
            coverage[wname].append(sym)
            for tf, rule in TIMEFRAMES.items():
                df = prepare_frame(raw, rule)
                sidx = start_index(df, wstart)
                if sidx >= len(df) - 2:
                    continue
                sig = confluence_position(df, min_pct=MIN_PCT, trend_align=True)
                for vlabel, mode in VARIANTS.items():
                    out = run_variant(df, sig, mode=mode, start_idx=sidx, **GEOM)
                    nets = [t["net_r"] for t in out["trades"]]
                    net[vlabel][tf].setdefault(wname, []).extend(nets)
                    f, a = sum(x["filled"] for x in out["attempts"]), len(out["attempts"])
                    pf, pa = fills[vlabel][tf].get(wname, (0, 0))
                    fills[vlabel][tf][wname] = (pf + f, pa + a)
                # STEP 3 — cancelled-signal market resolution (adverse selection).
                arecs = adverse_selection(df, sig, start_idx=sidx, **GEOM)
                adv[tf].setdefault(wname, []).extend([r["net_r"] for r in arecs])
            print(f"  + {sym}: {len(raw)} 5m bars -> all timeframes", flush=True)

    # ---- assemble results ----------------------------------------------------
    results: dict = {
        "meta": {
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "task": "execution head-to-head: maker-retrace vs market vs hybrid (OOS, net of fees)",
            "signal": {"fn": "confluence_position", "min_pct": MIN_PCT, "trend_align": True},
            "geometry": GEOM,
            "fees": {"taker_side": 0.00045, "maker_side": 0.0002,
                     "model": "per-leg: stop/time=taker (market out), target=maker (resting limit)"},
            "windows": {k: [v[0].date().isoformat(), v[1].date().isoformat()]
                        for k, v in WINDOWS.items()},
            "symbols_requested": SYMBOLS,
            "coverage": coverage,
            "note": "OFFLINE research only; live trading path unchanged. Maker side fee is an "
                    "unconfirmed assumption (MEMORY §25). 'A_maker_retrace_legacycost' below "
                    "re-costs variant A round-trip-maker (the current backtest's optimistic "
                    "assumption) for reference.",
        },
        "per_timeframe": {},   # pooled across symbols+windows
        "per_window": {},      # tf -> window -> variant metrics
        "adverse_selection": {},
    }

    def metrics_for(vlabel, tf, window=None):
        if window is None:
            pool = [r for w in net[vlabel][tf].values() for r in w]
            f = sum(fills[vlabel][tf].get(w, (0, 0))[0] for w in WINDOWS)
            a = sum(fills[vlabel][tf].get(w, (0, 0))[1] for w in WINDOWS)
        else:
            pool = net[vlabel][tf].get(window, [])
            f, a = fills[vlabel][tf].get(window, (0, 0))
        m = summarize(pool, target_r=GEOM["target_r"])
        m["fill_rate"] = (f / a) if a else float("nan")
        m["n_signals_attempted"] = a
        return m

    for tf in TIMEFRAMES:
        results["per_timeframe"][tf] = {v: metrics_for(v, tf) for v in VARIANTS}
        results["per_window"][tf] = {
            w: {v: metrics_for(v, tf, w) for v in VARIANTS} for w in WINDOWS
        }
        # adverse selection pooled + per window
        results["adverse_selection"][tf] = {
            "pooled": summarize([r for w in adv[tf].values() for r in w],
                                target_r=GEOM["target_r"]),
            "per_window": {w: summarize(adv[tf].get(w, []), target_r=GEOM["target_r"])
                           for w in WINDOWS},
        }

    # Reference: variant A re-costed round-trip MAKER (the current backtest's assumption).
    legacy = {}
    for tf in TIMEFRAMES:
        # Re-run A with taker==maker so stops also cost maker (round-trip maker).
        pool = []
        f_a = a_a = 0
        for wname, (wstart, wend) in WINDOWS.items():
            for sym in coverage[wname]:
                raw = fetch_5m(sym, wstart - dt.timedelta(days=WARMUP_DAYS), wend)
                df = prepare_frame(raw, TIMEFRAMES[tf])
                sidx = start_index(df, wstart)
                if sidx >= len(df) - 2:
                    continue
                sig = confluence_position(df, min_pct=MIN_PCT, trend_align=True)
                out = run_variant(df, sig, mode="maker_retrace", start_idx=sidx,
                                  taker_side=0.0002, maker_side=0.0002, **GEOM)
                pool.extend(t["net_r"] for t in out["trades"])
                f_a += sum(x["filled"] for x in out["attempts"])
                a_a += len(out["attempts"])
        m = summarize(pool, target_r=GEOM["target_r"])
        m["fill_rate"] = (f_a / a_a) if a_a else float("nan")
        legacy[tf] = m
    results["per_timeframe_A_maker_retrace_legacycost"] = legacy

    out_path = Path("data/execution_backtest_results.json")
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {out_path}", flush=True)
    _print_verdict(results)


def _fmt(m: dict) -> str:
    return (f"n={m['n_trades']:<5d} fill={m.get('fill_rate', float('nan')):.0%} "
            f"win={m['win_rate']*100:4.1f}% exp={m['expectancy_r']:+.4f}R "
            f"tot={m['total_r']:+7.1f}R pf={m['profit_factor']:.2f} "
            f"dd={m['max_drawdown_r']:.1f}R p={m['bootstrap_p']:.3f}")


def _print_verdict(results: dict) -> None:
    print("\n" + "=" * 78)
    print("POOLED NET-OF-FEES OOS RESULTS (per timeframe, across all windows)")
    print("=" * 78)
    for tf, byv in results["per_timeframe"].items():
        print(f"\n[{tf}]")
        for v, m in byv.items():
            print(f"  {v:<22s} {_fmt(m)}")
        print(f"  {'A_legacycost(rt-maker)':<22s} "
              f"{_fmt(results['per_timeframe_A_maker_retrace_legacycost'][tf])}")
        adv = results["adverse_selection"][tf]["pooled"]
        print(f"  >> adverse-selection (cancelled signals as MARKET): "
              f"n={adv['n_trades']} win={adv['win_rate']*100 if adv['n_trades'] else float('nan'):.1f}% "
              f"exp={adv['expectancy_r']:+.4f}R tot={adv['total_r']:+.1f}R p={adv['bootstrap_p']:.3f}")
        # winner by expectancy
        best = max(byv.items(), key=lambda kv: (kv[1]["expectancy_r"]
                                                if kv[1]["n_trades"] else -9))
        print(f"  WINNER ({tf}): {best[0]}  exp={best[1]['expectancy_r']:+.4f}R")


if __name__ == "__main__":
    main()
