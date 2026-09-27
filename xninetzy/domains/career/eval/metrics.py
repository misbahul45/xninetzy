from __future__ import annotations


def recall_at_k(retrieved_urls: list[str], ground_truth_urls: set[str], k: int) -> float:
    if not ground_truth_urls:
        return 0.0
    top_k = retrieved_urls[: max(0, k)]
    if not top_k:
        return 0.0
    hits = sum(1 for url in top_k if url in ground_truth_urls)
    return hits / len(ground_truth_urls)