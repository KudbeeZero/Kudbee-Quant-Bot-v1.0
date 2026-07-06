"""Tests for kudbee_quant/memory/registry.py — the L4 procedural-memory catalog.

MEMORY §86/CROSSROADS N6: a broken import of overnight_candidates.REGISTRY used
to be swallowed silently, leaving StrategyRegistry looking like a legitimately
thin catalog (baseline-only) rather than a broken one. It must now log loudly.
"""
from __future__ import annotations

import logging

import pytest

from kudbee_quant.memory.registry import Strategy, StrategyRegistry


def test_normal_construction_includes_candidates(tmp_path):
    reg = StrategyRegistry(results_path=tmp_path / "missing.json")
    assert reg.get("confluence_r_baseline") is not None
    # overnight_candidates.REGISTRY is real in this repo, so at least one
    # candidate strategy should be present alongside the seeded baseline.
    assert any(s.kind == "candidate" for s in reg.strategies.values())


def test_broken_registry_import_logs_loudly_not_silently(tmp_path, monkeypatch, caplog):
    """Force the overnight_candidates import to fail and verify the failure is
    LOUD (a warning naming the gap), not just a quietly-empty candidate set."""
    import builtins
    real_import = builtins.__import__

    def _boom(name, *a, **kw):
        if name == "overnight_candidates":
            raise ImportError("simulated broken import")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", _boom)
    with caplog.at_level(logging.WARNING):
        reg = StrategyRegistry(results_path=tmp_path / "missing.json")

    # Construction must not raise — still usable with just the baseline.
    assert reg.get("confluence_r_baseline") is not None
    assert not any(s.kind == "candidate" for s in reg.strategies.values())
    # But the gap must be visible in the log, not silent.
    assert any("overnight_candidates" in r.message and "MISSING" in r.message
              for r in caplog.records)


def test_verdicts_join_from_results_file(tmp_path):
    import json
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"results": [
        {"name": "clean_trend", "verdict": "WINNER", "delta": 0.02},
    ]}))
    reg = StrategyRegistry(results_path=results)
    s = reg.get("clean_trend")
    if s is not None:   # only present if clean_trend is a real REGISTRY entry
        assert s.verdict == "WINNER"
        assert s.status == "validated"
        assert s.delta_r == 0.02
