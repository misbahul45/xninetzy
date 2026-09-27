from __future__ import annotations

import json

import pytest


@pytest.fixture
def sample_eval_path(tmp_path):
    payload = {
        "version": 1,
        "domain": "career",
        "subset": "indonesia_internships",
        "created_at": "2026-09-27",
        "queries": [
            {
                "query_id": "ind-intern-001",
                "query_text": "backend engineer intern",
                "country": "ID",
                "work_mode": "any",
                "posted_within_days": 30,
                "ground_truth": [
                    {
                        "url": "https://kalibrr.com/jobs/abc",
                        "source_board": "kalibrr",
                        "title": "Backend Engineer Intern",
                        "company": "Tokopedia",
                    },
                    {
                        "url": "https://glints.com/id/opportunities/xyz",
                        "source_board": "glints",
                        "title": "Software Engineer Intern",
                        "company": "Gojek",
                    },
                ],
            },
            {
                "query_id": "ind-intern-002",
                "query_text": "data scientist intern",
                "country": "ID",
                "work_mode": "remote",
                "posted_within_days": 14,
                "ground_truth": [
                    {
                        "url": "https://dealls.com/opportunities/ds-1",
                        "source_board": "dealls",
                        "title": "Data Science Intern",
                        "company": "Bukalapak",
                    }
                ],
            },
            {
                "query_id": "ind-intern-003",
                "query_text": "frontend engineer",
                "country": "ID",
                "ground_truth": [],
            },
        ],
    }
    path = tmp_path / "indonesia_internships.json"
    path.write_text(json.dumps(payload))
    return path


def test_eval_set_loads_from_json(sample_eval_path):
    from xninetzy.domains.career.eval.loader import load_eval_set

    eval_set = load_eval_set(sample_eval_path)
    assert eval_set.version == 1
    assert eval_set.domain == "career"
    assert eval_set.subset == "indonesia_internships"
    assert len(eval_set.queries) == 3
    q1 = eval_set.queries[0]
    assert q1.query_id == "ind-intern-001"
    assert q1.query_text == "backend engineer intern"
    assert q1.country == "ID"
    assert q1.posted_within_days == 30
    assert len(q1.ground_truth) == 2
    assert q1.ground_truth[0].company == "Tokopedia"


def test_recall_at_k_matches_ground_truth_overlap():
    from xninetzy.domains.career.eval.metrics import recall_at_k

    retrieved = [
        "https://kalibrr.com/jobs/abc",
        "https://unrelated.com/x",
        "https://glints.com/id/opportunities/xyz",
    ]
    ground = {
        "https://kalibrr.com/jobs/abc",
        "https://glints.com/id/opportunities/xyz",
        "https://missing.com/y",
    }
    assert recall_at_k(retrieved, ground, k=10) == pytest.approx(2 / 3)


def test_recall_at_k_returns_zero_when_no_overlap():
    from xninetzy.domains.career.eval.metrics import recall_at_k

    assert recall_at_k(["https://other.com/y"], {"https://missing.com/z"}, k=10) == 0.0


def test_recall_at_k_is_safe_with_empty_ground_truth():
    from xninetzy.domains.career.eval.metrics import recall_at_k

    assert recall_at_k(["https://any.com/y"], set(), k=10) == 0.0


def test_recall_at_k_is_k_sensitive():
    from xninetzy.domains.career.eval.metrics import recall_at_k

    retrieved = [
        "https://kalibrr.com/jobs/abc",
        "https://noise.com/1",
    ]
    ground = {"https://kalibrr.com/jobs/abc"}
    assert recall_at_k(retrieved, ground, k=1) == 1.0
    assert recall_at_k(retrieved, ground, k=2) == 1.0
    assert recall_at_k(retrieved, ground, k=5) == 1.0


def test_eval_harness_runs_queries_and_aggregates(sample_eval_path):
    from xninetzy.domains.career.eval.harness import run_eval
    from xninetzy.domains.career.eval.loader import load_eval_set

    eval_set = load_eval_set(sample_eval_path)

    def mock_query_fn(query):
        if query.query_id == "ind-intern-001":
            return [
                _result("https://kalibrr.com/jobs/abc"),
                _result("https://unrelated.com/x"),
            ]
        if query.query_id == "ind-intern-002":
            return [_result("https://noise.com/y")]
        return []

    report = run_eval(eval_set, mock_query_fn, k_values=(10,))
    assert report.subset == "indonesia_internships"
    assert report.query_count == 3
    assert report.per_query[0].recall_at_10 == pytest.approx(1 / 2)
    assert report.per_query[1].recall_at_10 == 0.0
    assert report.per_query[2].recall_at_10 == 0.0
    expected_mean = (1 / 2 + 0.0 + 0.0) / 3
    assert report.mean_recall_at_10 == pytest.approx(expected_mean)


def test_eval_harness_records_hits_and_retrieved_count(sample_eval_path):
    from xninetzy.domains.career.eval.harness import run_eval
    from xninetzy.domains.career.eval.loader import load_eval_set

    eval_set = load_eval_set(sample_eval_path)

    def mock_query_fn(query):
        return [
            _result("https://kalibrr.com/jobs/abc"),
            _result("https://glints.com/id/opportunities/xyz"),
            _result("https://dealls.com/opportunities/ds-1"),
        ]

    report = run_eval(eval_set, mock_query_fn, k_values=(10,))
    first = report.per_query[0]
    assert first.retrieved_count == 3
    assert sorted(first.hits) == sorted(
        ["https://kalibrr.com/jobs/abc", "https://glints.com/id/opportunities/xyz"]
    )


def _result(url):
    from xninetzy.domains.career.eval.harness import RetrievalResult

    return RetrievalResult(url=url, source="mock", title="mock", company="mock")


def test_default_eval_dir_points_to_data_career_eval():
    from xninetzy.domains.career.eval.loader import default_eval_dir

    assert default_eval_dir().name == "eval"
    assert default_eval_dir().parent.name == "career"