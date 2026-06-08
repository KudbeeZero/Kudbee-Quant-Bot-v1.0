"""On-disk cache for fetched market data.

Caching is honest: every cached frame carries the wall-clock time it was
fetched (``_fetched_at`` attr in the sidecar meta) so downstream code can
tell fresh data from stale. We never silently serve stale data past TTL.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "kudbee_quant"


class DataCache:
    def __init__(self, root: Path | str = DEFAULT_CACHE_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _paths(self, key: str) -> tuple[Path, Path]:
        safe = key.replace("/", "_").replace(":", "_")
        return self.root / f"{safe}.parquet", self.root / f"{safe}.meta.json"

    def get(self, key: str, ttl_seconds: float) -> pd.DataFrame | None:
        data_path, meta_path = self._paths(key)
        if not (data_path.exists() and meta_path.exists()):
            return None
        meta = json.loads(meta_path.read_text())
        age = time.time() - meta.get("fetched_at", 0)
        if age > ttl_seconds:
            return None  # stale — force a refetch rather than lie about freshness
        return pd.read_parquet(data_path)

    def put(self, key: str, df: pd.DataFrame) -> None:
        data_path, meta_path = self._paths(key)
        df.to_parquet(data_path, index=False)
        meta_path.write_text(json.dumps({"fetched_at": time.time(), "rows": len(df)}))
