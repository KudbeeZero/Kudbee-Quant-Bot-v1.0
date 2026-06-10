"""Trade-date grouping for session-gapped TradFi venues (no Sunday-stub levels).

Verified on live Yahoo data first (docs/research/tradfi_session_levels.md):
calendar-date groupings give Monday pivots/PDH/PDL computed from the few-bar
Sunday-evening stub. These tests pin the fix: ``trade_dates=True`` groups by
the exchange trade date (NY+6h — the 18:00-ET Globex boundary), so
Monday's daily levels derive from Friday's full session.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kudbee_quant.context.calendar import trade_date
from kudbee_quant.levels.builder import build_levels

NY_TZ = "America/New_York"


def _globex_frame(weeks: int = 4) -> pd.DataFrame:
    """Synthetic CME-like hourly frame: Sun 18:00 -> Fri 17:00 ET, 17:00-18:00
    daily break, closed weekends. Per-day range amplitude varies so stub vs
    full-day levels are distinguishable."""
    hours = pd.date_range("2025-05-04", periods=weeks * 7 * 24, freq="h")  # NY-local, Sunday start
    dow, h = hours.dayofweek, hours.hour
    keep = ((dow == 6) & (h >= 18)) | ((dow <= 3) & (h != 17)) | ((dow == 4) & (h < 17))
    ny = hours[keep]
    ts = ny.tz_localize(NY_TZ).tz_convert("UTC")
    i = np.arange(len(ts), dtype=float)
    base = 100.0 + 3.0 * np.sin(i / 24.0) + 0.01 * i
    amp = 0.5 + (ny.dayofyear.values % 5) * 0.3
    return pd.DataFrame({
        "timestamp": ts,
        "open": base, "high": base + amp, "low": base - amp,
        "close": base + 0.1, "volume": 1000.0,
    })


def _expected_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Independent per-trade-date OHLC aggregation for expectations."""
    td = trade_date(df["timestamp"])
    g = df.groupby(td).agg(dh=("high", "max"), dl=("low", "min"), dc=("close", "last"))
    return g.sort_index()


def test_trade_date_exchange_convention():
    ts = pd.Series(pd.to_datetime([
        "2025-05-04 22:00:00Z",  # Sun 18:00 ET -> Monday's trade date
        "2025-05-05 20:59:00Z",  # Mon 16:59 ET -> Monday
        "2025-05-05 22:00:00Z",  # Mon 18:00 ET -> Tuesday
        "2025-05-06 13:30:00Z",  # Tue 09:30 ET (RTH open) -> Tuesday (identity)
    ]))
    got = trade_date(ts).tolist()
    assert [d.isoformat() for d in got] == [
        "2025-05-05", "2025-05-05", "2025-05-06", "2025-05-06"]


def test_no_stub_days_under_trade_dates():
    df = _globex_frame()
    stub = build_levels(df)
    fixed = build_levels(df, trade_dates=True)
    # Calendar grouping creates a 6-bar Sunday stub; trade dates give uniform
    # 23-bar exchange days (Sun 18:00-evening belongs to Monday).
    assert stub.groupby("ny_date").size().min() == 6
    assert fixed.groupby("ny_date").size().min() == 23
    assert fixed.groupby("ny_date").size().max() == 23


def test_monday_pivots_come_from_friday_session():
    df = _globex_frame()
    fixed = build_levels(df, trade_dates=True)
    stub = build_levels(df)
    daily = _expected_daily(df)

    # A mid-session Monday bar in week 3 (history behind it for pivots).
    ny = pd.to_datetime(fixed["timestamp"], utc=True).dt.tz_convert(NY_TZ)
    mon_bar = fixed[(ny.dt.dayofweek == 0) & (ny.dt.hour == 10)].iloc[2]
    d = mon_bar["ny_date"]
    i = daily.index.get_loc(d)
    fri = daily.iloc[i - 1]  # prior trade date = Friday's full session
    expected_pp = (fri.dh + fri.dl + fri.dc) / 3.0
    assert abs(mon_bar["pivot_pp"] - expected_pp) < 1e-9
    assert abs(mon_bar["pivot_r1"] - (2 * expected_pp - fri.dl)) < 1e-9

    # Same wall-clock bar without the flag: pivots from the Sunday stub differ.
    ny_s = pd.to_datetime(stub["timestamp"], utc=True).dt.tz_convert(NY_TZ)
    stub_bar = stub[(ny_s.dt.dayofweek == 0) & (ny_s.dt.hour == 10)].iloc[2]
    assert abs(stub_bar["pivot_pp"] - mon_bar["pivot_pp"]) > 1e-6


def test_monday_pdh_pdl_come_from_friday_session():
    df = _globex_frame()
    fixed = build_levels(df, trade_dates=True)
    stub = build_levels(df)
    daily = _expected_daily(df)

    ny = pd.to_datetime(fixed["timestamp"], utc=True).dt.tz_convert(NY_TZ)
    mon_bar = fixed[(ny.dt.dayofweek == 0) & (ny.dt.hour == 10)].iloc[2]
    fri = daily.iloc[daily.index.get_loc(mon_bar["ny_date"]) - 1]
    assert abs(mon_bar["pdh"] - fri.dh) < 1e-9
    assert abs(mon_bar["pdl"] - fri.dl) < 1e-9

    # Unflagged: Monday PDH/PDL derive from the 2-bar Sunday UTC stub — a
    # strictly narrower range than any full session here.
    ny_s = pd.to_datetime(stub["timestamp"], utc=True).dt.tz_convert(NY_TZ)
    stub_bar = stub[(ny_s.dt.dayofweek == 0) & (ny_s.dt.hour == 1)].iloc[2]
    assert (stub_bar["pdh"] - stub_bar["pdl"]) < (fri.dh - fri.dl)


def test_adr_uses_full_trade_day_ranges():
    df = _globex_frame()
    fixed = build_levels(df, trade_dates=True)
    daily = _expected_daily(df)
    rng = (daily.dh - daily.dl)

    last = fixed.iloc[-1]
    i = daily.index.get_loc(last["ny_date"])
    expected_adr = rng.iloc[max(0, i - 14):i].mean()  # prior completed days
    assert abs(last["adr"] - expected_adr) < 1e-9
    # Every range entering ADR is a full 23-bar session — none below the
    # smallest possible full-day range (2*min amp = 1.0); a 6-bar stub would
    # not be guaranteed to clear this.
    assert (rng.iloc[:i] >= 1.0).all()


def test_rth_only_frames_are_identity_under_trade_dates():
    hours = pd.date_range("2025-05-05", periods=4 * 7 * 24, freq="h")  # Monday start
    keep = (hours.dayofweek <= 4) & (hours.hour >= 10) & (hours.hour <= 15)
    ny = hours[keep]
    ts = ny.tz_localize(NY_TZ).tz_convert("UTC")
    i = np.arange(len(ts), dtype=float)
    base = 200.0 + np.cos(i / 7.0)
    df = pd.DataFrame({"timestamp": ts, "open": base, "high": base + 1,
                       "low": base - 1, "close": base, "volume": 500.0})
    a = build_levels(df)
    b = build_levels(df, trade_dates=True)
    for col in ("pdh", "pdl", "pivot_pp", "daily_open", "adr"):
        pd.testing.assert_series_equal(a[col], b[col], check_names=False)


def test_paper_scan_wires_trade_dates_by_venue(tmp_path, monkeypatch):
    import kudbee_quant.paper.paper as pp
    from kudbee_quant.journal import TradeJournal

    seen = {}

    def fake_build(df, **kw):
        seen[len(seen)] = kw.get("trade_dates")
        return df

    fake_levels = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                                "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", fake_build)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake_levels)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC")})

    j = TradeJournal(path=tmp_path / "j.json", client=C())
    pp.paper_scan(["yahoo:GC=F"], min_pct=0.5, journal=j, client=C())
    pp.paper_scan(["BTCUSDT"], min_pct=0.5, journal=j, client=C())
    assert seen[0] is True    # TradFi venue -> trade-date grouping
    assert seen[1] is False   # crypto venue -> validated calendar grouping
