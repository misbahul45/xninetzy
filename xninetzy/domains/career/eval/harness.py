from __future__ import annotations

from dataclasses import dataclass

from xninetzy.domains.career.eval.metrics import recall_at_k
from xninetzy.domains.career.eval.schema import EvalSet


@dataclass(frozen=True)
class RetrievalResult:
    url: str
    source: str
    title: str
    company: str


@dataclass(frozen=True)
class EvalQueryResult:
    query_id: str
    retrieved_count: int
    hits: list[str]
    recall_at_10: float
    recall_at_25: float


@dataclass(frozen=True)
class EvalRunReport:
    subset: str
    query_count: int
    mean_recall_at_10: float
    mean_recall_at_25: float
    per_query: tuple[EvalQueryResult, ...]


def run_eval(
    eval_set: EvalSet,
    query_fn,
    k_values: tuple[int, ...] = (10, 25),
) -> EvalRunReport:
    per_query: list[EvalQueryResult] = []
    sums: dict[int, float] = {k: 0.0 for k in k_values}
    for query in eval_set.queries:
        results = list(query_fn(query))
        retrieved_urls = [r.url for r in results]
        gt_urls = {gt.url for gt in query.ground_truth}
        per_k = {k: recall_at_k(retrieved_urls, gt_urls, k) for k in k_values}
        hits = [url for url in retrieved_urls if url in gt_urls]
        per_query.append(
            EvalQueryResult(
                query_id=query.query_id,
                retrieved_count=len(retrieved_urls),
                hits=hits,
                recall_at_10=per_k.get(10, 0.0),
                recall_at_25=per_k.get(25, 0.0),
            )
        )
        for k in k_values:
            sums[k] += per_k[k]
    n = max(1, len(eval_set.queries))
    return EvalRunReport(
        subset=eval_set.subset,
        query_count=len(eval_set.queries),
        mean_recall_at_10=sums.get(10, 0.0) / n,
        mean_recall_at_25=sums.get(25, 0.0) / n,
        per_query=tuple(per_query),
    )