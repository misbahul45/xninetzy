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
from xninetzy.os.research.sources.registry import register_adapter
from xninetzy.os.research.sources.browser_session import quote_url as _quote


logger = logging.getLogger(__name__)


class KalibrrAdapter(BrowserScrapingAdapter):
    id = "kalibrr"
    category = SourceCategory.COMPANY
    base_url = "https://www.kalibrr.com"
    rate_limit = RateLimit(requests_per_minute=4, burst=1)
    retry = RetryPolicy(max_attempts=2, backoff_base_seconds=2.0, backoff_max_seconds=8.0)
    circuit_breaker = CircuitBreaker(failure_threshold=3, open_duration_seconds=600.0)

    SEARCH_URL = "https://www.kalibrr.com/c/jobs/search?keyword=__QUERY__&location=Indonesia"

    def build_search_url(self, query: str, **kwargs) -> str:
        return self.SEARCH_URL.replace("__QUERY__", _quote(query))

    @property
    def wait_selector(self) -> str:
        return ".k-list-item, .k-job-card, [data-test='job-card']"

    def parse_jobs(self, html: str, *, query: str, limit: int) -> list:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".k-list-item") or soup.select("[data-test='job-card']")
        records = []
        for card in cards:
            title_a = card.select_one(".k-list-item__title, a.job-title, h2 a")
            if title_a is None:
                continue
            title = title_a.get_text(strip=True)
            href = title_a.get("href", "")
            if not title:
                continue
            slug = href.rstrip("/").split("/")[-1] if href else ""
            full_url = (
                f"{self.base_url}{href}" if href.startswith("/") else href
            ) or self.base_url
            company_el = card.select_one(".k-list-item__company, .company-name")
            company = company_el.get_text(strip=True) if company_el else ""
            loc_el = card.select_one(".k-list-item__location, .job-location")
            location = loc_el.get_text(strip=True) if loc_el else ""
            posted_el = card.select_one(".k-list-item__posted-at, time")
            posted_at = posted_el.get_text(strip=True) if posted_el else None
            desc_el = card.select_one(".k-list-item__desc, .job-description, p")
            snippet = (desc_el.get_text(" ", strip=True) if desc_el else "") + f" | Location: {location}"
            identifiers = {"kalibrr_slug": slug, "location": location}
            records.append(
                self.make_record(
                    title=title,
                    company=company,
                    url=full_url,
                    snippet=snippet,
                    posted_at=posted_at,
                    identifiers=identifiers,
                    confidence=0.55,
                )
            )
            if len(records) >= max(1, min(limit, 100)):
                break
        return records


register_adapter(KalibrrAdapter())
