"""Extraction quality evaluator.

Scores a normalized record based on field completeness, selector
confidence, and sanity checks. Returns a typed ``QualityVerdict`` that
the MCP surface consumes.

Quality is deliberately bounded to ``[0.0, 1.0]``. Empty descriptions,
unknown companies, and invalid URLs trigger warnings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QualityVerdict:
    score: float
    field_confidence: dict[str, float]
    warnings: tuple[str, ...]
    recommended_action: str  # "ACCEPT" | "REVIEW" | "REJECT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "field_confidence": {
                k: round(v, 3) for k, v in self.field_confidence.items()
            },
            "warnings": list(self.warnings),
            "recommended_action": self.recommended_action,
        }


@dataclass
class ExtractionQualityEvaluator:
    """Field-weighted quality scorer.

    Default weights assume the canonical job record defined by the brief.
    Override ``weights`` to specialize per source.
    """

    weights: dict[str, float] = field(
        default_factory=lambda: {
            "title": 0.20,
            "company": 0.20,
            "url": 0.15,
            "location": 0.10,
            "description": 0.20,
            "posted_at": 0.05,
            "salary": 0.05,
            "skills": 0.05,
        }
    )
    accept_threshold: float = 0.65
    review_threshold: float = 0.45

    def evaluate(self, record: dict[str, Any]) -> QualityVerdict:
        field_conf: dict[str, float] = {}
        warnings: list[str] = []
        weighted = 0.0
        total_weight = 0.0

        for field_name, weight in self.weights.items():
            total_weight += weight
            value = record.get(field_name)
            conf = self._confidence(field_name, value)
            if conf == 0.0 and weight >= 0.10:
                warnings.append(f"MISSING_{field_name.upper()}")
            field_conf[field_name] = conf
            weighted += weight * conf

        # Hard guards.
        url = record.get("url") or ""
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            warnings.append("INVALID_URL")
            weighted -= 0.15
        description = record.get("description")
        if isinstance(description, str) and len(description.strip()) < 30:
            warnings.append("EMPTY_DESCRIPTION")
            weighted -= 0.10

        score = max(0.0, min(1.0, weighted / max(total_weight, 1e-9)))

        if score >= self.accept_threshold:
            action = "ACCEPT"
        elif score >= self.review_threshold:
            action = "REVIEW"
        else:
            action = "REJECT"

        return QualityVerdict(
            score=score,
            field_confidence=field_conf,
            warnings=tuple(warnings),
            recommended_action=action,
        )

    @staticmethod
    def _confidence(field_name: str, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return 0.0
            if field_name == "url":
                return 0.95 if stripped.startswith(("http://", "https://")) else 0.2
            return min(1.0, 0.6 + 0.4 * min(len(stripped) / 200.0, 1.0))
        if isinstance(value, list):
            return 0.95 if value else 0.0
        if isinstance(value, (int, float)):
            return 0.95 if value > 0 else 0.0
        return 0.6
