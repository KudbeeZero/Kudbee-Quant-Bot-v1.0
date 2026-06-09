"""Tests for the directional bias layer (human read -> bot scalps with it)."""
import pandas as pd

from kudbee_quant.bias import Bias, BiasBook
from kudbee_quant.journal import TradeJournal


def test_bias_set_get_clear(tmp_path):
    bb = BiasBook(path=tmp_path / "b.json")
    bb.set("SOLUSDT", "short", target=62.0, days=1, note="dopen reject")
    b = bb.get("SOLUSDT")
    assert b is not None and b.direction == -1.0 and b.side == "short" and b.target == 62.0
    # Persisted.
    assert BiasBook(path=tmp_path / "b.json").get("solusdt").side == "short"
    assert bb.clear("SOLUSDT") and bb.get("SOLUSDT") is None


def test_expired_bias_is_inactive(tmp_path):
    bb = BiasBook(path=tmp_path / "b.json")
    bb.set("BTCUSDT", "long", days=-1)  # already expired
    assert bb.get("BTCUSDT") is None and bb.active() == []


def test_paper_scan_only_trades_with_bias(tmp_path, monkeypatch):
    import kudbee_quant.paper.paper as pp
    # Engine wants to go LONG (direction +1, 60% confluence).
    fake = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC")})

    j = TradeJournal(path=tmp_path / "j.json", client=C())
    bb = BiasBook(path=tmp_path / "b.json")
    bb.set("BTCUSDT", "short")  # human says SHORT, engine says long -> skip
    assert pp.paper_scan(["BTCUSDT"], journal=j, client=C(), biases=bb) == []

    bb.set("BTCUSDT", "long")   # now aligned -> trade
    logged = pp.paper_scan(["BTCUSDT"], journal=j, client=C(), biases=bb)
    assert len(logged) == 1 and logged[0].direction == 1.0
    assert "bias_scalp" in logged[0].setup


def test_require_bias_skips_unbiased_symbols(tmp_path, monkeypatch):
    import kudbee_quant.paper.paper as pp
    fake = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [-1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC")})

    j = TradeJournal(path=tmp_path / "j.json", client=C())
    bb = BiasBook(path=tmp_path / "b.json")  # empty
    assert pp.paper_scan(["ETHUSDT"], journal=j, client=C(), biases=bb, require_bias=True) == []
