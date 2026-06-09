"""Timeframe survey — where does the confluence-R edge actually live?

Runs the validated config (>=50% confluence, 3R, 0.25-ATR limit retrace, maker)
across many timeframes (incl. resampled 'strange' ones like 7m/3h) with
REALISTIC, timeframe-aware costs (fee_pct converted to R via each TF's stop), so
we see where the edge holds and where costs/noise kill it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest.bracket import bracket_backtest
from .confluence.stack import confluence_position
from .ingest import BinanceClient
from .ingest.resample import resample_ohlcv
from .levels import build_levels

# label -> (fetch_interval, resample_rule_or_None, fetch_limit)
TF_SPECS = {
    "7m": ("1m", "7min", 14000),
    "15m": ("15m", None, 5000),
    "30m": ("30m", None, 4000),
    "1h": ("1h", None, 4000),
    "2h": ("2h", None, 3000),
    "3h": ("1h", "3h", 4000),
    "4h": ("4h", None, 3000),
}


def timeframe_survey(symbol: str, tfs=None, fee_pct: float = 0.0004,
                     n_folds: int = 6, client: BinanceClient | None = None) -> pd.DataFrame:
    """Walk-forward expectancy of the validated config across timeframes."""
    client = client or BinanceClient()
    tfs = tfs or list(TF_SPECS)
    rows = []
    for tf in tfs:
        fi, rule, fl = TF_SPECS[tf]
        try:
            df = client.klines(symbol, interval=fi, limit=fl)
            if rule:
                df = resample_ohlcv(df, rule)
            f = build_levels(df)
            sig = confluence_position(f, min_pct=0.5)
            n = len(f)
            bounds = np.linspace(0, n, n_folds + 1, dtype=int)
            cells, trades = [], 0
            for i in range(n_folds):
                fd = f.iloc[bounds[i]:bounds[i + 1]].reset_index(drop=True)
                sg = pd.Series(sig).iloc[bounds[i]:bounds[i + 1]].reset_index(drop=True)
                r = bracket_backtest(fd, sg, stop_atr=1, target_r=3, max_bars=36,
                                     fee_pct=fee_pct, limit_retrace_atr=0.25)
                if r.n_trades >= 8:
                    cells.append(r.expectancy_r)
                    trades += r.n_trades
            atr_pct = float((f["atr"] / f["close"]).median())
            c = np.array(cells)
            rows.append({
                "timeframe": tf, "atr_pct": atr_pct,
                "fee_r": fee_pct / atr_pct if atr_pct else float("nan"),
                "frac_positive": float(np.mean(c > 0)) if len(c) else float("nan"),
                "median_exp_r": float(np.median(c)) if len(c) else float("nan"),
                "trades": trades,
            })
        except Exception as e:  # noqa: BLE001
            rows.append({"timeframe": tf, "error": str(e)[:60]})
    return pd.DataFrame(rows)
