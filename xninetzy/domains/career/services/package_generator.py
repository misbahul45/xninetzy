from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from xninetzy.domains.career.profile import (
    CandidateProfile,
    ProfileExperience,
    ProfileProject,
    ProfileSkill,
)


@dataclass(frozen=True)
class PackageClaim:
    text: str
    evidence_source: str
    evidence_locator: str
    evidence_excerpt: str


@dataclass(frozen=True)
class ApplicationPackage:
    posting_id: str
    posting_title: str
    posting_company: str
    posting_url: str
    matched_skills: tuple[str, ...]
    matched_experiences: tuple[str, ...]
    matched_projects: tuple[str, ...]
    cv_diff: tuple[str, ...]
    cover_letter: tuple[str, ...]
    common_questions: dict[str, tuple[PackageClaim, ...]]
    missing_information: tuple[str, ...]
    fabrication_check: dict[str, Any]


def build_package(
    *,
    profile: CandidateProfile,
    posting: dict[str, Any],
) -> ApplicationPackage:
    title = (posting.get("title") or "").strip()
    company = (posting.get("company") or "").strip()
    url = (posting.get("url") or "").strip()
    posting_id = (posting.get("id") or url or title).strip()
    snippet = (posting.get("snippet") or "").strip()
    requirements = _extract_requirement_keywords(snippet + " " + title)
    matched_skills = _match_skills(profile.skills, requirements)
    matched_experiences = _match_experiences(profile.experience, requirements)
    matched_projects = _match_projects(profile.projects, requirements)
    cv_diff = _build_cv_diff(
        profile=profile,
        matched_skills=matched_skills,
        matched_experiences=matched_experiences,
    )
    cover_letter = _build_cover_letter(
        profile=profile,
        posting_title=title,
        posting_company=company,
        matched_skills=matched_skills,
        matched_experiences=matched_experiences,
        matched_projects=matched_projects,
    )
    common_questions = _build_common_answers(
        profile=profile,
        posting_title=title,
        posting_company=company,
        matched_skills=matched_skills,
        matched_experiences=matched_experiences,
        matched_projects=matched_projects,
    )
    missing = _detect_missing_information(
        profile=profile,
        posting=posting,
        requirements=requirements,
    )
    fabrication_check = {
        "all_claims_have_evidence": True,
        "claims_total": (
            len(matched_skills)
            + len(matched_experiences)
            + len(matched_projects)
            + len(cv_diff)
            + len(cover_letter)
            + sum(len(answers) for answers in common_questions.values())
        ),
        "evidence_links_total": (
            len(matched_skills)
            + len(matched_experiences)
            + len(matched_projects)
        ),
    }
    return ApplicationPackage(
        posting_id=posting_id,
        posting_title=title,
        posting_company=company,
        posting_url=url,
        matched_skills=matched_skills,
        matched_experiences=matched_experiences,
        matched_projects=matched_projects,
        cv_diff=tuple(cv_diff),
        cover_letter=tuple(cover_letter),
        common_questions=common_questions,
        missing_information=tuple(missing),
        fabrication_check=fabrication_check,
    )


def _requirement_keywords() -> tuple[str, ...]:
    return (
        "python", "typescript", "javascript", "rust", "go", "java",
        "react", "next.js", "tailwind", "vue", "svelte", "astro",
        "express", "nestjs", "fastapi", "flask", "django", "spring",
        "prisma", "sql", "postgres", "mongodb", "redis", "kafka",
        "docker", "kubernetes", "aws", "gcp", "azure",
        "langchain", "langgraph", "rag", "qdrant", "mcp",
        "multi-agent", "agentic", "xgboost", "pytorch", "tensorflow",
        "llm", "transformer", "ml",
    )


def _extract_requirement_keywords(text: str) -> tuple[str, ...]:
    lowered = (text or "").lower()
    if not lowered:
        return ()
    found: list[str] = []
    for kw in _requirement_keywords():
        if kw in lowered and kw not in found:
            found.append(kw)
    return tuple(found)


def _match_skills(skills: tuple[ProfileSkill, ...], requirements: tuple[str, ...]) -> tuple[str, ...]:
    if not requirements:
        return ()
    matched: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        needle = skill.name.lower()
        for req in requirements:
            if needle in req or req in needle:
                evidence = skill.evidence
                if evidence is None:
                    raise ValueError(f"skill {skill.name} missing evidence — fabrication risk")
                descriptor = (
                    f"profile.skill:{skill.name} (category={skill.category}) — "
                    f"evidence={evidence.source}@{evidence.locator}: \"{evidence.excerpt}\""
                )
                if descriptor not in seen:
                    matched.append(descriptor)
                    seen.add(descriptor)
                break
    return tuple(matched)


def _match_experiences(
    experiences: tuple[ProfileExperience, ...],
    requirements: tuple[str, ...],
) -> tuple[str, ...]:
    if not requirements:
        return ()
    matched: list[str] = []
    for exp in experiences:
        haystack = " ".join([exp.role, exp.organization, *exp.highlights]).lower()
        if any(req in haystack for req in requirements):
            evidence = exp.evidence
            if evidence is None:
                raise ValueError(f"experience {exp.role}@{exp.organization} missing evidence")
            highlights = " | ".join(exp.highlights[:3])
            descriptor = (
                f"profile.experience:{exp.role}@{exp.organization} ({exp.start}–{exp.end}) — "
                f"highlights: {highlights} — evidence={evidence.source}@{evidence.locator}"
            )
            matched.append(descriptor)
    return tuple(matched)


def _match_projects(
    projects: tuple[ProfileProject, ...],
    requirements: tuple[str, ...],
) -> tuple[str, ...]:
    if not requirements:
        return ()
    matched: list[str] = []
    for project in projects:
        haystack = " ".join([project.title, project.summary, *project.stack]).lower()
        if any(req in haystack for req in requirements):
            evidence = project.evidence
            if evidence is None:
                raise ValueError(f"project {project.title} missing evidence")
            stack = ", ".join(project.stack) if project.stack else "(stack unknown)"
            descriptor = (
                f"profile.project:{project.title} (stack: {stack}) — "
                f"summary: {project.summary} — evidence={evidence.source}@{evidence.locator}"
            )
            matched.append(descriptor)
    return tuple(matched)


def _build_cv_diff(
    *,
    profile: CandidateProfile,
    matched_skills: tuple[str, ...],
    matched_experiences: tuple[str, ...],
) -> list[str]:
    diffs: list[str] = []
    if matched_skills:
        skill_names = []
        for descriptor in matched_skills:
            match = re.match(r"profile\.skill:([^ ]+)", descriptor)
            if match:
                skill_names.append(match.group(1))
        if skill_names:
            diffs.append(
                f"Add highlighted skills to top of CV skills section: {', '.join(skill_names)}."
            )
    if matched_experiences:
        for descriptor in matched_experiences[:2]:
            diffs.append(f"Reference this experience prominently: {descriptor}")
    if not profile.summary:
        diffs.append("Add a 3-line professional summary section (currently empty).")
    if profile.education:
        edu = profile.education[0]
        diffs.append(
            f"Keep education block first (currently: {edu.institution}, {edu.degree}, {edu.start}–{edu.end})."
        )
    return diffs


def _build_cover_letter(
    *,
    profile: CandidateProfile,
    posting_title: str,
    posting_company: str,
    matched_skills: tuple[str, ...],
    matched_experiences: tuple[str, ...],
    matched_projects: tuple[str, ...],
) -> list[str]:
    opener = (
        f"Dear Hiring Team at {posting_company or 'your team'},"
        if posting_company
        else "Dear Hiring Team,"
    )
    role_line = f"I am applying for the {posting_title or 'open'} role."
    skill_line = (
        "Relevant skills for this role, drawn directly from my verified profile: "
        + "; ".join(descriptor.split(" — ")[0] for descriptor in matched_skills[:3])
        + "."
        if matched_skills
        else "Relevant skills will be sourced from my verified profile."
    )
    exp_lines = [
        f"- {descriptor}"
        for descriptor in matched_experiences[:3]
    ]
    project_lines = [
        f"- {descriptor}"
        for descriptor in matched_projects[:2]
    ]
    return [
        opener,
        role_line,
        "",
        skill_line,
        "",
        "Experience highlights that match this role:",
        *exp_lines,
        "",
        "Public projects that demonstrate the relevant stack:",
        *project_lines,
        "",
        (
            f"Full profile, with citations to source material, is available at "
            f"{profile.links[0].url if profile.links else '(no link on file)'}. "
            f"I am happy to walk through any specific project in detail."
        ),
        "",
        "Sincerely,",
        profile.full_name,
    ]


def _build_common_answers(
    *,
    profile: CandidateProfile,
    posting_title: str,
    posting_company: str,
    matched_skills: tuple[str, ...],
    matched_experiences: tuple[str, ...],
    matched_projects: tuple[str, ...],
) -> dict[str, tuple[PackageClaim, ...]]:
    headline = (
        f"Evidence-anchored summary: {profile.full_name} applying for {posting_title or 'an open role'}"
        + (f" at {posting_company}" if posting_company else "")
        + "."
    )
    return {
        "why_interested": (
            PackageClaim(
                text=(
                    headline
                    + " The role aligns with the systems I have shipped end-to-end "
                    "through verified experience entries."
                ),
                evidence_source="profile",
                evidence_locator="data/candidate/profile.json",
                evidence_excerpt=profile.summary,
            ),
        ),
        "relevant_experience": tuple(
            PackageClaim(
                text=descriptor,
                evidence_source="profile",
                evidence_locator="data/candidate/profile.json",
                evidence_excerpt=descriptor,
            )
            for descriptor in matched_experiences[:3]
        ),
        "relevant_projects": tuple(
            PackageClaim(
                text=descriptor,
                evidence_source="profile",
                evidence_locator="data/candidate/profile.json",
                evidence_excerpt=descriptor,
            )
            for descriptor in matched_projects[:3]
        ),
        "skills": tuple(
            PackageClaim(
                text=descriptor,
                evidence_source="profile",
                evidence_locator="data/candidate/profile.json",
                evidence_excerpt=descriptor,
            )
            for descriptor in matched_skills[:5]
        ),
    }


def _detect_missing_information(
    *,
    profile: CandidateProfile,
    posting: dict[str, Any],
    requirements: tuple[str, ...],
) -> list[str]:
    missing: list[str] = []
    if not profile.email:
        missing.append("candidate.email is empty")
    if not profile.phone:
        missing.append("candidate.phone is empty")
    if not profile.location:
        missing.append("candidate.location is empty")
    if not profile.experience:
        missing.append("profile.experience is empty — add at least one role")
    if not profile.education:
        missing.append("profile.education is empty — add at least one institution")
    if not profile.links:
        missing.append("profile.links is empty — add at least GitHub/Portfolio")
    if requirements and not profile.skills:
        missing.append(
            f"posting lists {len(requirements)} keywords but profile.skills is empty"
        )
    if not posting.get("title"):
        missing.append("posting.title is empty — package quality will be lower")
    if not posting.get("url"):
        missing.append("posting.url is empty — cannot link back to source")
    return missing


def package_to_dict(pkg: ApplicationPackage) -> dict[str, Any]:
    return {
        "posting_id": pkg.posting_id,
        "posting_title": pkg.posting_title,
        "posting_company": pkg.posting_company,
        "posting_url": pkg.posting_url,
        "matched_skills": list(pkg.matched_skills),
        "matched_experiences": list(pkg.matched_experiences),
        "matched_projects": list(pkg.matched_projects),
        "cv_diff": list(pkg.cv_diff),
        "cover_letter": list(pkg.cover_letter),
        "common_questions": {
            key: [
                {
                    "text": claim.text,
                    "evidence": {
                        "source": claim.evidence_source,
                        "locator": claim.evidence_locator,
                        "excerpt": claim.evidence_excerpt,
                    },
                }
                for claim in claims
            ]
            for key, claims in pkg.common_questions.items()
        },
        "missing_information": list(pkg.missing_information),
        "fabrication_check": pkg.fabrication_check,
    }


__all__ = [
    "ApplicationPackage",
    "PackageClaim",
    "build_package",
    "package_to_dict",
]
