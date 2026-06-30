"""Tests for the ADR exhaustion filter + its paper-scan gate ('_adr')."""
import pandas as pd

from kudbee_quant.signals.adr_filter import adr_consumed_pct, adr_gate


def _daily_frame(day_ranges, today_range):
    """Build an hourly OHLCV frame whose daily resample has the given ranges.

    Each completed day is a single bar spanning [0, range]; today is a partial bar.
    """
    rows = []
    base = pd.Timestamp("2026-01-01T00:00:00Z")
    for i, rng in enumerate(day_ranges):
        ts = base + pd.Timedelta(days=i)
        rows.append({"timestamp": ts, "open": 100.0, "high": 100.0 + rng,
                     "low": 100.0, "close": 100.0 + rng, "volume": 1.0})
    ts = base + pd.Timedelta(days=len(day_ranges))
    rows.append({"timestamp": ts, "open": 100.0, "high": 100.0 + today_range,
                 "low": 100.0, "close": 100.0 + today_range, "volume": 1.0})
    return pd.DataFrame(rows)


def test_consumed_pct_from_daily_resample():
    # 14 complete days of range 10, then today's range 5 -> consumed 0.5.
    df = _daily_frame([10.0] * 14, today_range=5.0)
    assert abs(adr_consumed_pct(df) - 0.5) < 1e-9


def test_prefers_precomputed_column():
    df = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC"),
                       "high": [1, 2, 3], "low": [0, 0, 0], "pct_adr_used": [0.1, 0.4, 0.82]})
    assert abs(adr_consumed_pct(df) - 0.82) < 1e-9      # last value of the column


def test_fail_open_few_daily_bars():
    df = _daily_frame([10.0] * 3, today_range=8.0)      # only 4 daily bars (< 5)
    assert adr_consumed_pct(df) == 0.0


def test_fail_open_missing_columns():
    assert adr_consumed_pct(pd.DataFrame()) == 0.0
    assert adr_consumed_pct(None) == 0.0


def test_gate_allows_below_threshold_blocks_at_or_above():
    low = _daily_frame([10.0] * 14, today_range=5.0)    # consumed 0.5
    high = _daily_frame([10.0] * 14, today_range=8.0)   # consumed 0.8
    assert adr_gate(low, 1.0, threshold=0.75) is True
    assert adr_gate(high, 1.0, threshold=0.75) is False


# --- paper_scan wiring -------------------------------------------------------

def _force_long_signal(monkeypatch):
    import kudbee_quant.paper.paper as pp
    fake = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake)
    return pp


class _C:
    def klines(self, *a, **k):
        return pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=1, freq="h", tz="UTC")})


def test_adr_gate_blocks(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    monkeypatch.setattr(pp, "adr_gate", lambda f, d, t: False)   # exhausted -> block
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), adr_filter=True)
    assert logged == []


def test_adr_gate_allows_and_tags(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    monkeypatch.setattr(pp, "adr_gate", lambda f, d, t: True)    # runway left -> allow
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), adr_filter=True)
    assert len(logged) == 1 and "_adr" in logged[0].setup


def test_adr_gate_off_byte_identical(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    monkeypatch.setattr(pp, "adr_gate", lambda f, d, t: False)   # would block if consulted
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C())     # filter defaults off
    assert len(logged) == 1 and "_adr" not in logged[0].setup
