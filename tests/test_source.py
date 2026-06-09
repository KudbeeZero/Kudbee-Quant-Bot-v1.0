"""Source provenance (bot vs human) scoring + resolved-series tests (no network)."""
from kudbee_quant.journal import Prediction, TradeJournal


def _resolved(symbol, source, outcome_r, status="hit"):
    p = Prediction(symbol=symbol, kind="bracket", level=100, entry=100, stop=99,
                   target=103, direction=1.0, target_r=3.0, deadline_days=1.0,
                   source=source, setup="x")
    p.status = status
    p.outcome_r = outcome_r
    p.resolved_at = "2026-06-09T0%d:00:00+00:00" % (1 if status == "hit" else 2)
    return p


def test_source_defaults_to_bot():
    p = Prediction(symbol="X", kind="bracket", level=1, deadline_days=1)
    assert p.source == "bot"


def test_source_record_splits_human_and_bot(tmp_path):
    j = TradeJournal(path=tmp_path / "j.json")
    j.predictions = [_resolved("BTCUSDT", "bot", 3.0), _resolved("BTCUSDT", "bot", -1.0, "miss"),
                     _resolved("ETHUSDT", "human", 3.0)]
    rec = j.source_record()
    assert rec["bot"]["n"] == 2 and rec["bot"]["hits"] == 1
    assert abs(rec["bot"]["expectancy_r"] - 1.0) < 1e-9      # (3 + -1)/2
    assert rec["human"]["n"] == 1 and abs(rec["human"]["expectancy_r"] - 3.0) < 1e-9


def test_resolved_series_is_time_ordered(tmp_path):
    j = TradeJournal(path=tmp_path / "j.json")
    a = _resolved("BTCUSDT", "bot", -1.0, "miss")  # resolved_at hour 02
    b = _resolved("ETHUSDT", "bot", 3.0, "hit")    # resolved_at hour 01
    j.predictions = [a, b]
    series = j.resolved_series()
    assert [s["r"] for s in series] == [3.0, -1.0]   # sorted by time (hit@01 first)


def test_human_source_persists_through_save_load(tmp_path):
    path = tmp_path / "j.json"
    j = TradeJournal(path=path)
    j.add(Prediction(symbol="ZECUSDT", kind="bracket", level=100, entry=100, stop=99,
                     target=103, direction=1.0, target_r=3.0, deadline_days=1.0,
                     source="human", setup="my_read"))
    reloaded = TradeJournal(path=path)
    assert reloaded.predictions[-1].source == "human"
