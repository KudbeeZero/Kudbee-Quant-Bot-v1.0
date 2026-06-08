"""On-disk cache for fetched market data.

Caching is honest: every cached frame records the wall-clock time it was
fetched, so downstream code can tell fresh data from stale, and we never
serve stale data past its TTL.

Security: cache keys are hashed (SHA-256) to derive filenames, so no
attacker-influenced symbol/source string can traverse the filesystem
(``../``) or collide outside the cache root. Every resolved write path is
verified to live inside the cache root before use.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pandas as pd

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "kudbee_quant"


class DataCache:
    def __init__(self, root: Path | str = DEFAULT_CACHE_DIR):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _paths(self, key: str) -> tuple[Path, Path]:
        # Hash the key so the filename is a fixed, safe hex string regardless
        # of what the key contains. Defeats path traversal and weird chars.
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        data_path = (self.root / f"{digest}.parquet").resolve()
        meta_path = (self.root / f"{digest}.meta.json").resolve()
        # Defense in depth: ensure the resolved paths stay within the root.
        for p in (data_path, meta_path):
            if self.root not in p.parents:
                raise ValueError(f"cache path escapes root: {p}")
        return data_path, meta_path

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
        meta_path.write_text(json.dumps({"fetched_at": time.time(), "rows": len(df), "key": key}))
