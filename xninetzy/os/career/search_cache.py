from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from typing import Any


DEFAULT_TTL_SECONDS = {
    "remoteok": 1800,
    "arbeitnow": 1800,
    "kalibrr": 300,
    "glints": 300,
    "dealls": 300,
    "jobstreet_id": 60,
}
DEFAULT_TTL_FALLBACK = 900


@dataclass
class CacheEntry:
    key: str
    adapter_id: str
    value: Any
    stored_at: float
    expires_at: float
    hits: int = 0


@dataclass
class CacheStats:
    size: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    stores: int = 0


class SearchCache:
    def __init__(self, *, max_entries: int = 256, ttl_overrides: dict[str, int] | None = None) -> None:
        self._max_entries = max(1, max_entries)
        self._ttl = {**DEFAULT_TTL_SECONDS, **(ttl_overrides or {})}
        self._store: dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._lock = threading.Lock()

    def ttl_for(self, adapter_id: str) -> int:
        return self._ttl.get(adapter_id, DEFAULT_TTL_FALLBACK)

    def make_key(self, *, adapter_id: str, query: str, country: str, work_mode: str) -> str:
        payload = json.dumps(
            {"a": adapter_id, "q": query.strip().lower(), "c": country.strip().lower(), "m": work_mode.strip().lower()},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            if entry.expires_at <= now:
                self._store.pop(key, None)
                self._stats.misses += 1
                self._stats.evictions += 1
                self._stats.size = len(self._store)
                return None
            entry.hits += 1
            self._stats.hits += 1
            return entry.value

    def put(self, *, key: str, adapter_id: str, value: Any) -> None:
        now = time.monotonic()
        ttl = self.ttl_for(adapter_id)
        with self._lock:
            self._evict_if_full()
            self._store[key] = CacheEntry(
                key=key,
                adapter_id=adapter_id,
                value=value,
                stored_at=now,
                expires_at=now + ttl,
            )
            self._stats.stores += 1
            self._stats.size = len(self._store)

    def clear(self, adapter_id: str | None = None) -> int:
        with self._lock:
            if adapter_id is None:
                removed = len(self._store)
                self._store.clear()
                self._stats.size = 0
                self._stats.evictions += removed
                return removed
            removed = 0
            for k in [k for k, v in self._store.items() if v.adapter_id == adapter_id]:
                self._store.pop(k, None)
                removed += 1
            self._stats.size = len(self._store)
            self._stats.evictions += removed
            return removed

    def stats(self) -> dict[str, Any]:
        with self._lock:
            snapshot = {
                "size": self._stats.size,
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "evictions": self._stats.evictions,
                "stores": self._stats.stores,
                "by_adapter": {},
                "oldest_age_seconds": 0.0,
            }
        now = time.monotonic()
        ages: list[float] = []
        with self._lock:
            for entry in self._store.values():
                adapter = entry.adapter_id
                snapshot["by_adapter"].setdefault(
                    adapter,
                    {"count": 0, "ttl_seconds": self.ttl_for(adapter)},
                )
                snapshot["by_adapter"][adapter]["count"] += 1
                ages.append(now - entry.stored_at)
        if ages:
            snapshot["oldest_age_seconds"] = max(ages)
        return snapshot

    def _evict_if_full(self) -> None:
        if len(self._store) < self._max_entries:
            return
        target = self._store.pop(next(iter(self._store)))
        del target
        self._stats.evictions += 1
        self._stats.size = len(self._store)


__all__ = [
    "DEFAULT_TTL_FALLBACK",
    "DEFAULT_TTL_SECONDS",
    "CacheEntry",
    "CacheStats",
    "SearchCache",
]
