"""Tests for ingestion routing, period inference, and Yahoo parsing (no network)."""
import pandas as pd

from kudbee_quant.backtest.metrics import infer_periods_per_year
from kudbee_quant.ingest.router import parse_spec
from kudbee_quant.ingest.yahoo import YahooClient


def test_parse_spec_defaults_to_binance():
    assert parse_spec("BTCUSDT") == ("binance", "BTCUSDT")
    assert parse_spec("yahoo:SPY") == ("yahoo", "SPY")
    assert parse_spec("binance:ETHUSDT") == ("binance", "ETHUSDT")
    # A bare symbol containing '=' (Yahoo futures) without a known prefix
    # stays a Binance default rather than being mis-split.
    assert parse_spec("GC=F") == ("binance", "GC=F")


def test_infer_periods_hourly_vs_daily():
    hourly = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=100, freq="h", tz="UTC")})
    daily = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC")})
    assert abs(infer_periods_per_year(hourly) - 8766) < 5
    assert abs(infer_periods_per_year(daily) - 365.25) < 1
    # Missing timestamps -> safe fallback.
    assert infer_periods_per_year(pd.DataFrame({"close": [1, 2]})) == 365.0


def test_yahoo_parse_builds_ohlcv():
    payload = {
        "chart": {
            "error": None,
            "result": [
                {
                    "timestamp": [1704153600, 1704240000, 1704326400],
                    "indicators": {
                        "quote": [
                            {
                                "open": [10.0, 10.5, None],
                                "high": [11.0, 12.0, 13.0],
                                "low": [9.0, 10.0, 11.0],
                                "close": [10.5, 11.0, None],  # null close dropped
                                "volume": [1000, None, 3000],
                            }
                        ]
                    },
                }
            ],
        }
    }
    df = YahooClient._parse(payload, "SPY")
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2  # the null-close row is dropped
    assert df["volume"].iloc[1] == 0.0  # null volume filled
    assert str(df["timestamp"].dt.tz) == "UTC"
