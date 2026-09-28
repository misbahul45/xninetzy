from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from xninetzy.os.research.sources.base import (
    CircuitBreaker,
    RateLimit,
    RetryPolicy,
    SourceCategory,
)
from xninetzy.os.research.sources.browser_scraper import BrowserScrapingAdapter
from xninetzy.os.research.sources.browser_session import quote_url as _quote
from xninetzy.os.research.sources.registry import register_adapter


logger = logging.getLogger(__name__)


class GlintsAdapter(BrowserScrapingAdapter):
    id = "glints"
    category = SourceCategory.COMPANY
    base_url = "https://glints.com"
    rate_limit = RateLimit(requests_per_minute=3, burst=1)
    retry = RetryPolicy(max_attempts=2, backoff_base_seconds=2.0, backoff_max_seconds=8.0)
    circuit_breaker = CircuitBreaker(failure_threshold=3, open_duration_seconds=600.0)

    SEARCH_URL = "https://glints.com/id/opportunities/jobs/explore?keyword=__QUERY__&country=ID&locationName=All+Cities+in+Indonesia"

    def build_search_url(self, query: str, **kwargs) -> str:
        return self.SEARCH_URL.replace("__QUERY__", _quote(query))

    @property
    def wait_selector(self) -> str:
        return "article[role='article'], a[aria-label*='Job card title']"

    def parse_jobs(self, html: str, *, query: str, limit: int) -> list:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("article[role='article']") or soup.select("a[aria-label*='Job card title']")
        records = []
        for card in cards:
            a = card if card.name == 'a' else card.select_one("a[aria-label*='Job card title'], h1 a, h2 a")
            if a is None:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not title:
                continue
            slug = href.rstrip("/").split("/")[-1] if href else ""
            full_url = (
                f"https://glints.com{href}" if href.startswith("/") else href
            ) or "https://glints.com"
            company_el = card.select_one(".Opportunityscard__company, .company-name")
            company = company_el.get_text(strip=True) if company_el else ""
            loc_el = card.select_one(".Opportunityscard__location, .job-location")
            location = loc_el.get_text(strip=True) if loc_el else ""
            posted_el = card.select_one("time, .posted-date")
            posted_at = posted_el.get_text(strip=True) if posted_el else None
            desc_el = card.select_one(".Opportunityscard__description, .job-description, p")
            snippet = (desc_el.get_text(" ", strip=True) if desc_el else "") + f" | Location: {location}"
            identifiers = {"glints_slug": slug, "location": location}
            records.append(
                self.make_record(
                    title=title,
                    company=company,
                    url=full_url,
                    snippet=snippet,
                    posted_at=posted_at,
                    identifiers=identifiers,
                    confidence=0.5,
                )
            )
            if len(records) >= max(1, min(limit, 100)):
                break
        return records


register_adapter(GlintsAdapter())
