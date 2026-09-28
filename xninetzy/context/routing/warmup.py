from __future__ import annotations

import threading
import time
from typing import Any

from xninetzy.context.routing.embeddings_warmup import (
    is_warmed,
    warm_faiss_index,
)

WARM_VERSION = "1.0.0"
_DEFAULT_WARM_QUERIES: tuple[str, ...] = (
    "submit to HEBAT",
    "find research papers",
    "show my tasks",
    "render the video",
    "audit my code",
    "find React jobs",
)


def warmup_routing_stack(
    *,
    queries: tuple[str, ...] = _DEFAULT_WARM_QUERIES,
    calibration_dir: str = "data/routing_calibration",
) -> dict[str, Any]:
    started = time.perf_counter()
    faiss_loaded, faiss_latency_ms = warm_faiss_index(queries=queries)
    from xninetzy.context.routing.calibration import CalibrationRegistry

    cal_registry = CalibrationRegistry(storage_dir=calibration_dir)
    n_calibration = 0
    for layer in ("L2_domain", "L3_skill", "L4_task", "L5_capability", "L5_tool"):
        for domain in ("learning", "research", "career", "academic", "media", "security", "knowledge"):
            if cal_registry.lookup(layer, domain):
                n_calibration += 1
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "version": WARM_VERSION,
        "faiss_loaded": faiss_loaded,
        "faiss_warm_latency_ms": faiss_latency_ms,
        "n_calibration_records": n_calibration,
        "n_warmup_queries": len(queries),
        "total_warmup_ms": elapsed_ms,
        "already_warm": is_warmed(),
    }


_warm_lock = threading.Lock()
_warm_invoked = False


def warm_once(*, queries: tuple[str, ...] = _DEFAULT_WARM_QUERIES) -> dict[str, Any]:
    global _warm_invoked
    with _warm_lock:
        if _warm_invoked:
            return {"already_warm": True, "version": WARM_VERSION}
        result = warmup_routing_stack(queries=queries)
        _warm_invoked = True
        return result
