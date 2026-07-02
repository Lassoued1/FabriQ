from __future__ import annotations

import threading
import time
from typing import Any


class TTLCache:
    """Thread-safe in-memory cache with per-entry TTL.

    Entries expire silently on read — no background eviction thread needed.
    All operations are O(1) amortized.
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self.ttl = ttl_seconds

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic() + self.ttl)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._store)


# Shared cache instance — 5 minute TTL for SQL result sets.
sql_result_cache = TTLCache(ttl_seconds=300)
