from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroundTruthPost:
    url: str
    source_board: str
    title: str
    company: str


@dataclass(frozen=True)
class EvalQuery:
    query_id: str
    query_text: str
    country: str = ""
    work_mode: str = "any"
    posted_within_days: int = 0
    ground_truth: tuple[GroundTruthPost, ...] = ()


@dataclass(frozen=True)
class EvalSet:
    version: int
    domain: str
    subset: str
    created_at: str
    queries: tuple[EvalQuery, ...] = ()