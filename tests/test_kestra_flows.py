"""Validate the Kestra flow YAMLs (syntax + required keys).

These flows are a PLAN/SCAFFOLD (no Kestra runtime is stood up — see
docs/KESTRA_AUTOMATION.md). This test just guarantees they are well-formed so they
won't silently rot.
"""
from pathlib import Path

import pytest
import yaml

FLOWS_DIR = Path(__file__).resolve().parents[1] / "flows"
FLOW_FILES = sorted(FLOWS_DIR.glob("*.yaml"))


def test_flows_directory_has_the_expected_set():
    names = {p.stem for p in FLOW_FILES}
    assert {"hourly_top100_scan", "paper_trade_cycle", "open_trades_review",
            "daily_trade_history", "health_check"} <= names


@pytest.mark.parametrize("path", FLOW_FILES, ids=lambda p: p.stem)
def test_flow_is_valid(path):
    flow = yaml.safe_load(path.read_text())
    assert isinstance(flow, dict), f"{path.name} is not a mapping"
    for key in ("id", "namespace", "tasks"):
        assert key in flow, f"{path.name} missing '{key}'"
    assert flow["id"] == path.stem, f"{path.name} id should match filename"
    assert isinstance(flow["tasks"], list) and flow["tasks"], f"{path.name} has no tasks"
    for t in flow["tasks"]:
        assert "id" in t and "type" in t, f"{path.name} task missing id/type"


@pytest.mark.parametrize("path", FLOW_FILES, ids=lambda p: p.stem)
def test_flow_never_enables_live(path):
    """Safety: no flow may turn live execution on."""
    text = path.read_text()
    assert "ENABLE_LIVE_EXECUTION: \"true\"" not in text
    assert "TRADING_MODE: live" not in text
