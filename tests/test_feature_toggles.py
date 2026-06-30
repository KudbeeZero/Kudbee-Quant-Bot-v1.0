"""Tests for the env-or-file feature toggles (powers Telegram /enable)."""
import pytest

from kudbee_quant.config import feature_toggles as ft


def test_default_off(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_SIGNAL_CARDS_ENABLED", raising=False)
    assert ft.is_enabled("signal_cards", path=str(tmp_path / "f.json")) is False


def test_env_wins(tmp_path, monkeypatch):
    path = str(tmp_path / "f.json")
    ft.set_flag("signal_cards", False, path=path)          # file says off
    monkeypatch.setenv("TELEGRAM_SIGNAL_CARDS_ENABLED", "true")
    assert ft.is_enabled("signal_cards", path=path) is True   # env overrides file


def test_env_false_overrides_file_true(tmp_path, monkeypatch):
    path = str(tmp_path / "f.json")
    ft.set_flag("signal_cards", True, path=path)
    monkeypatch.setenv("TELEGRAM_SIGNAL_CARDS_ENABLED", "off")
    assert ft.is_enabled("signal_cards", path=path) is False


def test_file_used_when_env_unset(tmp_path, monkeypatch):
    path = str(tmp_path / "f.json")
    monkeypatch.delenv("TELEGRAM_SIGNAL_CARDS_ENABLED", raising=False)
    ft.set_flag("signal_cards", True, path=path)
    assert ft.is_enabled("signal_cards", path=path) is True
    ft.set_flag("signal_cards", False, path=path)
    assert ft.is_enabled("signal_cards", path=path) is False


def test_set_flag_round_trips_all(tmp_path):
    path = str(tmp_path / "f.json")
    ft.set_flag("live_tracker", True, path=path)
    flags = ft.all_flags(path=path)
    assert flags["live_tracker"] is True
    assert flags["signal_cards"] is False        # untouched -> default off
    assert set(flags) == set(ft.KNOWN_FLAGS)


def test_unknown_flag_raises(tmp_path):
    with pytest.raises(KeyError):
        ft.set_flag("not_a_flag", True, path=str(tmp_path / "f.json"))


def test_corrupt_file_is_ignored(tmp_path, monkeypatch):
    p = tmp_path / "f.json"
    p.write_text("{not json")
    monkeypatch.delenv("TELEGRAM_SIGNAL_CARDS_ENABLED", raising=False)
    assert ft.is_enabled("signal_cards", path=str(p)) is False   # fail-open to default
