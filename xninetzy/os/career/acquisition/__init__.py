"""Career acquisition shared engine.

Layer that sits between Xninetzy's canonical research/adapter infrastructure
and the career-domain MCP surface.

This package must NOT duplicate:

- ``SourceAdapter`` (lives in ``xninetzy/os/research/sources/base.py``)
- ``RateLimiter`` / ``CircuitBreakerGuard`` / ``retry_async`` (lives in
  ``xninetzy/os/research/sources/rate_limit.py``)
- ``BrowserGateway`` (lives in ``xninetzy/os/auth/browser/gateway.py``)
- ``SearchCache`` (lives in ``xninetzy/os/career/search_cache.py``)

It does provide:

- explicit per-source ``SourcePolicy`` enforcement
- centralized transport selection (``TransportPlan``)
- structured failure taxonomy (``FailureTaxonomy``)
- page readiness detection (``PageReadinessDetector``)
- selector fallback chains (``SelectorStrategy``)
- pagination strategies (``PaginationStrategy``)
- per-source health metrics (``SourceHealthService``)
- extraction quality evaluation (``ExtractionQualityEvaluator``)
- composition root: ``CareerAcquisitionService``

Every public function returns structured, typed data — never raises
untyped exceptions across the boundary.
"""

from __future__ import annotations

from xninetzy.os.career.acquisition.adapter import (
    CareerSourceAdapter,
    JobDetail,
    ListingCandidate,
    NormalizedJob,
)
from xninetzy.os.career.acquisition.adapters import (
    RemoteOkCareerAdapter,
    build_remoteok_career_adapter,
    build_research_browser_career_adapter,
)
from xninetzy.os.career.acquisition.auth_detector import (
    AuthState,
    AuthVerdict,
    AuthenticationDetector,
    build_default_detector,
)
from xninetzy.os.career.acquisition.extraction import (
    FieldProvenance,
    SelectorCandidate,
    SelectorChain,
    SelectorExtractor,
    SelectorStrategy,
)
from xninetzy.os.career.acquisition.failures import (
    FailureClassification,
    FailureClassifier,
    FailureTaxonomy,
)
from xninetzy.os.career.acquisition.health import (
    SourceHealthRecord,
    SourceHealthService,
)
from xninetzy.os.career.acquisition.pagination import (
    CursorPagination,
    InfiniteScrollPagination,
    LoadMorePagination,
    NoPagination,
    PageNumberPagination,
    PaginationMode,
)
from xninetzy.os.career.acquisition.policy import (
    PolicyStatus,
    PolicyVerdict,
    SourcePolicy,
    SourcePolicyGate,
    build_default_gate,
)
from xninetzy.os.career.acquisition.quality import (
    ExtractionQualityEvaluator,
    QualityVerdict,
)
from xninetzy.os.career.acquisition.readiness import (
    PageReadinessDetector,
    ReadinessCondition,
    ReadinessConditionType,
    ReadinessResult,
)
from xninetzy.os.career.acquisition.service import (
    AcquisitionResult,
    CareerAcquisitionService,
    CareerSearchRequest,
    SourceOutcome,
)
from xninetzy.os.career.acquisition.transport_selector import (
    CacheState,
    HealthSnapshot,
    SourceDefinition,
    Transport,
    TransportPlan,
    TransportSelector,
    default_definitions,
)

__all__ = [
    "AcquisitionResult",
    "AuthState",
    "AuthVerdict",
    "AuthenticationDetector",
    "CacheState",
    "CareerAcquisitionService",
    "CareerSearchRequest",
    "CareerSourceAdapter",
    "CursorPagination",
    "ExtractionQualityEvaluator",
    "FailureClassification",
    "FailureClassifier",
    "FailureTaxonomy",
    "FieldProvenance",
    "HealthSnapshot",
    "InfiniteScrollPagination",
    "JobDetail",
    "ListingCandidate",
    "LoadMorePagination",
    "NoPagination",
    "NormalizedJob",
    "PageNumberPagination",
    "PageReadinessDetector",
    "PaginationMode",
    "PolicyStatus",
    "PolicyVerdict",
    "QualityVerdict",
    "ReadinessCondition",
    "ReadinessConditionType",
    "ReadinessResult",
    "RemoteOkCareerAdapter",
    "SelectorCandidate",
    "SelectorChain",
    "SelectorExtractor",
    "SelectorStrategy",
    "SourceDefinition",
    "SourceHealthRecord",
    "SourceHealthService",
    "SourceOutcome",
    "SourcePolicy",
    "SourcePolicyGate",
    "Transport",
    "TransportPlan",
    "TransportSelector",
    "build_default_detector",
    "build_default_gate",
    "build_remoteok_career_adapter",
    "build_research_browser_career_adapter",
    "default_definitions",
]
