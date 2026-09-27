from __future__ import annotations

from xninetzy.domains.career.profile.builder import build_seed_profile
from xninetzy.domains.career.profile import ProfileStore
from xninetzy.domains.career.services import build_package, package_to_dict


def _seed_profile(tmp_path):
    store = ProfileStore(tmp_path / "profile.json")
    if store.exists():
        return store.load()
    cv_text = (
        "Misbahul backend developer python fastapi langchain langgraph. "
        "Frontend engineer intern gatxel react.js tailwind. "
        "IT manager 180 degrees consulting universitas airlangga. "
        "Greenly project langchain rag multi-agent."
    )
    repos = [
        {
            "name": "Greenly",
            "fork": False,
            "description": "sustainable e-commerce",
            "language": "TypeScript",
            "html_url": "https://github.com/misbahul45/Greenly",
            "stargazers_count": 4,
        }
    ]
    profile = build_seed_profile(cv_text, github_repos=repos)
    store.save(profile)
    return profile


def test_build_package_produces_application_package():
    profile = _seed_profile(__import__("pathlib").Path("/tmp/package_test_1"))
    pkg = build_package(
        profile=profile,
        posting={
            "id": "test-123",
            "title": "Senior Python Developer",
            "company": "Acme",
            "url": "https://example.com/jobs/test-123",
            "snippet": "Python FastAPI LangChain LangGraph RAG",
        },
    )
    assert pkg.posting_id == "test-123"
    assert pkg.posting_title == "Senior Python Developer"
    assert pkg.posting_company == "Acme"
    assert pkg.matched_skills
    assert pkg.fabrication_check["all_claims_have_evidence"] is True


def test_build_package_each_matched_skill_has_evidence():
    profile = _seed_profile(__import__("pathlib").Path("/tmp/package_test_2"))
    pkg = build_package(
        profile=profile,
        posting={
            "id": "x",
            "title": "Backend",
            "company": "Co",
            "url": "https://example.com/jobs/x",
            "snippet": "Python FastAPI required",
        },
    )
    for descriptor in pkg.matched_skills:
        assert "evidence=" in descriptor
        assert "@" in descriptor


def test_build_package_each_matched_experience_has_evidence():
    profile = _seed_profile(__import__("pathlib").Path("/tmp/package_test_3"))
    pkg = build_package(
        profile=profile,
        posting={
            "id": "x",
            "title": "Backend",
            "company": "Co",
            "url": "https://example.com/jobs/x",
            "snippet": "python backend developer fastapi",
        },
    )
    for descriptor in pkg.matched_experiences:
        assert "evidence=" in descriptor


def test_build_package_each_matched_project_has_evidence():
    profile = _seed_profile(__import__("pathlib").Path("/tmp/package_test_4"))
    pkg = build_package(
        profile=profile,
        posting={
            "id": "x",
            "title": "Backend",
            "company": "Co",
            "url": "https://example.com/jobs/x",
            "snippet": "Greenly python",
        },
    )
    for descriptor in pkg.matched_projects:
        assert "evidence=" in descriptor


def test_build_package_detects_missing_information_when_profile_incomplete():
    from xninetzy.domains.career.profile import (
        CandidateProfile,
    )

    profile = CandidateProfile(
        full_name="X",
        email="",
        phone="",
        location="",
        headline="",
        summary="",
        education=(),
        experience=(),
        projects=(),
        skills=(),
        links=(),
        updated_at="2026-09-27T00:00:00+00:00",
    )
    pkg = build_package(
        profile=profile,
        posting={
            "id": "x",
            "title": "Backend",
            "company": "Co",
            "url": "https://example.com/jobs/x",
            "snippet": "Python",
        },
    )
    assert any("email" in m for m in pkg.missing_information)
    assert any("experience" in m for m in pkg.missing_information)


def test_build_package_emits_zero_fabrication_claims_for_unmatched_posting():
    profile = _seed_profile(__import__("pathlib").Path("/tmp/package_test_5"))
    pkg = build_package(
        profile=profile,
        posting={
            "id": "x",
            "title": "Quantum Physicist",
            "company": "Co",
            "url": "https://example.com/jobs/x",
            "snippet": "Quantum computing entanglement research",
        },
    )
    assert pkg.matched_skills == ()
    assert pkg.matched_experiences == ()
    assert pkg.matched_projects == ()
    assert pkg.fabrication_check["evidence_links_total"] == 0


def test_build_package_cover_letter_includes_company_and_role():
    profile = _seed_profile(__import__("pathlib").Path("/tmp/package_test_6"))
    pkg = build_package(
        profile=profile,
        posting={
            "id": "x",
            "title": "Backend Engineer",
            "company": "Acme",
            "url": "https://example.com/jobs/x",
            "snippet": "Python",
        },
    )
    assert any("Acme" in line for line in pkg.cover_letter)
    assert any("Backend Engineer" in line for line in pkg.cover_letter)


def test_build_package_common_questions_returns_dict():
    profile = _seed_profile(__import__("pathlib").Path("/tmp/package_test_7"))
    pkg = build_package(
        profile=profile,
        posting={
            "id": "x",
            "title": "Backend",
            "company": "Co",
            "url": "https://example.com/jobs/x",
            "snippet": "Python FastAPI",
        },
    )
    assert "why_interested" in pkg.common_questions
    assert "relevant_experience" in pkg.common_questions
    assert "skills" in pkg.common_questions


def test_package_to_dict_serializes_evidence_per_claim():
    profile = _seed_profile(__import__("pathlib").Path("/tmp/package_test_8"))
    pkg = build_package(
        profile=profile,
        posting={
            "id": "x",
            "title": "Backend",
            "company": "Co",
            "url": "https://example.com/jobs/x",
            "snippet": "Python",
        },
    )
    data = package_to_dict(pkg)
    for entry in data["common_questions"]["skills"]:
        assert "evidence" in entry
        assert "source" in entry["evidence"]
        assert "locator" in entry["evidence"]
