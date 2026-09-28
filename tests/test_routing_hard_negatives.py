from __future__ import annotations

from pathlib import Path

from xninetzy.context.routing.benchmark import BenchmarkCase
from xninetzy.context.routing.hard_negatives import (
    DEFAULT_CONFUSION_PAIRS,
    HARD_NEGATIVE_VERSION,
    analyze_confusion_pairs,
    generate_negation_set,
    generate_paraphrase_pair,
    write_hard_negative_report,
)


def test_constants() -> None:
    assert HARD_NEGATIVE_VERSION == "1.0.0"
    assert len(DEFAULT_CONFUSION_PAIRS) >= 5


def test_generate_paraphrase_pair_returns_two_cases() -> None:
    pos, neg = generate_paraphrase_pair("submit to HEBAT", target_tools=("hebat_upload_submission",))
    assert pos.query == "submit to HEBAT"
    assert neg.query.startswith("do NOT")


def test_generate_negation_set_returns_three() -> None:
    samples = generate_negation_set("academic sources", exclude_tools=("research_search_papers",))
    assert len(samples) == 3
    assert any("include only" in s.query for s in samples)
    assert any(s.query.startswith("exclude ") for s in samples)


def test_analyze_confusion_pairs_with_combined_baseline(tmp_path) -> None:
    from xninetzy.context.routing.baselines import CombinedBaseline

    cases = [
        BenchmarkCase(
            request_id="r1",
            query="find research papers",
            expected_tools=("research_search_papers",),
            expected_domains=("research",),
        ),
        BenchmarkCase(
            request_id="r2",
            query="memory recall",
            expected_tools=("memory_relevance",),
            expected_domains=("knowledge",),
        ),
    ]
    router = CombinedBaseline().route
    result = analyze_confusion_pairs(cases=cases, router=router)
    assert isinstance(result, dict)
    assert "research_knowledge" in result


def test_write_hard_negative_report(tmp_path) -> None:
    analysis = {
        "research_knowledge": {"n": 10, "accuracy": 0.6, "positive_hit": 6, "missed": 4},
    }
    path = write_hard_negative_report(analysis, tmp_path)
    assert Path(path).exists()
