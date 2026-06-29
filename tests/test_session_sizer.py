"""Tests for the session risk sizer + its paper-scan flag ('_ss')."""
import pandas as pd

from kudbee_quant.risk.session_sizer import (
    ASIA_MULT, LONDON_MULT, NY_MULT, OTHER_MULT, OVERLAP_MULT,
    session_risk_multiplier, sized_risk,
)


def _mult(hour):
    return session_risk_multiplier(f"2026-01-01T{hour:02d}:30:00+00:00")


def test_multipliers_by_session():
    assert _mult(14) == OVERLAP_MULT == 1.5      # London+NY overlap (13-16)
    assert _mult(18) == NY_MULT == 1.25          # NY (16-21)
    assert _mult(9) == LONDON_MULT == 1.25       # London (7-13)
    assert _mult(3) == ASIA_MULT == 0.75         # Asia (23-7)
    assert _mult(22) == OTHER_MULT == 1.0        # dead zone (21-23)


def test_overlap_takes_precedence():
    # 13-16 is inside BOTH London (7-16) and NY (13-21); overlap multiplier wins.
    assert _mult(15) == OVERLAP_MULT


def test_sized_risk_scales_and_clamps():
    assert abs(sized_risk(0.01, "2026-01-01T14:00:00+00:00") - 0.015) < 1e-12
    assert abs(sized_risk(0.01, "2026-01-01T03:00:00+00:00") - 0.0075) < 1e-12
    # clamp: 0.02 * 1.5 = 0.03 -> capped at default max_risk 0.02
    assert sized_risk(0.02, "2026-01-01T14:00:00+00:00") == 0.02


def test_unparseable_timestamp_is_neutral():
    assert session_risk_multiplier(None) == OTHER_MULT
    assert session_risk_multiplier("not-a-date") == OTHER_MULT


# --- paper_scan wiring -------------------------------------------------------

def _force_long_signal(monkeypatch, with_ts=False):
    import kudbee_quant.paper.paper as pp
    cols = {"close": [100.0], "atr": [1.0], "strength": [6.0],
            "direction": [1.0], "confluence_pct": [0.6]}
    if with_ts:
        cols["timestamp"] = pd.to_datetime(["2026-01-01T14:00:00+00:00"], utc=True)
    fake = pd.DataFrame(cols)
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake)
    return pp


class _C:
    def klines(self, *a, **k):
        return pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=1, freq="h", tz="UTC")})


def test_session_sizing_tags_book(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch, with_ts=True)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C(), session_sizing=True)
    assert len(logged) == 1
    assert "_ss" in logged[0].setup
    assert "session-sized risk" in logged[0].note


def test_session_sizing_off_byte_identical(tmp_path, monkeypatch):
    from kudbee_quant.journal import TradeJournal
    pp = _force_long_signal(monkeypatch, with_ts=True)
    j = TradeJournal(path=tmp_path / "j.json", client=_C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0,
                           journal=j, client=_C())     # session_sizing defaults off
    assert len(logged) == 1
    assert "_ss" not in logged[0].setup and "session-sized" not in logged[0].note
