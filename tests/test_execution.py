"""Runtime-config + execution gating tests — the live-safety guarantees (no network)."""
import pytest

from kudbee_quant.config.runtime import (
    LiveExecutionBlocked,
    load_runtime_config,
    require_live_enabled,
)
from kudbee_quant.execution import PaperExecutor, build_executor
from kudbee_quant.execution.base import STRATEGY_VERSION
from kudbee_quant.execution.live import LiveExecutor
from kudbee_quant.journal import Prediction, TradeJournal

from test_journal import _FakeClient   # reuse the no-network OHLCV fake


_LIVE_ENV = {"TRADING_MODE": "live", "ENABLE_LIVE_EXECUTION": "true"}


def _bracket(symbol="BTCUSDT"):
    return Prediction(symbol=symbol, kind="bracket", level=100.0, deadline_days=7,
                      entry=100.0, stop=99.0, target=103.0, direction=1.0, target_r=3.0)

def _journal(tmp_path):
    return TradeJournal(path=tmp_path / "j.json", client=_FakeClient())


# --- runtime config defaults ------------------------------------------------

def test_default_config_is_paper_and_not_live():
    cfg = load_runtime_config(env={})
    assert cfg.trading_mode == "paper"
    assert cfg.enable_live_execution is False
    assert cfg.is_live is False

def test_invalid_mode_fails_safe():
    with pytest.raises(ValueError):
        load_runtime_config(env={"TRADING_MODE": "yolo"})

def test_is_live_requires_both_flags():
    assert load_runtime_config(env={"TRADING_MODE": "live"}).is_live is False
    assert load_runtime_config(env={"ENABLE_LIVE_EXECUTION": "true"}).is_live is False
    assert load_runtime_config(env=_LIVE_ENV).is_live is True


# --- the guard --------------------------------------------------------------

def test_require_live_enabled_blocks_by_default():
    with pytest.raises(LiveExecutionBlocked):
        require_live_enabled(load_runtime_config(env={}))

def test_require_live_enabled_blocks_with_one_flag():
    with pytest.raises(LiveExecutionBlocked):
        require_live_enabled(load_runtime_config(env={"TRADING_MODE": "live"}))

def test_require_live_enabled_passes_when_fully_enabled():
    cfg = require_live_enabled(load_runtime_config(env=_LIVE_ENV))
    assert cfg.is_live is True


# --- executor selection -----------------------------------------------------

def test_build_executor_defaults_to_paper(tmp_path):
    ex = build_executor(load_runtime_config(env={}), journal=_journal(tmp_path))
    assert isinstance(ex, PaperExecutor) and ex.mode == "paper"

def test_live_executor_cannot_even_construct_by_default():
    with pytest.raises(LiveExecutionBlocked):
        LiveExecutor(load_runtime_config(env={}))

def test_live_executor_constructs_when_enabled_without_touching_network(tmp_path):
    # Both flags set -> it constructs (broker built lazily; no network at __init__).
    ex = LiveExecutor(load_runtime_config(env=_LIVE_ENV), journal=_journal(tmp_path))
    assert ex.mode == "live"

def test_live_submit_without_credentials_is_safely_rejected(tmp_path, monkeypatch):
    # No API keys -> the broker raises before any network call; submit returns a
    # clean rejection (NOT an order, NOT an unhandled crash).
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    j = _journal(tmp_path)
    ex = LiveExecutor(load_runtime_config(env=_LIVE_ENV), journal=j)
    res = ex.submit(_bracket())
    assert res.accepted is False and "credential" in res.reason
    assert len(j.predictions) == 0


# --- paper executor records trades -----------------------------------------

def test_paper_executor_records_a_paper_trade(tmp_path):
    j = _journal(tmp_path)
    ex = PaperExecutor(journal=j)
    res = ex.submit(_bracket())
    assert res.accepted and res.mode == "paper"
    assert res.prediction.mode == "paper"
    assert res.prediction.strategy_version == STRATEGY_VERSION
    assert len(j.predictions) == 1

def test_paper_executor_honours_max_concurrent(tmp_path):
    j = _journal(tmp_path)
    ex = PaperExecutor(journal=j, max_concurrent_positions=1)
    assert ex.submit(_bracket("BTCUSDT")).accepted is True
    blocked = ex.submit(_bracket("ETHUSDT"))
    assert blocked.accepted is False and "max_concurrent" in blocked.reason
    assert len(j.predictions) == 1
