from __future__ import annotations

from pathlib import Path


def test_profile_roundtrip(tmp_path: Path) -> None:
    from xninetzy.domains.career.profile import (
        CandidateProfile,
        Evidence,
        ProfileEducation,
        ProfileExperience,
        ProfileStore,
    )

    profile = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="+1 555 0000",
        location="Test City",
        headline="Engineer",
        summary="A test summary",
        education=(
            ProfileEducation(
                institution="Test Univ",
                degree="BS CS",
                start="2020",
                end="2024",
                evidence=Evidence(source="cv", locator="cv.txt", excerpt="BS CS Test Univ 2020-2024"),
            ),
        ),
        experience=(
            ProfileExperience(
                role="SWE",
                organization="TestCo",
                start="2024",
                end="2025",
                highlights=("Built things",),
                evidence=Evidence(source="cv", locator="cv.txt", excerpt="SWE TestCo 2024-2025"),
            ),
        ),
        projects=(),
        skills=(),
        links=(),
        updated_at="2026-09-27T00:00:00+00:00",
    )
    store = ProfileStore(tmp_path / "profile.json")
    store.save(profile)
    loaded = store.load()
    assert loaded is not None
    assert loaded.full_name == "Test User"
    assert loaded.education[0].institution == "Test Univ"
    assert loaded.experience[0].highlights == ("Built things",)


def test_profile_store_returns_none_when_missing(tmp_path: Path) -> None:
    from xninetzy.domains.career.profile import ProfileStore

    assert ProfileStore(tmp_path / "missing.json").load() is None


def test_build_seed_profile_extracts_skills_from_cv_text(tmp_path: Path) -> None:
    from xninetzy.domains.career.profile import build_seed_profile

    cv_text = "Misbahul Muttaqin has experience with Python, FastAPI, TypeScript, React.js, and LangGraph multi-agent systems. He led CERVANA at LIDM 2025."
    profile = build_seed_profile(cv_text, github_repos=[])
    skill_names = {s.name for s in profile.skills}
    assert "python" in skill_names
    assert "fastapi" in skill_names
    assert "typescript" in skill_names
    assert "react.js" in skill_names
    assert "langgraph" in skill_names


def test_build_seed_profile_extracts_experiences_from_cv_text() -> None:
    from xninetzy.domains.career.profile import build_seed_profile

    cv_text = (
        "Backend Developer, Study First Aug to Oct 2025. Frontend Engineer Intern, Gatxel Jan to Mar 2025. "
        "IT Manager, 180 Degrees Consulting Universitas Airlangga May 2026 to Present."
    )
    profile = build_seed_profile(cv_text, github_repos=[])
    orgs = {e.organization for e in profile.experience}
    assert "Study First" in orgs
    assert "Gatxel" in orgs
    assert "180 Degrees Consulting — Universitas Airlangga" in orgs


def test_build_seed_profile_attaches_github_repos_as_projects() -> None:
    from xninetzy.domains.career.profile import build_seed_profile

    repos = [
        {
            "name": "Greenly",
            "fork": False,
            "description": "sustainable e-commerce marketplace",
            "language": "TypeScript",
            "html_url": "https://github.com/misbahul45/Greenly",
            "stargazers_count": 4,
        },
        {
            "name": "contrib-fork",
            "fork": True,
            "description": "forked",
            "language": "Python",
            "html_url": "https://github.com/misbahul45/contrib-fork",
            "stargazers_count": 0,
        },
    ]
    profile = build_seed_profile("Misbahul backend developer Python.", github_repos=repos)
    titles = {p.title for p in profile.projects}
    assert "Greenly" in titles
    assert "contrib-fork" not in titles


def test_build_seed_profile_includes_evidence_for_each_skill() -> None:
    from xninetzy.domains.career.profile import build_seed_profile

    cv_text = "Misbahul has experience with Python, FastAPI, and Docker."
    profile = build_seed_profile(cv_text, github_repos=[])
    for skill in profile.skills:
        assert skill.evidence is not None
        assert skill.evidence.source
        assert skill.evidence.locator


def test_build_seed_profile_returns_empty_skills_when_cv_has_no_known_skills() -> None:
    from xninetzy.domains.career.profile import build_seed_profile

    profile = build_seed_profile("just a brief bio", github_repos=[])
    assert profile.skills == ()


def test_default_profile_path_points_to_gitignored_dir() -> None:
    from xninetzy.domains.career.profile import default_profile_path

    assert default_profile_path().parent.name == "candidate"
    assert str(default_profile_path()).startswith("data/")


def test_build_seed_profile_summary_does_not_fabricate_metrics() -> None:
    from xninetzy.domains.career.profile import build_seed_profile

    cv_text = "Misbahul — Information Systems student."
    profile = build_seed_profile(cv_text, github_repos=[])
    assert "93%" not in profile.summary
    assert "86%" not in profile.summary
