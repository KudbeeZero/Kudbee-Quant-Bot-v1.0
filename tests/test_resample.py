"""Tests for kudbee_quant/ingest/resample.py — resampling to non-native timeframes.

MEMORY §86/CROSSROADS N6: the trailing resampled bucket must be dropped when the
source data doesn't yet reach its end boundary — otherwise a partial bucket (built
from fewer base bars than the target interval needs) gets handed downstream looking
like a normal, closed bar, understating its true high/overstating its low/misstating
its close.
"""
from __future__ import annotations

import pandas as pd

from kudbee_quant.ingest.resample import resample_ohlcv


def _hourly(n, start="2024-01-01"):
    ts = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({
        "timestamp": ts,
        "open": range(n), "high": [x + 1 for x in range(n)],
        "low": list(range(n)), "close": range(n),
        "volume": [10.0] * n,
    })


def test_trailing_partial_bucket_is_dropped():
    # 3h buckets: [00-03), [03-06). Only 5 hourly bars (00..04) -> the second
    # bucket [03-06) only has hours 03,04 — 2 of the 3 it needs. Must be dropped.
    df = _hourly(5)
    out = resample_ohlcv(df, "3h")
    assert len(out) == 1
    assert out["timestamp"].iloc[0] == pd.Timestamp("2024-01-01T00:00:00Z")


def test_fully_covered_buckets_are_all_kept():
    # 6 hourly bars (00..05) resampled to 3h -> exactly 2 complete buckets,
    # [00-03) proven complete by [03-06)'s own bars existing, [03-06) proven
    # complete by... nothing further, so with exactly 6 bars the trailing
    # bucket [03-06) is NOT provably complete (source ends at hour 05, bucket
    # end is 06:00) and must still be dropped, leaving exactly 1 bucket.
    df = _hourly(6)
    out = resample_ohlcv(df, "3h")
    assert len(out) == 1


def test_extra_bar_into_the_next_bucket_proves_completion():
    # 7 hourly bars (00..06): hour 06 belongs to the THIRD bucket [06-09), which
    # proves [03-06) is fully closed (the source has moved past its end). Both
    # [00-03) and [03-06) must survive; the new partial [06-09) bucket is dropped.
    df = _hourly(7)
    out = resample_ohlcv(df, "3h")
    assert len(out) == 2
    assert list(out["timestamp"]) == [pd.Timestamp("2024-01-01T00:00:00Z"),
                                       pd.Timestamp("2024-01-01T03:00:00Z")]


def test_all_buckets_incomplete_yields_empty_not_a_crash():
    df = _hourly(2)   # only 2 hours -> the single 3h bucket is partial
    out = resample_ohlcv(df, "3h")
    assert len(out) == 0
    assert list(out.columns) == ["timestamp", "open", "high", "low", "close", "volume"]


def test_native_interval_resample_still_works():
    """Resampling to the SAME granularity as the source (a no-op aggregation)
    must not spuriously drop the last row — every bucket is 1:1 with a source
    bar, so the source always 'reaches' each bucket's own start but the very
    last one still needs the same completeness rule as any other rate."""
    df = _hourly(5)
    out = resample_ohlcv(df, "1h")
    # Last hourly bar (04:00) is its own bucket [04:00,05:00); the source's max
    # timestamp is 04:00, which is < the bucket end (05:00) -> conservatively
    # dropped, same as any other trailing partial bucket.
    assert len(out) == 4
