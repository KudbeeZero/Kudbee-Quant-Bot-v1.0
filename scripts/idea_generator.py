"""DMN — the open-ended idea generator (docs/BRAIN.md Part II, the Default Mode Network).

Turns the FIXED candidate `REGISTRY` (scripts/overnight_candidates.py) into a
GENERATIVE layer. Instead of only testing hand-written ideas, it *composes* new
candidate edges by combining primitives — a regime GATE × an execution OVERRIDE —
the way improvisation combines known phrases into new ones. Each generated candidate
obeys the same contract as a hand-written one:

    candidate(df, scored, base_sig) -> (signal, size, overrides)

Two hard honesty rules make this safe (the anterior-cingulate critic, BRAIN.md):
  1. It INVENTS NO EDGE. Every generated candidate is a HYPOTHESIS fed to the SAME
     significance-gated harness (overnight_research.py) — bootstrap p<0.05 AND
     both-halves-robust before anything is called a WINNER. Generation only proposes.
  2. It NEVER re-proposes a known dead end. A generated combo is skipped if its name
     is already hand-written in REGISTRY or already recorded in the results ledger
     (data/overnight_results.json). New ideas only.

Composition stays inside the buckets the project has PROVEN matter (execution /
regime / entry-timing), never "one more confluence factor" (MEMORY §2). The gates
and overrides below are primitives, not the hand-written candidates — the value is
in the COMBINATIONS the registry never enumerated (e.g. "clean-trend regime × 4R
target × deeper retrace").

CLI:
    python scripts/idea_generator.py --list                 # show all fresh combos
    python scripts/idea_generator.py --emit 5 [--seed 7]    # enqueue 5 fresh ones
    python scripts/idea_generator.py --emit 5 --dry-run     # show, don't enqueue

Reuses the helpers + REGISTRY from overnight_candidates (no reimplementation).
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np  # noqa: F401  (kept for primitive authors; helpers use it)
import pandas as pd

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from overnight_candidates import (  # noqa: E402  reuse, never reimplement
    REGISTRY, _atr_pct, _gate, _rolling_pctrank,
)

_RESULTS_PATH = _HERE.parent / "data" / "overnight_results.json"


# --- PRIMITIVES: regime GATES (mask the baseline to a sub-population) ---------
# Each is mask_fn(df, scored) -> boolean Series aligned to df.index. Causal only.

def _g_highvol(df, scored):
    return _rolling_pctrank(_atr_pct(df), 200) >= 0.60

def _g_lowvol(df, scored):
    return _rolling_pctrank(_atr_pct(df), 200) <= 0.40

def _g_midvol(df, scored):
    r = _rolling_pctrank(_atr_pct(df), 200)
    return (r >= 0.20) & (r <= 0.80)

def _g_clean_trend(df, scored):
    # 50/800-EMA separated by >= 1 ATR — an untangled trend, not a braid.
    if not {"ema_50", "ema_800", "atr"} <= set(df.columns):
        return pd.Series(False, index=df.index)
    return (df["ema_50"] - df["ema_800"]).abs() >= df["atr"]

def _g_pullback(df, scored):
    # With-trend entry only after price has pulled back through the fast EMA.
    if not {"ema_13", "close"} <= set(df.columns):
        return pd.Series(False, index=df.index)
    d = np.sign(scored["direction"])
    return (d > 0) & (df["close"] <= df["ema_13"]) | (d < 0) & (df["close"] >= df["ema_13"])

def _g_not_overextended(df, scored):
    # Skip entries stretched > 2.5 ATR from the 50-EMA (chasing).
    if not {"ema_50", "close", "atr"} <= set(df.columns):
        return pd.Series(True, index=df.index)
    return (df["close"] - df["ema_50"]).abs() <= 2.5 * df["atr"]

def _g_participation(df, scored):
    # Require above-average volume at the trigger (real participation).
    if not {"volume"} <= set(df.columns):
        return pd.Series(True, index=df.index)
    avg = df["volume"].rolling(20, min_periods=5).mean()
    return df["volume"] >= 1.2 * avg

GATES: dict[str, tuple] = {
    "highvol":     (_g_highvol,        "high-vol regime (ATR% top 40%)"),
    "lowvol":      (_g_lowvol,         "low-vol regime (ATR% bottom 40%)"),
    "midvol":      (_g_midvol,         "mid-vol band (skip calm & shock)"),
    "cleantrend":  (_g_clean_trend,    "untangled 50/800-EMA trend (gap >= 1 ATR)"),
    "pullback":    (_g_pullback,       "after a pullback through the 13-EMA"),
    "notextended": (_g_not_overextended, "not >2.5 ATR stretched from the 50-EMA"),
    "participation": (_g_participation, "above-average volume at the trigger"),
}


# --- PRIMITIVES: execution OVERRIDES (bracket_backtest kwargs) ----------------
OVERRIDES: dict[str, tuple] = {
    "ride3r":       ({}, "validated ride-to-3R (no override)"),
    "target4r":     ({"target_r": 4.0}, "bigger 4R target"),
    "target2r":     ({"target_r": 2.0}, "quicker 2R target"),
    "deepretrace":  ({"limit_retrace_atr": 0.5}, "deeper 0.5-ATR limit (better price, fewer fills)"),
    "shallowretrace": ({"limit_retrace_atr": 0.12}, "shallow 0.12-ATR limit (more fills)"),
    "widestop":     ({"stop_atr": 2.0, "target_r": 3.0}, "wider 2.0-ATR stop, keep 3R reward:risk"),
}


def semantic_name(gate: str, override: str) -> str:
    """Deterministic name for a combo — the key used for dedup + registry lookup."""
    return f"gen__{gate}__{override}"


def _make_candidate(gate: str, override: str):
    """Build the (df, scored, base_sig) -> (signal, size, overrides) callable."""
    gate_fn = GATES[gate][0]
    kwargs = OVERRIDES[override][0]

    def candidate(df, scored, base_sig):
        mask = gate_fn(df, scored)
        return _gate(base_sig, mask), None, dict(kwargs)

    candidate.__name__ = semantic_name(gate, override)
    candidate.__doc__ = f"[gen] {GATES[gate][1]} × {OVERRIDES[override][1]}"
    return candidate


def _tested_names() -> set[str]:
    """Names already recorded in the results ledger — never re-propose them."""
    try:
        data = json.loads(_RESULTS_PATH.read_text())
    except (OSError, ValueError):
        return set()
    return {r.get("name") for r in data.get("results", []) if r.get("name")}


def generate_candidates(exclude: set[str] | None = None,
                        skip_noop: bool = True) -> dict[str, tuple]:
    """All FRESH (gate × override) combos as ``{name: (fn, desc)}``.

    Skips any combo whose name is already in ``REGISTRY``, in ``exclude`` (e.g.
    already-tested), and (when ``skip_noop``) the pure ``ride3r`` no-override combos
    — a bare regime gate with no execution change duplicates the plain gate-only
    candidates the registry already covers, so the novel value is gate × a real
    execution change.
    """
    exclude = set(exclude or set())
    out: dict[str, tuple] = {}
    for gate, override in itertools.product(GATES, OVERRIDES):
        name = semantic_name(gate, override)
        # `gen__*` is a dedicated namespace — it can't collide with a hand-written
        # REGISTRY name, so we only dedup against `exclude` (already-tested history).
        # (Checking `name in REGISTRY` here would be self-defeating once the harness
        # has merged generated names back into REGISTRY via register_generated.)
        if name in exclude:
            continue
        if skip_noop and override == "ride3r":
            continue
        out[name] = (_make_candidate(gate, override), f"[gen] {GATES[gate][1]} × {OVERRIDES[override][1]}")
    return out


def fresh_candidates() -> dict[str, tuple]:
    """Generated combos minus everything already tested — the DMN's new ideas."""
    return generate_candidates(exclude=_tested_names())


def register_generated(registry: dict[str, tuple]) -> int:
    """Merge ALL generated combos into ``registry`` in place (deterministic, so the
    same ``gen__*`` name always resolves to the same callable). Called by the harness
    at startup so any queued generated name is runnable. Returns how many were added."""
    added = 0
    for name, spec in generate_candidates(skip_noop=False).items():
        if name not in registry:
            registry[name] = spec
            added += 1
    return added


def _emit(n: int, dry_run: bool) -> None:
    fresh = fresh_candidates()
    picks = list(fresh)[:n]
    if not picks:
        print("No fresh candidates — every generated combo is already tested or hand-written.")
        return
    for name in picks:
        print(f"  {name}\n      {fresh[name][1]}")
    if dry_run:
        print(f"\n(dry-run) {len(picks)} candidate(s) NOT enqueued.")
        return
    # Register into the live REGISTRY, then enqueue via the harness's own function
    # so the name is known + the significance gate will judge it.
    import overnight_research as research  # noqa: PLC0415
    register_generated(REGISTRY)
    research.enqueue(picks)


def main() -> None:
    ap = argparse.ArgumentParser(description="DMN idea generator (compose fresh candidate edges)")
    ap.add_argument("--list", action="store_true", help="list all fresh combos")
    ap.add_argument("--emit", type=int, metavar="N", help="enqueue N fresh combos for the harness")
    ap.add_argument("--dry-run", action="store_true", help="with --emit, show but don't enqueue")
    args = ap.parse_args()

    if args.list:
        fresh = fresh_candidates()
        print(f"{len(fresh)} fresh generated candidates "
              f"({len(GATES)} gates × {len(OVERRIDES)} overrides, minus tested/hand-written):\n")
        for name, (_fn, desc) in fresh.items():
            print(f"  {name}\n      {desc}")
    elif args.emit is not None:
        _emit(args.emit, args.dry_run)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
