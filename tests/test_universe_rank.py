"""Tests for the opt-in dynamic volume universe (§B). No network — a stub client
returns DataFrames with known quote_volume so ranking is deterministic."""
from __future__ import annotations

import pandas as pd
import pytest

from kudbee_quant.universe_rank import rank_by_volume, volume_ranked_universe


class _StubClient:
    """Returns a frame whose quote_volume is a fixed per-symbol level; raises for
    symbols in `broken` to exercise the skip path."""
    def __init__(self, levels: dict[str, float], broken: tuple[str, ...] = ()):
        self.levels = levels
        self.broken = broken

    def klines(self, symbol, interval="1h", limit=1000):
        if symbol in self.broken:
            raise RuntimeError("delisted / fetch failed")
        qv = self.levels[symbol]
        return pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=limit, freq="h", tz="UTC"),
            "close": [100.0] * limit,
            "volume": [qv / 100.0] * limit,
            "quote_volume": [qv] * limit,
        })


def test_rank_orders_by_volume_desc():
    client = _StubClient({"AAA": 10.0, "BBB": 30.0, "CCC": 20.0})
    ranked = rank_by_volume(["AAA", "BBB", "CCC"], client=client)
    assert [s for s, _ in ranked] == ["BBB", "CCC", "AAA"]
    assert ranked[0][1] == 30.0


def test_volume_ranked_universe_top_n_and_order():
    client = _StubClient({"AAA": 10.0, "BBB": 30.0, "CCC": 20.0, "DDD": 5.0})
    assert volume_ranked_universe(["AAA", "BBB", "CCC", "DDD"], top_n=2, client=client) == ["BBB", "CCC"]


def test_broken_symbols_are_skipped_not_fatal():
    client = _StubClient({"AAA": 10.0, "CCC": 20.0}, broken=("BBB",))
    out = volume_ranked_universe(["AAA", "BBB", "CCC"], top_n=10, client=client)
    assert out == ["CCC", "AAA"]          # BBB dropped, rest still ranked


def test_min_quote_volume_floor():
    client = _StubClient({"AAA": 10.0, "BBB": 30.0, "CCC": 20.0})
    out = volume_ranked_universe(["AAA", "BBB", "CCC"], top_n=10,
                                 min_quote_volume=15.0, client=client)
    assert out == ["BBB", "CCC"]          # AAA (10) below the 15 floor


def test_defaults_to_candidate_pool():
    # No candidates passed -> uses universe.CRYPTO_CANDIDATES (all routed to the stub).
    from kudbee_quant.universe import CRYPTO_CANDIDATES
    client = _StubClient({s: float(i) for i, s in enumerate(CRYPTO_CANDIDATES, 1)})
    ranked = rank_by_volume(client=client)
    assert len(ranked) == len(CRYPTO_CANDIDATES)
    assert ranked[0][0] == CRYPTO_CANDIDATES[-1]   # highest index == highest volume
