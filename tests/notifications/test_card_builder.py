"""Tests for the Signal Intelligence Card formatter + its default-off sender."""
import pandas as pd

import kudbee_quant.notifications.card_builder as cb
from kudbee_quant.notifications.card_builder import (
    SignalEvent, build_signal_card, confidence, notify_signal_card,
)


def _long(**kw):
    base = dict(symbol="BTCUSDT", direction=1.0, entry=64000.0, stop=63000.0,
                target=67000.0, tp1=65000.0, tp1_r=1.0, tp2_r=3.0,
                pvsra_label="Bull climax", pvsra_bull=True, inside_pdh_pdl=True,
                session_name="London", dxy_regime="RISK_ON", corr_ok=True,
                adr_pct=0.40, fp_winrate=0.72, fp_trades=12,
                gates_passed=6, gates_total=6)
    base.update(kw)
    return SignalEvent(**base)


# --- formatting --------------------------------------------------------------

def test_long_card_shape():
    card = build_signal_card(_long())
    assert card.startswith("🟢 <b>LONG SIGNAL — BTCUSDT</b>")
    assert "Entry:" in card and "<code>$64,000</code>" in card
    assert "Stop:" in card and "(−1.6%)" in card        # 1000/64000 = 1.56%
    assert "Target 1:" in card and "(+1.0R)" in card
    assert "Target 2:" in card and "(+3.0R)" in card
    assert "DXY regime: RISK_ON 🟢" in card
    assert "Correlation guard: clear ✅" in card
    assert "ADR consumed: 40% (room left)" in card
    assert "Fingerprint bucket: 72% win rate (12 trades)" in card
    assert "Signal confidence: <b>HIGH</b>" in card


def test_short_card_flips_emoji_and_side():
    card = build_signal_card(_long(direction=-1.0))
    assert card.startswith("🔴 <b>SHORT SIGNAL — BTCUSDT</b>")


def test_missing_context_renders_placeholders_not_errors():
    ev = SignalEvent(symbol="ETHUSDT", direction=1.0, entry=3000.0, stop=2950.0, target=3150.0)
    card = build_signal_card(ev)
    assert "ETHUSDT" in card
    assert "PVSRA: n/a" in card
    assert "DXY regime: unknown" in card
    assert "Fingerprint bucket: building" in card


def test_correlated_peer_shown_as_warning():
    card = build_signal_card(_long(corr_ok=False, corr_peer="ETHUSDT"))
    assert "Correlation guard: correlated (ETHUSDT) ⚠️" in card


def test_adr_stretched_above_threshold():
    card = build_signal_card(_long(adr_pct=0.90, adr_threshold=0.75))
    assert "ADR consumed: 90% (stretched)" in card


def test_malformed_event_falls_back_without_raising():
    # adr_pct as a string makes the "<" comparison raise inside the builder; the
    # builder must catch it and return a safe plain-text fallback (never raise).
    card = build_signal_card(_long(adr_pct="oops"))
    assert "BTCUSDT" in card
    assert "<b>" not in card        # fell back to plain text


# --- confidence tiers --------------------------------------------------------

def test_confidence_high():
    assert confidence(_long(fp_winrate=0.72, gates_passed=6)) == "HIGH"


def test_confidence_medium_on_one_warn():
    # Unknown win-rate + exactly one non-blocking gate warn -> MEDIUM (the one-warn path).
    assert confidence(_long(fp_winrate=None, fp_trades=None, gates_passed=5)) == "MEDIUM"


def test_confidence_weak_winrate_beats_one_warn():
    # A genuinely weak sample (<55%) downgrades to LOW even with only one warn.
    assert confidence(_long(fp_winrate=0.50, gates_passed=5)) == "LOW"


def test_confidence_medium_on_winrate():
    assert confidence(_long(fp_winrate=0.60, gates_passed=6)) == "MEDIUM"


def test_confidence_low_weak_winrate():
    assert confidence(_long(fp_winrate=0.40, gates_passed=6)) == "LOW"


def test_confidence_low_near_threshold_overrides():
    assert confidence(_long(fp_winrate=0.90, gates_passed=6, near_threshold=True)) == "LOW"


# --- sender (default-off) ----------------------------------------------------

def test_notify_off_by_default(monkeypatch):
    monkeypatch.delenv("TELEGRAM_SIGNAL_CARDS_ENABLED", raising=False)
    sent = {}
    monkeypatch.setattr(cb, "telegram_enabled", lambda: True)
    monkeypatch.setattr(cb, "send_telegram", lambda *a, **k: sent.setdefault("called", True))
    assert notify_signal_card(_long()) is False
    assert "called" not in sent          # flag off -> never sends


def test_notify_sends_html_when_enabled(monkeypatch):
    monkeypatch.setenv("TELEGRAM_SIGNAL_CARDS_ENABLED", "true")
    captured = {}

    def _fake_send(text, **kw):
        captured["text"] = text
        captured["parse_mode"] = kw.get("parse_mode")
        return True

    monkeypatch.setattr(cb, "telegram_enabled", lambda: True)
    monkeypatch.setattr(cb, "send_telegram", _fake_send)
    assert notify_signal_card(_long()) is True
    assert captured["parse_mode"] == "HTML"
    assert "LONG SIGNAL — BTCUSDT" in captured["text"]


# --- paper_scan take-site wiring ---------------------------------------------

def test_paper_scan_sends_card_when_enabled(tmp_path, monkeypatch):
    import kudbee_quant.paper.paper as pp
    from kudbee_quant.journal import TradeJournal
    fake = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake)
    sent = {}
    monkeypatch.setattr(cb, "signal_cards_enabled", lambda: True)
    monkeypatch.setattr(cb, "notify_signal_card", lambda ev: sent.update(ev=ev) or True)

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=1, freq="h", tz="UTC")})
    j = TradeJournal(path=tmp_path / "j.json", client=C())
    logged = pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0, journal=j, client=C())
    assert len(logged) == 1
    assert sent.get("ev") is not None and sent["ev"].symbol == "BTCUSDT"


def test_paper_scan_no_card_when_disabled(tmp_path, monkeypatch):
    import kudbee_quant.paper.paper as pp
    from kudbee_quant.journal import TradeJournal
    fake = pd.DataFrame({"close": [100.0], "atr": [1.0], "strength": [6.0],
                         "direction": [1.0], "confluence_pct": [0.6]})
    monkeypatch.setattr(pp, "build_levels", lambda df: df)
    monkeypatch.setattr(pp, "confluence_score", lambda df: fake)
    called = {"n": 0}
    monkeypatch.setattr(cb, "signal_cards_enabled", lambda: False)
    monkeypatch.setattr(cb, "notify_signal_card", lambda ev: called.__setitem__("n", called["n"] + 1))

    class C:
        def klines(self, *a, **k):
            return pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=1, freq="h", tz="UTC")})
    j = TradeJournal(path=tmp_path / "j.json", client=C())
    pp.paper_scan(["BTCUSDT"], min_pct=0.5, target_r=2.0, stop_atr=1.0, journal=j, client=C())
    assert called["n"] == 0
