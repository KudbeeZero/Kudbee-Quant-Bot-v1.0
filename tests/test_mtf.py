"""Tests for multi-timeframe agreement merge (no network)."""
import pandas as pd

from kudbee_quant.levels.mtf import add_htf_agreement


def test_htf_agreement_is_causal_and_filled():
    # 1h bars hourly; 4h reads at 00:00 and 04:00 UTC.
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01 00:00", periods=8, freq="h", tz="UTC"),
        "close": range(8),
    })
    htf = pd.DataFrame({
        "timestamp": pd.to_datetime(["2024-01-01 00:00", "2024-01-01 04:00"], utc=True),
        "htf_dir": [1.0, -1.0], "htf_pct": [0.6, 0.7],
    })
    out = add_htf_agreement(df, htf)
    assert "htf_dir" in out.columns and len(out) == 8
    # HTF read is shifted by one closed bar (no lookahead): the 04:00 htf value
    # (-1) only becomes visible AFTER 04:00, never on the 04:00 bar itself.
    at_04 = out[out["timestamp"] == pd.Timestamp("2024-01-01 04:00", tz="UTC")]
    assert at_04["htf_dir"].iloc[0] != -1.0  # still the prior (shifted) read
