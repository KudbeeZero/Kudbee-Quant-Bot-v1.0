"""The 6-layer memory architecture — the project's durable, self-checking spine.

The remote container is ephemeral; what survives is git-versioned memory. This
package formalizes SIX layers, most of which already existed informally, plus the
two that make the whole thing trustworthy (reflective + multiple-testing):

  L1  Semantic    — validated lessons & thesis.        docs/MEMORY.md (manual)
  L2  Episodic    — every trade + outcome.             data/journal.json (journal/)
  L3  Experiment  — every hypothesis + verdict.        data/overnight_results.json
  L4  Procedural  — strategies/candidates as objects.  memory/registry.py
  L5  Working     — current biases + open questions.   memory/working.py
  L6  Reflective  — self-critique: regime, overfit     memory/reflection.py
                    alarms, "what kinds of ideas fail" + the multiple-testing
                    ledger (memory/testing_ledger.py) that re-grades "winners"
                    under the multiplicity of everything we've ever tried.

The thesis (docs/MEMORY.md): the rules are commodity — the edge is in the
reasoning and the execution. L6 exists so we never mistake luck for edge.
"""
from .registry import Strategy, StrategyRegistry
from .testing_ledger import family_ledger
from .working import WorkingMemory

__all__ = ["Strategy", "StrategyRegistry", "WorkingMemory", "family_ledger"]
