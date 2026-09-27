from __future__ import annotations

from typing import Any

from xninetzy.domains.career.profile.profile import (
    CandidateProfile,
    Evidence,
    ProfileEducation,
    ProfileExperience,
    ProfileLink,
    ProfileProject,
    ProfileSkill,
    _now_iso,
    default_profile_path,
)


CV_SKILLS = (
    ("python", "backend"),
    ("typescript", "language"),
    ("javascript", "language"),
    ("java", "language"),
    ("rust", "language"),
    ("go", "language"),
    ("react.js", "frontend"),
    ("next.js", "frontend"),
    ("tailwind css", "frontend"),
    ("express.js", "backend"),
    ("nestjs", "backend"),
    ("fastapi", "backend"),
    ("prisma", "backend"),
    ("langchain", "ai"),
    ("langgraph", "ai"),
    ("rag", "ai"),
    ("qdrant", "ai"),
    ("multi-agent", "ai"),
    ("mcp", "ai"),
    ("docker", "devops"),
    ("kubernetes", "devops"),
    ("aws", "cloud"),
    ("gcp", "cloud"),
    ("xgboost", "ml"),
    ("pytorch", "ml"),
    ("tensorflow", "ml"),
    ("scikit-learn", "ml"),
    ("transformer", "ml"),
    ("llm", "ml"),
    ("sql", "data"),
    ("postgres", "data"),
    ("mongodb", "data"),
    ("redis", "data"),
    ("kafka", "data"),
    ("rest api", "backend"),
    ("graphql", "backend"),
    ("websockets", "backend"),
    ("flutter", "mobile"),
    ("swift", "mobile"),
)


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def build_seed_profile(cv_text: str, github_repos: list[dict[str, Any]]) -> CandidateProfile:
    cv_norm = _normalize(cv_text)
    skills: list[ProfileSkill] = []
    for needle, category in CV_SKILLS:
        if needle in cv_norm:
            excerpt = _excerpt(cv_text, needle)
            skills.append(
                ProfileSkill(
                    name=needle,
                    category=category,
                    evidence=Evidence(
                        source="cv",
                        locator="data/candidate/raw/misbahul_muttaqin_cv.txt",
                        excerpt=excerpt,
                        confidence=0.95,
                    ),
                )
            )
    experience: list[ProfileExperience] = []
    if "backend developer" in cv_norm and "study first" in cv_norm:
        experience.append(
            ProfileExperience(
                role="Backend Developer",
                organization="Study First",
                start="Aug 2025",
                end="Oct 2025",
                highlights=(
                    "Built RESTful backend (Express.js, TypeScript) modeling users, courses, roles, and content",
                    "Built authentication middleware, request validation, and error-handling patterns",
                    "Iterated quickly against evolving product requirements",
                ),
                evidence=Evidence(
                    source="cv",
                    locator="data/candidate/raw/misbahul_muttaqin_cv.txt",
                    excerpt="Backend Developer, Study First — Aug to Oct 2025",
                    confidence=0.95,
                ),
            )
        )
    if "frontend engineer intern" in cv_norm and "gatxel" in cv_norm:
        experience.append(
            ProfileExperience(
                role="Frontend Engineer Intern",
                organization="Gatxel",
                start="Jan 2025",
                end="Mar 2025",
                highlights=(
                    "Built responsive and accessible frontend interfaces with React.js and Tailwind CSS",
                    "Integrated RESTful APIs into frontend workflows via Git/GitHub",
                    "Iterated on UI implementation based on evolving requirements",
                ),
                evidence=Evidence(
                    source="cv",
                    locator="data/candidate/raw/misbahul_muttaqin_cv.txt",
                    excerpt="Frontend Engineer Intern, Gatxel — Jan to Mar 2025",
                    confidence=0.95,
                ),
            )
        )
    if "it manager" in cv_norm and "180 degrees" in cv_norm:
        experience.append(
            ProfileExperience(
                role="IT Manager",
                organization="180 Degrees Consulting — Universitas Airlangga",
                start="May 2026",
                end="Present",
                highlights=(
                    "Rebuilt department's flagship competition platform (Laravel to Next.js + Prisma + TanStack Query)",
                    "Owned end-to-end participant experience: registration, member management, document submission, stage tracking",
                    "Carried the platform from migration through production deployment and live maintenance",
                ),
                evidence=Evidence(
                    source="cv",
                    locator="data/candidate/raw/misbahul_muttaqin_cv.txt",
                    excerpt="IT Manager, 180 Degrees Consulting Universitas Airlangga",
                    confidence=0.9,
                ),
            )
        )
    education: list[ProfileEducation] = []
    if "universitas airlangga" in cv_norm:
        education.append(
            ProfileEducation(
                institution="Universitas Airlangga",
                degree="Bachelor of Information Systems",
                start="Jul 2024",
                end="Present",
                evidence=Evidence(
                    source="cv",
                    locator="data/candidate/raw/misbahul_muttaqin_cv.txt",
                    excerpt="Universitas Airlangga, Surabaya, Indonesia — Bachelor of Information Systems | Jul 2024 to Present",
                    confidence=0.95,
                ),
            )
        )
    projects: list[ProfileProject] = []
    for repo in github_repos[:20]:
        if repo.get("fork"):
            continue
        name = repo.get("name", "")
        if not name:
            continue
        stack = []
        if repo.get("language"):
            stack.append(repo["language"])
        if name.lower() in {"greenly", "xninetzy", "edulearn", "cervana", "slara"}:
            stack.extend(["AI", "Multi-agent", "RAG"])
        projects.append(
            ProfileProject(
                title=name,
                role="Author",
                summary=repo.get("description") or "GitHub public repository",
                stack=tuple(s for s in dict.fromkeys(stack)),
                links=(
                    ProfileLink(
                        label="GitHub",
                        url=repo.get("html_url", ""),
                        evidence=Evidence(
                            source="github",
                            locator=f"github.com/misbahul45/{name}",
                            excerpt=f"{name}: {repo.get('description') or ''} [{repo.get('language', '?')}, {repo.get('stargazers_count', 0)} stars]",
                            confidence=1.0,
                        ),
                    ),
                ),
                evidence=Evidence(
                    source="github",
                    locator="github.com/misbahul45",
                    excerpt=f"Public repo '{name}' (language={repo.get('language')}, stars={repo.get('stargazers_count', 0)})",
                    confidence=1.0,
                ),
            )
        )
    links: list[ProfileLink] = [
        ProfileLink(
            label="GitHub",
            url="https://github.com/misbahul45",
            evidence=Evidence(
                source="github",
                locator="github.com/misbahul45",
                excerpt="Public profile — 48 non-fork repos, 35 followers",
                confidence=1.0,
            ),
        ),
        ProfileLink(
            label="Portfolio",
            url="https://misbahulportfolio.netlify.app/",
            evidence=Evidence(
                source="github",
                locator="github.com/misbahul45",
                excerpt="blog field of GitHub profile",
                confidence=1.0,
            ),
        ),
    ]
    summary = (
        "Information Systems student at Universitas Airlangga building full-stack and AI-powered products end to end. "
        "Experience spans production web platforms, AI/RAG systems, agentic architectures, and real-world product evaluation. "
        "Develops and ships software under XNINETZY Labs to explore how AI becomes useful, reliable products rather than "
        "isolated prototypes."
    )
    return CandidateProfile(
        full_name="Misbahul Muttaqin",
        email="misbahulmuttaqin395@gmail.com",
        phone="+62 856-4920-4151",
        location="Gresik / Surabaya, Indonesia",
        headline="Full-Stack + AI Engineer — Information Systems @ Universitas Airlangga",
        summary=summary,
        education=tuple(education),
        experience=tuple(experience),
        projects=tuple(projects),
        skills=tuple(skills),
        links=tuple(links),
        updated_at=_now_iso(),
    )


def _excerpt(text: str, needle: str, *, window: int = 80) -> str:
    norm = _normalize(text)
    idx = norm.find(needle)
    if idx < 0:
        return ""
    start = max(0, idx - window // 2)
    end = min(len(norm), idx + len(needle) + window // 2)
    return norm[start:end]


__all__ = [
    "build_seed_profile",
    "default_profile_path",
]
