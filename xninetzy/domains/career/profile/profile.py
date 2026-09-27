from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Evidence:
    source: str
    locator: str
    excerpt: str
    confidence: float = 1.0


@dataclass(frozen=True)
class ProfileLink:
    label: str
    url: str
    evidence: Evidence | None = None


@dataclass(frozen=True)
class ProfileSkill:
    name: str
    category: str
    evidence: Evidence | None = None


@dataclass(frozen=True)
class ProfileProject:
    title: str
    role: str
    summary: str
    stack: tuple[str, ...]
    links: tuple[ProfileLink, ...]
    evidence: Evidence | None = None


@dataclass(frozen=True)
class ProfileExperience:
    role: str
    organization: str
    start: str
    end: str
    highlights: tuple[str, ...]
    evidence: Evidence | None = None


@dataclass(frozen=True)
class ProfileEducation:
    institution: str
    degree: str
    start: str
    end: str
    evidence: Evidence | None = None


@dataclass(frozen=True)
class CandidateProfile:
    full_name: str
    email: str
    phone: str
    location: str
    headline: str
    summary: str
    education: tuple[ProfileEducation, ...]
    experience: tuple[ProfileExperience, ...]
    projects: tuple[ProfileProject, ...]
    skills: tuple[ProfileSkill, ...]
    links: tuple[ProfileLink, ...]
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ProfileStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self._path.exists()

    def load(self) -> CandidateProfile | None:
        if not self._path.exists():
            return None
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return _from_dict(data)

    def save(self, profile: CandidateProfile) -> None:
        self._path.write_text(profile.to_json(), encoding="utf-8")

    def reset(self) -> None:
        if self._path.exists():
            self._path.unlink()


def _from_dict(data: dict[str, Any]) -> CandidateProfile:
    return CandidateProfile(
        full_name=data.get("full_name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        location=data.get("location", ""),
        headline=data.get("headline", ""),
        summary=data.get("summary", ""),
        education=tuple(_education_from_dict(e) for e in data.get("education", [])),
        experience=tuple(_experience_from_dict(e) for e in data.get("experience", [])),
        projects=tuple(_project_from_dict(p) for p in data.get("projects", [])),
        skills=tuple(_skill_from_dict(s) for s in data.get("skills", [])),
        links=tuple(_link_from_dict(link) for link in data.get("links", [])),
        updated_at=data.get("updated_at", _now_iso()),
    )


def _evidence_from_dict(data: dict | None) -> Evidence | None:
    if not data:
        return None
    return Evidence(
        source=data.get("source", ""),
        locator=data.get("locator", ""),
        excerpt=data.get("excerpt", ""),
        confidence=float(data.get("confidence", 1.0)),
    )


def _link_from_dict(data: dict) -> ProfileLink:
    return ProfileLink(
        label=data.get("label", ""),
        url=data.get("url", ""),
        evidence=_evidence_from_dict(data.get("evidence")),
    )


def _skill_from_dict(data: dict) -> ProfileSkill:
    return ProfileSkill(
        name=data.get("name", ""),
        category=data.get("category", "general"),
        evidence=_evidence_from_dict(data.get("evidence")),
    )


def _project_from_dict(data: dict) -> ProfileProject:
    return ProfileProject(
        title=data.get("title", ""),
        role=data.get("role", ""),
        summary=data.get("summary", ""),
        stack=tuple(data.get("stack", [])),
        links=tuple(_link_from_dict(link) for link in data.get("links", [])),
        evidence=_evidence_from_dict(data.get("evidence")),
    )


def _experience_from_dict(data: dict) -> ProfileExperience:
    return ProfileExperience(
        role=data.get("role", ""),
        organization=data.get("organization", ""),
        start=data.get("start", ""),
        end=data.get("end", ""),
        highlights=tuple(data.get("highlights", [])),
        evidence=_evidence_from_dict(data.get("evidence")),
    )


def _education_from_dict(data: dict) -> ProfileEducation:
    return ProfileEducation(
        institution=data.get("institution", ""),
        degree=data.get("degree", ""),
        start=data.get("start", ""),
        end=data.get("end", ""),
        evidence=_evidence_from_dict(data.get("evidence")),
    )


def default_profile_path() -> Path:
    return Path("data/candidate/profile.json")


__all__ = [
    "CandidateProfile",
    "Evidence",
    "ProfileEducation",
    "ProfileExperience",
    "ProfileLink",
    "ProfileProject",
    "ProfileSkill",
    "ProfileStore",
    "default_profile_path",
]
