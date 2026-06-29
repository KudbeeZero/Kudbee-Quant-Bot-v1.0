"""Tests for the signal-fingerprint expectancy DB + its paper-scan gate ('_fp')."""
from types import SimpleNamespace

import pandas as pd

from kudbee_quant.signals.signal_fingerprint import (
    MIN_SAMPLE, SignalFingerprintDB, make_fingerprint,
)


def _closed(setup="confluence_r_60pct", direction=1.0, r=1.0,
            created_at="2026-01-01T14:00:00+00:00", status="hit"):
    """A minimal closed-Prediction stub (fingerprint reads via getattr)."""
    return SimpleNamespace(setup=setup, direction=direction, outcome_r=r,
                           created_at=created_at, filled_at=None, status=status)


# --- fingerprint construction ------------------------------------------------

def test_make_fingerprint_buckets():
    fp = make_fingerprint(confluence_pct=0.62, direction=1.0,
                          timestamp="2026-01-01T14:00:00+00:00")
    assert fp.confluence_bucket == "0.60-0.70"
    assert fp.direction == "long"
    assert fp.session == "ny"          # 14:00 UTC = London/NY overlap -> ny
    # unpersisted dims collapse to unknown
    assert fp.ema_stack == "unknown" and fp.atr_regime == "unknown"


def test_make_fingerprint_missing_fields_are_unknown():
    fp = make_fingerprint()
    assert fp.key() == ("unknown",) * 5


def test_session_buckets():
    def sess(h):
        return make_fingerprint(timestamp=f"2026-01-01T{h:02d}:00:00+00:00").session
    assert sess(9) == "london"
    assert sess(14) == "ny"            # overlap folded into ny
    assert sess(18) == "ny"
    assert sess(3) == "asia"
    assert sess(22) == "other"


# --- DB aggregation ----------------------------------------------------------

def test_db_expectancy_and_win_rate():
    preds = [_closed(r=2.0), _closed(r=-1.0), _closed(r=1.0)]
    db = SignalFingerprintDB.from_predictions(preds)
    fp = make_fingerprint(confluence_pct=0.60, direction=1.0,
                          timestamp="2026-01-01T14:00:00+00:00")
    assert db.sample_size(fp) == 3
    assert abs(db.expectancy(fp) - (2.0 - 1.0 + 1.0) / 3) < 1e-9
    assert abs(db.win_rate(fp) - 2 / 3) < 1e-9


def test_db_ignores_open_and_unresolved():
    preds = [_closed(status="open"), _closed(r=None, status="hit")]
    db = SignalFingerprintDB.from_predictions(preds)
    fp = make_fingerprint(confluence_pct=0.60, direction=1.0,
                          timestamp="2026-01-01T14:00:00+00:00")
    assert db.sample_size(fp) == 0


# --- should_skip: the MIN_SAMPLE floor + the expectancy rule -----------------

def test_should_skip_respects_min_sample_floor():
    # 4 losing trades (< MIN_SAMPLE=5) must NEVER block.
    preds = [_closed(r=-1.0) for _ in range(MIN_SAMPLE - 1)]
    db = SignalFingerprintDB.from_predictions(preds)
    fp = make_fingerprint(confluence_pct=0.60, direction=1.0,
                          timestamp="2026-01-01T14:00:00+00:00")
    assert db.sample_size(fp) == MIN_SAMPLE - 1
    assert db.should_skip(fp) is False


def test_should_skip_blocks_sampled_losing_bucket():
    preds = [_closed(r=-1.0) for _ in range(MIN_SAMPLE)]
    db = SignalFingerprintDB.from_predictions(preds)
    fp = make_fingerprint(confluence_pct=0.60, direction=1.0,
                          timestamp="2026-01-01T14:00:00+00:00")
    assert db.should_skip(fp) is True              # negative expectancy, >=5 samples
    # a winning bucket of the same size is NOT skipped
    win_db = SignalFingerprintDB.from_predictions([_closed(r=1.0) for _ in range(MIN_SAMPLE)])
    assert win_db.should_skip(fp) is False


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


class _FakeDB:
    """Stand-in fingerprint DB with a fixed should_skip verdict."""
    verdict = False

    @classmethod
    def from_predictions(cls, predictions):
        return cls()

    def should_skip(self, fp, *a, **k):
        return self.verdict


def test_fingerprint_gate_blocks_sampled_loser(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    _FakeDB.verdict = True
    monkeypatch.setattr(pp, "SignalFingerprintDB", _FakeDB)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), fingerprint_gate=True)
    assert logged == []


def test_fingerprint_gate_allows_and_tags(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    _FakeDB.verdict = False
    monkeypatch.setattr(pp, "SignalFingerprintDB", _FakeDB)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), fingerprint_gate=True)
    assert len(logged) == 1 and "_fp" in logged[0].setup


def test_fingerprint_gate_off_is_byte_identical(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch)
    _FakeDB.verdict = True       # would block if consulted
    monkeypatch.setattr(pp, "SignalFingerprintDB", _FakeDB)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C())     # gate defaults off
    assert len(logged) == 1 and "_fp" not in logged[0].setup
