"""Causality guard for the MTF backtest's 30m->15m merge: a 15m decision on a
30m boundary must use the PRIOR CLOSED 30m bar's bias, never the forming one."""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from mtf_backtest import causal_bias_merge  # noqa: E402

UTC = "UTC"


def _ts(s):
    return pd.Timestamp(s, tz=UTC)


def test_forming_30m_bar_does_not_leak():
    # Two 30m bars: A [00:00,00:30) bias +1 (closes 00:30); B [00:30,01:00) bias -1
    # (closes 01:00 — the FORMING bar during 00:30..01:00).
    df30 = pd.DataFrame({
        "timestamp": [_ts("2026-01-01 00:00"), _ts("2026-01-01 00:30")],
        "bias30": [1.0, -1.0],
    })
    # 15m bars on the boundary. The bar at 00:30 decides at 00:45 — bar B is still
    # forming (closes 01:00), so its bias must be A's (+1), NOT B's (-1).
    lv15 = pd.DataFrame({
        "timestamp": [_ts("2026-01-01 00:15"),   # decides 00:30 -> only A's bar OPEN, A not closed yet -> 0/none
                      _ts("2026-01-01 00:30"),    # decides 00:45 -> A closed (00:30), B forming -> +1
                      _ts("2026-01-01 00:45"),    # decides 01:00 -> A closed; B closes exactly 01:00 -> -1
                      _ts("2026-01-01 01:00")],   # decides 01:15 -> B closed -> -1
        "close": [10.0, 11.0, 12.0, 13.0],
    })
    out = causal_bias_merge(lv15, df30).sort_values("timestamp").reset_index(drop=True)
    bias = out["bias30"].tolist()

    # Boundary bar (00:30, decides 00:45): MUST be the prior closed 30m bar A (+1),
    # never the forming bar B (-1).
    assert bias[1] == 1.0, f"forming-bar leak: expected +1 (prior closed A), got {bias[1]}"
    # 00:15 decides 00:30: A (00:00-00:30) closes exactly at 00:30 -> available -> +1
    assert bias[0] == 1.0
    # 00:45 decides 01:00: B closes exactly at 01:00 -> now available -> -1
    assert bias[2] == -1.0
    assert bias[3] == -1.0


def test_no_30m_history_is_flat_not_error():
    df30 = pd.DataFrame({"timestamp": [_ts("2026-01-01 12:00")], "bias30": [1.0]})
    lv15 = pd.DataFrame({"timestamp": [_ts("2026-01-01 00:00")], "close": [10.0]})
    # 15m decision precedes any closed 30m bar -> bias 0, no crash.
    out = causal_bias_merge(lv15, df30)
    assert out["bias30"].iloc[0] == 0.0


def test_forming_4h_bar_does_not_leak_2h():
    # 2h entry / 4h bias. Two 4h bars: A [00:00,04:00) bias +1 (closes 04:00);
    # B [04:00,08:00) bias -1 (closes 08:00 — forming during 04:00..08:00).
    df4h = pd.DataFrame({
        "timestamp": [_ts("2026-01-01 00:00"), _ts("2026-01-01 04:00")],
        "bias30": [1.0, -1.0],
    })
    # 2h bars on the boundary. The bar at 04:00 decides at 06:00 — bar B is still
    # forming (closes 08:00), so its bias must be A's (+1), NOT B's (-1).
    lv2h = pd.DataFrame({
        "timestamp": [_ts("2026-01-01 02:00"),   # decides 04:00 -> A closes exactly 04:00 -> +1
                      _ts("2026-01-01 04:00"),    # decides 06:00 -> A closed; B forming -> +1
                      _ts("2026-01-01 06:00")],   # decides 08:00 -> B closes exactly 08:00 -> -1
        "close": [10.0, 11.0, 12.0],
    })
    out = causal_bias_merge(lv2h, df4h, entry_minutes=120, bias_minutes=240)
    out = out.sort_values("timestamp").reset_index(drop=True)
    bias = out["bias30"].tolist()
    assert bias[1] == 1.0, f"forming 4h-bar leak: expected +1 (prior closed A), got {bias[1]}"
    assert bias[0] == 1.0
    assert bias[2] == -1.0
