from __future__ import annotations

import time
from typing import Any

from xninetzy.os.knowledge.vector_store import _load_or_create_index

WARM_EMBEDDINGS_VERSION = "1.0.0"
_DEFAULT_PROBE_QUERY = "submit to HEBAT"

_warm_cache: dict[str, Any] = {"warmed": False, "latency_ms": 0.0}


def is_warmed() -> bool:
    return bool(_warm_cache.get("warmed", False))


def warm_faiss_index(
    *,
    queries: tuple[str, ...] = (_DEFAULT_PROBE_QUERY,),
    timeout_seconds: float = 30.0,
) -> tuple[bool, float]:
    if is_warmed():
        return True, float(_warm_cache.get("latency_ms", 0.0))
    started = time.perf_counter()
    try:
        from xninetzy.context.routing.embeddings_index import _index_documents

        _index_documents(list(queries))
        _load_or_create_index()
    except Exception:
        latency_ms = (time.perf_counter() - started) * 1000.0
        _warm_cache["warmed"] = False
        _warm_cache["latency_ms"] = latency_ms
        return False, latency_ms
    latency_ms = (time.perf_counter() - started) * 1000.0
    _warm_cache["warmed"] = True
    _warm_cache["latency_ms"] = latency_ms
    return True, latency_ms
