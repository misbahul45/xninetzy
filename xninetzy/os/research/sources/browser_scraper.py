from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from urllib.parse import quote_plus


from xninetzy.core.logging import configure_logging
from xninetzy.os.auth.browser.gateway import BrowserGatewayUnavailable
from xninetzy.os.research.sources.base import (
    CircuitBreaker,
    HealthStatus,
    RateLimit,
    RetryPolicy,
    SourceAdapter,
    SourceCategory,
    SourceRecord,
    make_retrieved_at,
)
from xninetzy.os.research.sources.browser_session import (
    BrowserSession,
    FakeBrowserSession,
    make_session,
)
from xninetzy.os.research.sources.rate_limit import (
    CircuitBreakerGuard,
    RateLimiter,
    retry_async,
)


logger = logging.getLogger(__name__)

_TOS_WARNING_TEMPLATE = (
    "Adapter {source} uses owner-gated browser scraping. "
    "Source terms-of-service may restrict automated access. "
    "Owner has accepted risk R6 from design §15. Use sparingly."
)


class _ScrapingAdapter(ABC):
    id: str
    base_url: str
    category: SourceCategory
    rate_limit: RateLimit
    retry: RetryPolicy
    circuit_breaker: CircuitBreaker

    def __init__(
        self,
        *,
        session_factory=None,
        rate_limiter: RateLimiter | None = None,
        breaker: CircuitBreakerGuard | None = None,
    ) -> None:
        self._session_factory = session_factory or make_session
        self._session: BrowserSession | None = None
        self._limiter: RateLimiter = rate_limiter or RateLimiter(
            requests_per_minute=self.rate_limit.requests_per_minute,
            burst=self.rate_limit.burst,
        )
        self._breaker: CircuitBreakerGuard = breaker or CircuitBreakerGuard(
            self.circuit_breaker
        )
        configure_logging()

    async def _get_session(self) -> BrowserSession:
        if self._session is None:
            self._session = self._session_factory()
        return self._session

    async def close(self) -> None:
        if self._session is not None:
            try:
                await self._session.close()
            except Exception:
                pass
            self._session = None

    @abstractmethod
    def build_search_url(self, query: str, **kwargs) -> str: ...

    @abstractmethod
    def parse_jobs(self, html: str, *, query: str, limit: int) -> list[SourceRecord]: ...

    @property
    def wait_selector(self) -> str | None:
        return None

    async def _fetch_html(self, url: str) -> str:
        session = await self._get_session()
        return await session.get_html(url, wait_selector=self.wait_selector)

    def make_record(
        self,
        *,
        title: str,
        company: str,
        url: str,
        snippet: str,
        posted_at: str | None,
        identifiers: dict,
        confidence: float = 0.6,
    ) -> SourceRecord:
        cleaned_title = (title or "(untitled)").strip()
        return SourceRecord(
            title=cleaned_title,
            url=url,
            source=self.id,
            source_type="job",
            published_at=posted_at,
            updated_at=posted_at,
            author=company.strip() or None,
            snippet=snippet[:600],
            content=None,
            language="id",
            license=None,
            retrieved_at=make_retrieved_at(),
            confidence=confidence,
            primary_source=False,
            citation=None,
            identifiers=identifiers,
        )

    async def _scrape(self, query: str, limit: int, **kwargs) -> list[SourceRecord]:
        if not await self._breaker.allow():
            logger.warning("%s breaker open; skipping search", self.id)
            return []
        await self._limiter.acquire()
        url = self.build_search_url(query, **kwargs)
        try:
            html = await retry_async(self.retry, self._fetch_html, url)
        except BrowserGatewayUnavailable as exc:
            logger.warning("%s browser unavailable: %s", self.id, exc)
            await self._breaker.record_failure()
            return []
        except Exception as exc:
            logger.warning("%s fetch failed: %s", self.id, exc)
            await self._breaker.record_failure()
            return []
        await self._breaker.record_success()
        try:
            records = self.parse_jobs(html, query=query, limit=limit)
        except Exception as exc:
            logger.warning("%s parse failed: %s", self.id, exc)
            return []
        return records[: max(1, min(limit, 100))]


class BrowserScrapingAdapter(SourceAdapter, _ScrapingAdapter):
    """SourceAdapter that scrapes a JS-heavy board via the browser gateway."""

    requires_api_key = False

    async def search(
        self, query: str, limit: int = 10, **kwargs: object
    ) -> list[SourceRecord]:
        logger.info(_TOS_WARNING_TEMPLATE.format(source=self.id))
        return await self._scrape(query, limit, **kwargs)

    async def fetch(self, identifier: str) -> SourceRecord | None:
        logger.info(_TOS_WARNING_TEMPLATE.format(source=self.id))
        if not identifier.startswith(("http://", "https://")):
            return None
        if not await self._breaker.allow():
            return None
        await self._limiter.acquire()
        try:
            html = await retry_async(self.retry, self._fetch_html, identifier)
        except Exception as exc:
            logger.warning("%s fetch failed: %s", self.id, exc)
            await self._breaker.record_failure()
            return None
        await self._breaker.record_success()
        try:
            records = self.parse_jobs(html, query="", limit=1)
            return records[0] if records else None
        except Exception:
            return None

    async def health(self) -> HealthStatus:
        return HealthStatus.DEGRADED if not await self._breaker.allow() else HealthStatus.HEALTHY


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_fake_session(html_by_url: dict[str, str]) -> FakeBrowserSession:
    return FakeBrowserSession(html_by_url=html_by_url)


def _quote(value: str) -> str:
    return quote_plus(value or "")


__all__ = [
    "BrowserScrapingAdapter",
    "_ScrapingAdapter",
    "make_fake_session",
]
