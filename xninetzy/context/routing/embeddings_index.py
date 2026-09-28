from __future__ import annotations

import time
from typing import Any

from xninetzy.os.knowledge.vector_store import _load_or_create_index as _lazy_index

_INDEX: dict[str, Any] = {"items": [], "vectors": []}


def _index_documents(items: list[str], vectors: list[Any] | None = None) -> None:
    _INDEX["items"] = list(items)
    if vectors is not None:
        _INDEX["vectors"] = list(vectors)
    else:
        _INDEX["vectors"] = [None] * len(items)


def get_indexed_items() -> list[str]:
    return list(_INDEX["items"])
