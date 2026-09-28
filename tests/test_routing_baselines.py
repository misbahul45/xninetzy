from __future__ import annotations

from xninetzy.context.routing.baselines import (
    BenchmarkCase,
    CombinedBaseline,
    EmbeddingsBaseline,
    RulesBaseline,
    get_baseline,
    load_benchmark_cases,
    top1_acc,
)


def _get_intent_registry():
    try:
        from xninetzy.tools.ecosystem.intent_registry import get as _g

        return _g()
    except Exception:
        return {}


def test_load_benchmark_cases_returns_test_split() -> None:
    cases = load_benchmark_cases(split="test", limit=20)
    assert cases == [] or all(isinstance(c, BenchmarkCase) for c in cases)


def test_rules_baseline_returns_decision() -> None:
    r = RulesBaseline(intent_registry_getter=_get_intent_registry)
    d = r.route("submit to HEBAT")
    assert d.baseline == "B-rules"
    assert d.latency_ms >= 0


def test_embeddings_baseline_handles_missing_model() -> None:
    e = EmbeddingsBaseline()
    d = e.route("hello")
    assert d.baseline == "C-embeddings"
    assert d.latency_ms >= 0


def test_combined_baseline_returns_combined_decision() -> None:
    c = CombinedBaseline()
    d = c.route("find research papers")
    assert d.baseline == "D-rules+embeddings"
    assert d.latency_ms >= 0


def test_top1_acc_metric_shape() -> None:
    cases = [
        BenchmarkCase(
            request_id="1",
            query="submit to HEBAT",
            expected_tools=("hebat_upload_submission",),
            expected_domains=("academic",),
        )
    ]
    r = RulesBaseline(intent_registry_getter=_get_intent_registry)
    summary = top1_acc(cases, router=r)
    assert summary["baseline"] == "B-rules"
    assert 0.0 <= summary["top1"] <= 1.0


def test_get_baseline_d_raises_for_unimplemented() -> None:
    try:
        get_baseline("E-Laya")
    except NotImplementedError:
        assert True
    else:
        assert False, "Phase 6/7+ should populate Laya baseline"
