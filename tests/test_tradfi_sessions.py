"""TradFi session/RTH handling (§29) — stub-day levels, Yahoo tick row, and
the pending-limit false-fill fix. No network — synthetic frames / fake clients.

TradFi instruments (Globex futures, RTH equities) have session gaps the 24/7
crypto pipeline never sees: the Sunday-evening reopen is a ~6-bar "day", and
holidays truncate days. These tests pin (a) that prior-day reference levels
(ADR, floor pivots, PDH/PDL) ignore those stub days, (b) that on 24/7 data the
filtering is an exact no-op (the validated crypto behavior is unchanged), and
(c) the journal/ingest defects the §29 investigation uncovered.
"""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from kudbee_quant.context.calendar import complete_period_mask
from kudbee_quant.ingest.yahoo import YahooClient
from kudbee_quant.journal import Prediction, TradeJournal
from kudbee_quant.levels import build_levels


# --- frame builders ---------------------------------------------------------

def _day_bars(ny_date: str, hours, level: float, high: float, low: float):
    """Hourly bars on NY-local ``hours`` of ``ny_date`` with a flat o/c at
    ``level`` and the day's extremes on the first bar."""
    ts = (pd.DatetimeIndex([f"{ny_date} {h:02d}:00" for h in hours], tz="America/New_York")
          .tz_convert("UTC"))
    n = len(ts)
    return pd.DataFrame({
        "timestamp": ts,
        "open": [level] * n, "close": [level] * n,
        "high": [high] + [level] * (n - 1),
        "low": [low] + [level] * (n - 1),
        "volume": [1.0] * n,
    })


def _futures_week():
    """Mon-Fri full 24h days, a 6-bar Sunday Globex stub, then a full Monday.

    Full day i (i=0..4, Jun 1-5 2026): close 110+i, high 120+i, low 100+i
    (range 20). Sunday Jun 7 stub: 18:00-23:00 NY, extreme range 50..300 —
    if any Sunday value leaks into Monday's levels the assertions catch it.
    """
    days = [_day_bars(f"2026-06-0{i + 1}", range(24), 110 + i, 120 + i, 100 + i)
            for i in range(5)]
    days.append(_day_bars("2026-06-07", range(18, 24), 200, 300, 50))
    days.append(_day_bars("2026-06-08", range(24), 116, 126, 106))
    return pd.concat(days, ignore_index=True)


def _crypto_frame(n_days: int = 8):
    """Continuous 24/7 hourly bars (crypto-like): full NY days, ranges vary."""
    days = [_day_bars(f"2026-06-0{i + 1}", range(24), 110 + i, 120 + 2 * i, 100 - i)
            for i in range(n_days)]
    return pd.concat(days, ignore_index=True)


# --- complete_period_mask ---------------------------------------------------

def test_complete_period_mask_flags_stubs_only():
    counts = pd.Series({"mon": 24, "tue": 24, "wed": 23, "sun_stub": 6})
    mask = complete_period_mask(counts)
    assert mask["mon"] and mask["tue"] and mask["wed"]      # DST 23h day still full
    assert not mask["sun_stub"]
    # 24/7 crypto: every period passes -> filtering is inert.
    assert complete_period_mask(pd.Series([24] * 30)).all()


# --- levels: 24/7 invariance (the validated crypto behavior is untouched) ---

def test_crypto_adr_and_pivots_match_naive_computation():
    df = _crypto_frame()
    out = build_levels(df)
    by_date = out.groupby("ny_date").agg(h=("high", "max"), l=("low", "min"),
                                         c=("close", "last"))
    # ADR exactly == plain shift(1).rolling(14) over EVERY day's range.
    naive_adr = (by_date["h"] - by_date["l"]).shift(1).rolling(14, min_periods=1).mean()
    got_adr = out.groupby("ny_date")["adr"].first()
    pd.testing.assert_series_equal(got_adr, naive_adr, check_names=False)
    # Pivot PP exactly == prior-day (H+L+C)/3 for every day.
    naive_pp = ((by_date["h"] + by_date["l"] + by_date["c"]) / 3).shift(1)
    got_pp = out.groupby("ny_date")["pivot_pp"].first()
    pd.testing.assert_series_equal(got_pp, naive_pp, check_names=False)


# --- levels: stub days must not poison TradFi reference levels --------------

def test_sunday_stub_does_not_set_monday_pivots():
    out = build_levels(_futures_week())
    monday = out[out["ny_date"].astype(str) == "2026-06-08"].iloc[0]
    # Monday's pivots come from FRIDAY (h=124, l=104, c=114 -> pp=114),
    # not the extreme Sunday stub (which would give pp ~(300+50+200)/3).
    assert monday["pivot_pp"] == pytest.approx(114.0)
    assert monday["pivot_r1"] == pytest.approx(2 * 114.0 - 104.0)


def test_sunday_stub_bars_inherit_fridays_levels():
    out = build_levels(_futures_week())
    sunday = out[out["ny_date"].astype(str) == "2026-06-07"].iloc[0]
    # The stub session itself trades against the last FULL day's pivots.
    assert sunday["pivot_pp"] == pytest.approx(114.0)


def test_adr_excludes_stub_day_ranges():
    out = build_levels(_futures_week())
    monday = out[out["ny_date"].astype(str) == "2026-06-08"].iloc[0]
    # Mean of the five FULL days' ranges (each 20). Including the Sunday
    # stub's truncated range would distort it.
    assert monday["adr"] == pytest.approx(20.0)


def test_stub_day_does_not_set_pdh_pdl():
    # mm_cycle PDH/PDL group by UTC day; build a UTC-day calendar directly.
    def utc_day(date, hours, level, high, low):
        ts = pd.DatetimeIndex([f"{date} {h:02d}:00" for h in hours], tz="UTC")
        n = len(ts)
        return pd.DataFrame({
            "timestamp": ts, "open": [level] * n, "close": [level] * n,
            "high": [high] + [level] * (n - 1), "low": [low] + [level] * (n - 1),
            "volume": [1.0] * n,
        })
    df = pd.concat([
        utc_day("2026-06-04", range(24), 110, 120, 100),
        utc_day("2026-06-05", range(24), 111, 121, 101),
        utc_day("2026-06-07", range(22, 24), 200, 300, 50),   # 2-bar stub
        utc_day("2026-06-08", range(24), 112, 122, 102),
    ], ignore_index=True)
    out = build_levels(df)
    monday = out[pd.to_datetime(out["timestamp"], utc=True).dt.date.astype(str) == "2026-06-08"].iloc[0]
    assert monday["pdh"] == pytest.approx(121.0)   # Friday's high, not 300
    assert monday["pdl"] == pytest.approx(101.0)   # Friday's low, not 50


# --- Yahoo ingestion: drop the synthetic trailing tick row -------------------

def _yahoo_payload(timestamps, closes, granularity="1h"):
    return {"chart": {"error": None, "result": [{
        "meta": {"dataGranularity": granularity},
        "timestamp": timestamps,
        "indicators": {"quote": [{
            "open": closes, "high": closes, "low": closes,
            "close": closes, "volume": [1.0] * len(closes),
        }]},
    }]}}


def test_yahoo_parse_drops_subinterval_tick_row():
    t0 = 1_780_000_000 - (1_780_000_000 % 3600)
    # Two real hourly bars + a "tick row" 54 minutes into the next hour.
    payload = _yahoo_payload([t0, t0 + 3600, t0 + 3600 + 3240], [10.0, 11.0, 11.5])
    df = YahooClient._parse(payload, "CL=F")
    assert len(df) == 2 and df["close"].iloc[-1] == 11.0


def test_yahoo_parse_keeps_grid_aligned_bars_and_session_gaps():
    t0 = 1_780_000_000 - (1_780_000_000 % 3600)
    # An on-grid final bar (in-progress hour) and a session GAP both survive.
    payload = _yahoo_payload([t0, t0 + 3600, t0 + 50 * 3600], [10.0, 11.0, 12.0])
    df = YahooClient._parse(payload, "CL=F")
    assert len(df) == 3
    # Unknown granularity -> conservative no-drop.
    payload = _yahoo_payload([t0, t0 + 1800], [10.0, 10.5], granularity="13m")
    assert len(YahooClient._parse(payload, "CL=F")) == 2


# --- journal: the pending-limit false-fill fix (§29) -------------------------

class _BarsClient:
    def __init__(self, df):
        self.df = df

    def klines(self, symbol, interval="1h", limit=1000):
        return self.df


def _pending(limit_price=99.5, stop=98.5, target=102.5, fill_days=0.5, **kw):
    return Prediction(symbol="X", kind="bracket", level=limit_price, entry=limit_price,
                      stop=stop, target=target, direction=1.0, target_r=3.0,
                      deadline_days=3.0, pending_limit=True, signal_price=100.0,
                      fill_deadline_days=fill_days, setup="c", **kw)


def _bars(end_offset_h: float, n: int = 6, low: float = 100.0):
    """n hourly bars ENDING ``end_offset_h`` hours from now (negative = past)."""
    end = datetime.now(timezone.utc) + timedelta(hours=end_offset_h)
    ts = pd.date_range(end - timedelta(hours=n - 1), periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"timestamp": ts, "open": 101.0, "high": 102.0,
                         "low": low, "close": 101.0, "volume": 1.0})


def test_fresh_pending_limit_stays_pending_with_no_new_bars(tmp_path):
    # All bars predate creation (the state seconds after the scan logs a
    # trade). The limit CANNOT have traded -> stays pending, no filled_at.
    j = TradeJournal(path=tmp_path / "j.json", client=_BarsClient(_bars(-1)))
    j.add(_pending())
    assert j.check_open() == []
    p = j.predictions[-1]
    assert p.status == "pending" and p.filled_at is None


def test_pending_limit_with_no_bars_cancels_after_fill_window(tmp_path):
    # No bars ever printed in the fill window (e.g. a TradFi limit logged
    # into a closed session) -> cancelled, NOT a miss (it never traded).
    j = TradeJournal(path=tmp_path / "j.json", client=_BarsClient(_bars(-30)))
    p = _pending(fill_days=0.25)
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
    j.add(p)
    changed = j.check_open()
    assert changed and changed[-1].status == "cancelled"
    assert changed[-1].outcome_r is None


def test_fill_timestamp_is_the_fill_bars_time_not_wall_clock(tmp_path):
    # Limit 99.5; bars since creation dip to 99 -> fills on the FIRST bar
    # after creation, and filled_at records that bar's timestamp.
    bars = _bars(0, n=6, low=99.0)
    j = TradeJournal(path=tmp_path / "j.json", client=_BarsClient(bars))
    p = _pending()
    p.created_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    j.add(p)
    changed = j.check_open()
    assert changed and changed[-1].status == "open"
    created = datetime.fromisoformat(p.created_at)
    fill_bar = bars[pd.to_datetime(bars["timestamp"], utc=True) >= created].iloc[0]
    assert changed[-1].filled_at == str(fill_bar["timestamp"])
