from __future__ import annotations

import json
from pathlib import Path

from xninetzy.domains.career.eval.schema import EvalQuery, EvalSet, GroundTruthPost


def default_eval_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "career" / "eval"


def list_eval_subsets(eval_dir: Path | None = None) -> list[str]:
    base = Path(eval_dir) if eval_dir is not None else default_eval_dir()
    if not base.exists():
        return []
    return sorted(p.stem for p in base.glob("*.json"))


def load_eval_set(path: str | Path) -> EvalSet:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    queries: list[EvalQuery] = []
    for entry in data.get("queries", []):
        gt = tuple(
            GroundTruthPost(
                url=g["url"],
                source_board=g.get("source_board", ""),
                title=g.get("title", ""),
                company=g.get("company", ""),
            )
            for g in entry.get("ground_truth", [])
        )
        queries.append(
            EvalQuery(
                query_id=entry["query_id"],
                query_text=entry["query_text"],
                country=entry.get("country", ""),
                work_mode=entry.get("work_mode", "any"),
                posted_within_days=entry.get("posted_within_days", 0),
                ground_truth=gt,
            )
        )
    return EvalSet(
        version=int(data.get("version", 1)),
        domain=data.get("domain", "career"),
        subset=data.get("subset", source.stem),
        created_at=data.get("created_at", ""),
        queries=tuple(queries),
    )