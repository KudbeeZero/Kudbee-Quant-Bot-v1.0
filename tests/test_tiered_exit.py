"""Tests for the tiered exit: resolver runner-trailing, config, momentum, compare."""
import numpy as np
import pandas as pd
import pytest

from kudbee_quant.backtest.resolver import resolve_bracket
from kudbee_quant.backtest.tiered_compare import compare_exit_configs, run_all_configs
from kudbee_quant.execution.tiered_exit import (
    TieredExitConfig, dynamic_tp2_r, resolver_kwargs,
    TieredPosition, get_stage, current_r, unrealized_r_locked,
)
from kudbee_quant.signals.momentum_score import (
    momentum_score, volume_momentum, trend_alignment, sr_clearance,
)

TIER = dict(tp1=101, tp1_r=1.0, tp1_frac=0.40, be_after_tp1=True,
            tp2=102, tp2_r=2.0, tp2_frac=0.35,
            runner_trail_atr=1.5, atr_at_entry=1.0, runner_floor_r=1.0, runner_max_bars=48)


def test_runner_trails_out_above_floor():
    H = [101.2, 102.2, 104.0, 104.5, 104.0]
    L = [100.0, 101.0, 103.0, 102.6, 102.9]
    C = [101.0, 102.0, 103.8, 103.0, 103.0]
    out = resolve_bracket(1, 100, 99, 110, 1.0, 10.0, H, L, C, **TIER)
    assert out.outcome_r == pytest.approx(1.85)
    assert out.tp1_offset == 0 and out.tp2_offset == 1
    assert out.runner_r == pytest.approx(0.75)


def test_runner_holds_1r_floor_on_immediate_reversal():
    H = [101.2, 102.2, 101.5]; L = [100.0, 101.0, 100.5]; C = [101.0, 102.0, 100.8]
    out = resolve_bracket(1, 100, 99, 110, 1.0, 10.0, H, L, C, **TIER)
    assert out.outcome_r == pytest.approx(1.35)
    assert out.runner_r == pytest.approx(0.25)


def test_runner_max_bars_force_close():
    cfg = dict(TIER); cfg["runner_max_bars"] = 1
    H = [101.2, 102.2, 103.0, 103.0]; L = [100.0, 101.0, 102.0, 102.0]
    C = [101.0, 102.0, 102.5, 102.5]
    out = resolve_bracket(1, 100, 99, 110, 1.0, 10.0, H, L, C, **cfg)
    assert out.exited and out.runner_r is not None


def test_legacy_tp2_unchanged_without_runner():
    H = [101.6, 102.6, 103.1]; L = [100, 101.5, 102.5]; C = [101.5, 102.5, 103.0]
    out = resolve_bracket(1, 100, 99, 103, 1.0, 3.0, H, L, C,
                          tp1=101.5, tp1_r=1.5, tp1_frac=0.75, be_after_tp1=True,
                          tp2=102.5, tp2_r=2.5, tp2_frac=0.10)
    assert out.outcome_r == pytest.approx(1.825)   # blended R unchanged (backward compat)
    # remainder after TP1(0.75)+TP2(0.10)=0.15 rides to 3R target -> runner_r 0.45
    assert out.runner_r == pytest.approx(0.45)


def test_short_runner_symmetry():
    L = [98.8, 97.8, 96.0, 95.5, 96.0]; H = [100.0, 99.0, 97.0, 97.4, 97.1]
    C = [99.0, 98.0, 96.2, 97.0, 97.0]
    out = resolve_bracket(-1, 100, 101, 90, 1.0, 10.0, H, L, C,
                          tp1=99, tp1_r=1.0, tp1_frac=0.40, be_after_tp1=True,
                          tp2=98, tp2_r=2.0, tp2_frac=0.35,
                          runner_trail_atr=1.5, atr_at_entry=1.0, runner_floor_r=1.0)
    assert out.outcome_r == pytest.approx(1.85)


def test_config_sizes_must_sum_to_one():
    with pytest.raises(ValueError):
        TieredExitConfig(tp1_size_pct=0.5, tp2_size_pct=0.4, runner_pct=0.3)
    TieredExitConfig()


def test_dynamic_tp2_mapping():
    c = TieredExitConfig()
    assert dynamic_tp2_r(0.80, c) == 3.0
    assert dynamic_tp2_r(0.50, c) == 2.0
    assert dynamic_tp2_r(0.20, c) == 1.5


def test_resolver_kwargs_dynamic_applies():
    c = TieredExitConfig()
    assert resolver_kwargs(c, momentum=0.9)["tp2_r"] == 3.0
    assert resolver_kwargs(c, momentum=0.1)["tp2_r"] == 1.5
    assert resolver_kwargs(c)["tp2_r"] == 2.0


def test_stage_and_locked_r():
    c = TieredExitConfig()
    pos = TieredPosition(entry=100, stop=99, direction=1, config=c)
    assert get_stage(pos) == "entry_to_tp1"
    assert unrealized_r_locked(pos) == 0.0
    pos.tp1_filled = True
    assert get_stage(pos) == "tp1_to_tp2"
    assert unrealized_r_locked(pos) == pytest.approx(0.40)
    pos.tp2_filled = True
    assert get_stage(pos) == "runner"
    assert unrealized_r_locked(pos) == pytest.approx(1.35)
    assert current_r(pos, 103.0) == pytest.approx(3.0)


def _df(n=80, vol=1000.0):
    px = pd.Series(np.linspace(100, 120, n))
    return pd.DataFrame({"open": px, "high": px + 0.3, "low": px - 0.3,
                         "close": px, "volume": [vol] * n, "atr": [1.0] * n})


def test_trend_alignment_long_uptrend():
    df = _df()
    assert trend_alignment(df, len(df) - 1, 1.0) == 1.0
    assert trend_alignment(df, len(df) - 1, -1.0) == 0.0


def test_volume_momentum_buckets():
    df = _df()
    df.loc[df.index[-1], "volume"] = 3000.0
    assert volume_momentum(df, len(df) - 1) == 1.0


def test_sr_clearance_no_levels_is_clear():
    df = _df()
    assert sr_clearance(df, len(df) - 1, 1.0, sd=1.0) == 1.0


def test_momentum_score_in_unit_range():
    df = _df()
    s = momentum_score(df, len(df) - 1, 1.0)
    assert 0.0 <= s <= 1.0


def _trend_df(n=600, seed=1):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0008, 0.009, n)))
    df = pd.DataFrame({"open": close, "high": close * 1.004, "low": close * 0.996,
                       "close": close, "volume": rng.uniform(900, 1100, n)})
    df["atr"] = (df["high"] - df["low"]).rolling(14, min_periods=1).mean()
    return df


def test_compare_returns_all_five_configs():
    df = _trend_df()
    sig = pd.Series(0.0, index=df.index); sig.iloc[::20] = 1.0
    res = compare_exit_configs(df, sig)
    assert set(res["configs"]) == {"A_flat_1R", "B_flat_2R", "C_flat_3R",
                                   "D_tiered_static", "E_tiered_dynamic"}
    for s in res["configs"].values():
        assert s["n_trades"] > 0
    assert res["configs"]["D_tiered_static"]["avg_runner_contribution_r"] != 0.0
    assert res["configs"]["A_flat_1R"]["avg_runner_contribution_r"] == 0.0


def test_aggregation_concatenates_trades():
    df = _trend_df()
    sig = pd.Series(0.0, index=df.index); sig.iloc[::20] = 1.0
    one = run_all_configs(df, sig)
    assert len(one["B_flat_2R"]) > 0
