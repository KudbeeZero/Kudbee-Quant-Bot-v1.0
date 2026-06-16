"""Chart-review record storage — flat JSON, mirroring journal/journal.py.

Each record is one AI read of an uploaded chart image. Storage is append-only
with an atomic full-file rewrite (same pattern as :class:`TradeJournal`). The raw
image bytes are NEVER stored here — only a sha256 hash, the byte size, and a
relative path to the image file on disk. This module has no dependency on the
execution layer: a chart review can never place an order.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path("data/chart_reviews.json")


@dataclass
class ChartReview:
    symbol: str
    timeframe: str = ""
    image_path: str = ""          # relative path to the stored image file
    image_sha256: str = ""        # "sha256:<hex>" of the raw bytes (bytes NOT stored)
    image_size_bytes: int = 0
    ai_model_used: str = ""
    ai_review_json: dict = field(default_factory=dict)  # the validated structured read
    bias: str = ""                # denormalized from ai_review_json for quick listing
    setup_name: str = ""
    confidence: int = 0
    final_recommendation: str = ""
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


class ChartReviewJournal:
    def __init__(self, path: Path | str = DEFAULT_PATH):
        self.path = Path(path)
        self.reviews: list[ChartReview] = []
        self._load()

    def _load(self):
        if self.path.exists():
            self.reviews = [ChartReview(**d) for d in json.loads(self.path.read_text())]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(r) for r in self.reviews], indent=2))

    def add(self, review: ChartReview) -> ChartReview:
        self.reviews.append(review)
        self.save()
        return review

    def get(self, review_id: str) -> ChartReview | None:
        for r in self.reviews:
            if r.id == review_id:
                return r
        return None

    def recent(self, n: int = 50) -> list[ChartReview]:
        """The newest ``n`` reviews, newest first."""
        return list(reversed(self.reviews[-n:]))
