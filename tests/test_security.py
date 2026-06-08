"""Security-focused tests (no network)."""
import numpy as np
import pandas as pd
import pytest

from kudbee_quant.config import SecretStr, get_secret
from kudbee_quant.ingest.cache import DataCache
from kudbee_quant.ingest.router import parse_spec
from kudbee_quant.ingest.validation import validate_ohlcv


def test_symbol_validation_blocks_injection():
    # SSRF / URL-injection attempts must be rejected.
    for bad in ["../../etc/passwd", "BTC&x=1", "BTC/USDT?a=b", "http://evil", "a" * 50, ""]:
        with pytest.raises(ValueError):
            parse_spec(bad if ":" not in bad else "binance:" + bad)
    # Legitimate symbols pass.
    assert parse_spec("BTCUSDT") == ("binance", "BTCUSDT")
    assert parse_spec("yahoo:GC=F") == ("yahoo", "GC=F")
    # Unknown source is not silently trusted as a prefix (becomes a symbol that fails).
    with pytest.raises(ValueError):
        parse_spec("evil:http://x")


def test_cache_keys_cannot_escape_root(tmp_path):
    cache = DataCache(root=tmp_path)
    # A malicious key with traversal still maps to a hashed file inside root.
    data_path, meta_path = cache._paths("../../../../etc/passwd")
    assert tmp_path.resolve() in data_path.parents
    assert tmp_path.resolve() in meta_path.parents
    # Round-trip works and stays contained.
    cache.put("../../evil", pd.DataFrame({"a": [1]}))
    assert cache.get("../../evil", ttl_seconds=1e9) is not None


def test_secretstr_never_leaks_value():
    s = SecretStr("super-secret-token")
    assert "super-secret-token" not in repr(s)
    assert "super-secret-token" not in str(s)
    assert "super-secret-token" not in f"{s}"
    assert s.reveal() == "super-secret-token"  # only via explicit reveal


def test_get_secret_required_raises(monkeypatch):
    monkeypatch.delenv("KQ_TEST_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        get_secret("KQ_TEST_SECRET", required=True)
    monkeypatch.setenv("KQ_TEST_SECRET", "abc")
    assert get_secret("KQ_TEST_SECRET").reveal() == "abc"


def test_validate_ohlcv_rejects_garbage():
    base = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC"),
        "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0, "volume": 100.0,
    }, index=range(5))
    # Missing column -> raise.
    with pytest.raises(ValueError):
        validate_ohlcv(base.drop(columns="high"))
    # Negative price row dropped.
    bad = base.copy(); bad.loc[2, "close"] = -5
    assert len(validate_ohlcv(bad)) == 4
    # Inf dropped; duplicate timestamp deduped.
    bad2 = base.copy(); bad2.loc[1, "high"] = np.inf
    assert len(validate_ohlcv(bad2)) == 4
    dup = pd.concat([base, base.iloc[[0]]], ignore_index=True)
    assert validate_ohlcv(dup)["timestamp"].is_unique
