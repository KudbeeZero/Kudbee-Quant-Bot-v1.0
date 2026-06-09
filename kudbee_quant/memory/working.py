"""L5 — Working / directional memory: the live context a decision needs right now.

Pulls together the two short-horizon stores that change day to day:
  * directional biases (data/biases.json via BiasBook) — the human's current reads
    that the bot scalps WITH (docs/MEMORY.md §0).
  * the open-hypothesis queue (data/overnight_queue.json) — what research is still
    pending vs done.

It's a read-only convenience snapshot; the authoritative stores stay where they
are. This is the layer an agent (or a person) checks to answer "what are we
leaning on, and what's still in flight?".
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..bias import BiasBook

QUEUE_PATH = Path("data/overnight_queue.json")


class WorkingMemory:
    def __init__(self, biases_path: Path | str | None = None,
                 queue_path: Path | str = QUEUE_PATH):
        self.biases = BiasBook() if biases_path is None else BiasBook(biases_path)
        self.queue_path = Path(queue_path)

    def open_hypotheses(self) -> dict:
        if not self.queue_path.exists():
            return {"pending": [], "done": []}
        return json.loads(self.queue_path.read_text())

    def active_biases(self) -> list[dict]:
        """Current, non-expired directional reads (list of Bias dataclasses)."""
        return [asdict(b) for b in self.biases.biases if getattr(b, "active", True)]

    def snapshot(self) -> dict:
        q = self.open_hypotheses()
        return {
            "active_biases": self.active_biases(),
            "pending_hypotheses": q.get("pending", []),
            "n_pending": len(q.get("pending", [])),
            "n_done": len(q.get("done", [])),
        }
