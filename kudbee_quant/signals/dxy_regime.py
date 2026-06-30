"""DXY Regime Filter — inverse-correlation macro gate for crypto entries.

DXY (US Dollar Index) is structurally inverse to BTC and most crypto (~-0.65
rolling correlation). When the dollar is in a confirmed uptrend, crypto longs
face a macro headwind. Three-state output:

  RISK_ON  (+1): DXY below its EMA AND declining  -> favours crypto longs
  RISK_OFF (-1): DXY above its EMA AND rising      -> favours crypto shorts
  NEUTRAL   (0): within the neutral band, or mixed -> pass-through

HONESTY NOTE: the DXY/crypto correlation is strongest on the 4H/Daily, so the
regime is always evaluated on the 4H candle regardless of the trade's timeframe.
Yahoo Finance has no native 4h interval (it serves 1h/1d), so we fetch 1h and
resample to 4h OHLC here.

FAIL-OPEN: if DXY data is unavailable (rate limit, weekend gap, parse error),
return NEUTRAL so a data outage never silently kills all entries.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DXY_SPEC = "yahoo:DX-Y.NYB"     # RouterClient yahoo path -> US Dollar Index
DXY_FETCH_INTERVAL = "1h"       # Yahoo native; resampled to 4h below
DXY_EMA_SPAN = 50
DXY_SLOPE_BARS = 5
DXY_NEUTRAL_BAND = 0.002        # 0.2% band around the EMA = neutral

RISK_ON = 1
RISK_OFF = -1
NEUTRAL = 0

_STATE_NAME = {RISK_ON: "RISK_ON", RISK_OFF: "RISK_OFF", NEUTRAL: "NEUTRAL"}


def _resample_4h(df: pd.DataFrame) -> pd.DataFrame:
    """1h OHLC -> 4h OHLC (timestamp-indexed)."""
    d = df.copy()
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    d = d.set_index("timestamp").sort_index()
    out = pd.DataFrame({
        "open": d["open"].resample("4h").first(),
        "high": d["high"].resample("4h").max(),
        "low": d["low"].resample("4h").min(),
        "close": d["close"].resample("4h").last(),
    }).dropna()
    return out


def compute_dxy(client, *, ema_span: int = DXY_EMA_SPAN,
                slope_bars: int = DXY_SLOPE_BARS,
                neutral_band: float = DXY_NEUTRAL_BAND) -> dict:
    """Compute the DXY regime + the inputs it was derived from.

    Returns ``{"state", "pct_diff", "slope", "last_close", "last_ema", "n_bars",
    "ok"}``. On any failure returns a NEUTRAL, ``ok=False`` dict (fail-open)."""
    fail = {"state": NEUTRAL, "pct_diff": None, "slope": None,
            "last_close": None, "last_ema": None, "n_bars": 0, "ok": False}
    try:
        raw = client.klines(DXY_SPEC, interval=DXY_FETCH_INTERVAL, limit=1500)
        if raw is None or len(raw) == 0:
            return fail
        bars = _resample_4h(raw)
        # If too few 4h bars (sparse intraday history), fall back to 1h closes.
        if len(bars) >= ema_span + slope_bars:
            close = pd.to_numeric(bars["close"], errors="coerce").dropna()
        else:
            close = pd.to_numeric(raw["close"], errors="coerce").dropna()
        if len(close) < slope_bars + 2:
            return fail
        ema = close.ewm(span=ema_span, adjust=False).mean()
        last_close = float(close.iloc[-1])
        last_ema = float(ema.iloc[-1])
        if last_ema == 0 or not np.isfinite(last_ema):
            return fail
        pct_diff = (last_close - last_ema) / last_ema
        y = ema.iloc[-slope_bars:].to_numpy(dtype=float)
        slope = float(np.polyfit(np.arange(len(y)), y, 1)[0])
        if pct_diff < -neutral_band and slope < 0:
            state = RISK_ON
        elif pct_diff > neutral_band and slope > 0:
            state = RISK_OFF
        else:
            state = NEUTRAL
        return {"state": state, "pct_diff": pct_diff, "slope": slope,
                "last_close": last_close, "last_ema": last_ema,
                "n_bars": int(len(close)), "ok": True}
    except Exception:
        return fail


def dxy_regime(client, *, ema_span: int = DXY_EMA_SPAN,
               slope_bars: int = DXY_SLOPE_BARS,
               neutral_band: float = DXY_NEUTRAL_BAND) -> int:
    """RISK_ON (+1) / RISK_OFF (-1) / NEUTRAL (0). Fail-open to NEUTRAL."""
    return compute_dxy(client, ema_span=ema_span, slope_bars=slope_bars,
                       neutral_band=neutral_band)["state"]


def state_name(state: int) -> str:
    return _STATE_NAME.get(state, "NEUTRAL")
