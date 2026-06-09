"""L4 — Procedural memory: strategies & candidate edges as first-class, versioned
objects, joined to their tested verdict.

Until now a "strategy" lived implicitly in code (the validated baseline) and the
candidate filters lived in ``scripts/overnight_candidates.py``. This layer makes
them addressable: each entry knows its name, description, provenance, and its
latest honest verdict from the experiment log (L3) — so "what do we actually
have?" is one query, not tribal knowledge.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

RESULTS_PATH = Path("data/overnight_results.json")


@dataclass
class Strategy:
    name: str
    kind: str                       # "baseline" | "candidate"
    description: str = ""
    provenance: str = ""            # where it came from (agent, manual, paper, …)
    verdict: str | None = None      # latest L3 verdict (WINNER/HURTS/…)
    delta_r: float | None = None    # expectancy edge vs baseline, if measured
    status: str = "research"        # research | validated | shipped | dead

    def to_dict(self) -> dict:
        return asdict(self)


class StrategyRegistry:
    """Catalog of the shipping baseline + every candidate edge, with verdicts."""

    def __init__(self, results_path: Path | str = RESULTS_PATH):
        self.results_path = Path(results_path)
        self._verdicts = self._load_verdicts()
        self.strategies: dict[str, Strategy] = {}
        self._seed()

    def _load_verdicts(self) -> dict:
        if not self.results_path.exists():
            return {}
        data = json.loads(self.results_path.read_text())
        return {r["name"]: r for r in data.get("results", [])}   # latest per name

    def _seed(self):
        # The shipping baseline (docs/MEMORY.md §1) — the thing everything beats.
        self.register(Strategy(
            name="confluence_r_baseline", kind="baseline", status="shipped",
            provenance="validated walk-forward (MEMORY §1)",
            description="1h, >=50% confluence + 800-EMA trend filter, 0.25-ATR limit "
                        "retrace (maker), 1.5-ATR stop, 3R target, both sides."))
        # Candidate edges from the procedural store, joined to their verdicts.
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
            from overnight_candidates import REGISTRY  # type: ignore
        except Exception:
            REGISTRY = {}
        for name, (_fn, desc) in REGISTRY.items():
            v = self._verdicts.get(name, {})
            verdict = v.get("verdict")
            status = {"WINNER": "validated", "HURTS": "dead"}.get(verdict, "research")
            self.register(Strategy(name=name, kind="candidate", description=desc,
                                   provenance="overnight research", verdict=verdict,
                                   delta_r=v.get("delta"), status=status))

    def register(self, s: Strategy) -> None:
        self.strategies[s.name] = s

    def get(self, name: str) -> Strategy | None:
        return self.strategies.get(name)

    def validated(self) -> list[Strategy]:
        """Candidates that beat baseline (naive WINNER). Cross-check against the
        multiple-testing ledger before trusting (memory/testing_ledger.py)."""
        return [s for s in self.strategies.values() if s.verdict == "WINNER"]

    def by_status(self, status: str) -> list[Strategy]:
        return [s for s in self.strategies.values() if s.status == status]

    def to_json(self) -> str:
        return json.dumps([s.to_dict() for s in self.strategies.values()], indent=2)
