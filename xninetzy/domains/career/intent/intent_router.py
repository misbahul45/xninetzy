from __future__ import annotations

import re
from dataclasses import dataclass, field


VALID_WORK_MODES = {"remote", "hybrid", "onsite", "any"}
_VALID_EMPLOYMENT_TYPES = {"full_time", "part_time", "contract", "internship", "freelance"}
_VALID_SENIORITIES = {"intern", "junior", "mid", "senior", "lead", "principal"}


_WORK_MODE_PATTERNS = (
    (re.compile(r"\b(remote|work from home|wfh|anywhere)\b", re.IGNORECASE), "remote"),
    (re.compile(r"\bhybrid\b", re.IGNORECASE), "hybrid"),
    (re.compile(r"\b(onsite|on-site|in[- ]office|in[- ]person)\b", re.IGNORECASE), "onsite"),
)


_SENIORITY_HINTS = (
    ("intern", re.compile(r"\b(intern|internship|magang)\b", re.IGNORECASE)),
    ("junior", re.compile(r"\b(junior|entry[- ]level|fresh[ -]?grad|new[ -]?grad)\b", re.IGNORECASE)),
    ("mid", re.compile(r"\b(mid[- ]?level|intermediate)\b", re.IGNORECASE)),
    ("senior", re.compile(r"\b(senior|sr\.?)\b", re.IGNORECASE)),
    ("lead", re.compile(r"\b(lead|staff)\b", re.IGNORECASE)),
    ("principal", re.compile(r"\b(principal|distinguished|head of)\b", re.IGNORECASE)),
)


_EMPLOYMENT_HINTS = (
    ("internship", re.compile(r"\b(intern|internship|magang)\b", re.IGNORECASE)),
    ("part_time", re.compile(r"\bpart[- ]time\b", re.IGNORECASE)),
    ("contract", re.compile(r"\b(contract|contractor|freelance)\b", re.IGNORECASE)),
    ("full_time", re.compile(r"\b(full[- ]?time|permanent)\b", re.IGNORECASE)),
)


_COUNTRY_TOKENS = (
    ("ID", re.compile(r"\b(?:indonesia|jakart[a]?|surabay[a]?|bandung|medan|kalibrr|glints|dealls|jobstreet|lowongan)\b", re.IGNORECASE)),
    ("US", re.compile(r"\b(?:usa|u\.s\.a|united states|america|new york|san francisco|seattle|austin)\b", re.IGNORECASE)),
    ("SG", re.compile(r"\b(?:singapore)\b", re.IGNORECASE)),
    ("DE", re.compile(r"\b(?:germany|berlin|munich)\b", re.IGNORECASE)),
    ("GB", re.compile(r"\b(?:united kingdom|uk|london)\b", re.IGNORECASE)),
    ("JP", re.compile(r"\b(?:japan|tokyo|osaka)\b", re.IGNORECASE)),
    ("AU", re.compile(r"\b(?:australia|sydney|melbourne)\b", re.IGNORECASE)),
    ("MY", re.compile(r"\b(?:malaysia|kuala lumpur)\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class CareerSearchIntent:
    raw_query: str
    role_terms: tuple[str, ...]
    location: str
    work_mode: str
    seniority: str
    employment_type: str
    country_code: str
    posted_within_days: int
    needs_sampling: bool = False
    debug: dict = field(default_factory=dict)


_GENERIC_TERMS = {"jobs", "job", "work", "role", "position", "lowongan", "career"}


def parse_intent(
    query: str,
    *,
    country: str = "",
    work_mode: str = "any",
    posted_within_days: int = 0,
) -> CareerSearchIntent:
    cleaned = (query or "").strip()
    role_terms = _extract_role_terms(cleaned)
    detected_work_mode = _detect_work_mode(cleaned, override=work_mode)
    detected_seniority = _detect_seniority(cleaned)
    detected_employment = _detect_employment(cleaned)
    detected_country = country.strip().upper() if country else _detect_country(cleaned)
    substantive_terms = [t for t in role_terms if t not in _GENERIC_TERMS]
    needs_sampling = (
        not substantive_terms
        or (
            detected_work_mode == "any"
            and "remote" in cleaned.lower()
        )
    )
    return CareerSearchIntent(
        raw_query=cleaned,
        role_terms=tuple(role_terms),
        location=cleaned,
        work_mode=detected_work_mode,
        seniority=detected_seniority,
        employment_type=detected_employment,
        country_code=detected_country,
        posted_within_days=int(posted_within_days or 0),
        needs_sampling=needs_sampling,
        debug={
            "role_terms": role_terms,
            "work_mode_detected": detected_work_mode,
            "seniority_detected": detected_seniority,
            "employment_detected": detected_employment,
            "country_detected": detected_country,
        },
    )


def _extract_role_terms(text: str) -> list[str]:
    parts = re.split(r"[,;\n]+", text)
    tokens: list[str] = []
    for part in parts:
        words = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,30}", part)
        for word in words:
            lowered = word.lower()
            if lowered in {"in", "on", "at", "for", "with", "and", "the", "a", "an", "of", "to"}:
                continue
            if any(re.search(p, word) for p, _ in _WORK_MODE_PATTERNS):
                continue
            if any(re.search(p, word) for _, p in _SENIORITY_HINTS):
                continue
            if lowered in {"id", "us", "sg", "jp", "uk", "de", "au", "my"}:
                continue
            tokens.append(lowered)
    return tokens


def _detect_work_mode(text: str, *, override: str) -> str:
    if override and override.lower() in VALID_WORK_MODES and override.lower() != "any":
        return override.lower()
    for pattern, label in _WORK_MODE_PATTERNS:
        if pattern.search(text):
            return label
    return "any"


def _detect_seniority(text: str) -> str:
    for label, pattern in _SENIORITY_HINTS:
        if pattern.search(text):
            return label
    return ""


def _detect_employment(text: str) -> str:
    for label, pattern in _EMPLOYMENT_HINTS:
        if pattern.search(text):
            return label
    return ""


def _detect_country(text: str) -> str:
    for code, pattern in _COUNTRY_TOKENS:
        if pattern.search(text):
            return code
    return ""
