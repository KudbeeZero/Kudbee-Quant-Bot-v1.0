"""Tests for the multi-asset validation harness (deterministic, no network)."""
import numpy as np
import pandas as pd

from kudbee_quant.backtest import pvsra_mm_positions, pvsra_positions
from kudbee_quant.validation import validate_frames
from kudbee_quant.validation.universe import AssetReport, _verdict


def _ohlcv(n: int = 1200, drift: float = 0.0008, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, 0.012, n)
    close = 100 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
            "open": close, "high": high, "low": low, "close": close,
            "volume": rng.lognormal(5, 0.6, n),
        }
    )


def test_validate_frames_structure():
    frames = {f"SYN{i}": _ohlcv(seed=i) for i in range(3)}
    report = validate_frames(frames, pvsra_positions, mc_paths=300)
    assert len(report.assets) == 3
    assert 0.0 <= report.frac_profitable_oos <= 1.0
    assert isinstance(report.robust, bool)
    assert report.verdict  # non-empty
    df = report.to_frame()
    assert {"symbol", "oos_sharpe", "oos_return"} <= set(df.columns)


def test_mm_strategy_runs_in_validation():
    frames = {f"SYN{i}": _ohlcv(seed=10 + i) for i in range(2)}
    report = validate_frames(frames, pvsra_mm_positions, mc_paths=200)
    assert len(report.assets) == 2
    for a in report.assets:
        assert a.n_bars > 0


def test_verdict_is_conservative_with_few_assets():
    # Even a great-looking single asset must not be called robust (n<3).
    great = AssetReport("X", 1000, 2.0, 3.0, -0.1, 2.5, 2.5, 0.5, 0.9, 0.0)
    report = _verdict([great])
    assert report.robust is False
    assert any("too few" in n for n in report.notes)


def test_verdict_flags_instability():
    # Big IS/OOS gap across assets => flagged as noise, not robust.
    noisy = [
        AssetReport(f"A{i}", 1000, 0.2, 1.0, -0.2, -1.0, 3.5, 0.3, 0.7, 4.5)
        for i in range(4)
    ]
    report = _verdict(noisy)
    assert report.robust is False
    assert any("disagree" in n for n in report.notes)


def test_verdict_can_certify_clean_robust_edge():
    clean = [
        AssetReport(f"A{i}", 2000, 0.5, 1.6, -0.15, 1.4, 1.6, 0.30, 0.72, 0.2)
        for i in range(5)
    ]
    # Low correlation => five near-independent bets => can certify robust.
    report = _verdict(clean, median_corr=0.1)
    assert report.robust is True
    assert "ROBUST" in report.verdict


def test_correlation_downgrades_robustness():
    # Same clean per-asset stats, but highly correlated => not independent
    # evidence, so the harness must refuse to certify robust.
    clean = [
        AssetReport(f"A{i}", 2000, 0.5, 1.6, -0.15, 1.4, 1.6, 0.30, 0.72, 0.2)
        for i in range(5)
    ]
    report = _verdict(clean, median_corr=0.85)
    assert report.robust is False
    assert report.effective_n < 3
    assert any("correlated" in n for n in report.notes)
