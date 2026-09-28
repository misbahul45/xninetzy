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


class JobstreetIDAdapter(BrowserScrapingAdapter):
    id = "jobstreet_id"
    category = SourceCategory.COMPANY
    base_url = "https://id.jobstreet.com"
    rate_limit = RateLimit(requests_per_minute=2, burst=1)
    retry = RetryPolicy(max_attempts=2, backoff_base_seconds=3.0, backoff_max_seconds=10.0)
    circuit_breaker = CircuitBreaker(failure_threshold=2, open_duration_seconds=900.0)

    SEARCH_URL = "https://id.jobstreet.com/intern-jobs"

    def build_search_url(self, query: str, **kwargs) -> str:
        return self.SEARCH_URL.replace("__QUERY__", _quote(query))

    @property
    def wait_selector(self) -> str:
        return "a[href*='/job/']"

    def parse_jobs(self, html: str, *, query: str, limit: int) -> list:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("article[data-automation='job-item']") or soup.select("a[href*='/job/']")
        records = []
        for card in cards:
            a = card.select_one("h1.job-title a, .job-title a, a[data-automation='job-title']")
            if a is None:
                a = card.select_one("a[href*='/job']")
            if a is None:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not title:
                continue
            slug = href.rstrip("/").split("/")[-1] if href else ""
            full_url = (
                f"https://id.jobstreet.com{href}" if href.startswith("/") else href
            ) or "https://id.jobstreet.com"
            company_el = card.select_one(".company-name, .job-company-name")
            company = company_el.get_text(strip=True) if company_el else ""
            loc_el = card.select_one(".job-location, ul.job-location li")
            location = loc_el.get_text(" ", strip=True) if loc_el else ""
            posted_el = card.select_one("time.job-date, time")
            posted_at = posted_el.get_text(strip=True) if posted_el else None
            desc_el = card.select_one(".job-description, .job-snippet")
            snippet = (desc_el.get_text(" ", strip=True) if desc_el else "") + f" | Location: {location}"
            identifiers = {"jobstreet_slug": slug, "location": location}
            records.append(
                self.make_record(
                    title=title,
                    company=company,
                    url=full_url,
                    snippet=snippet,
                    posted_at=posted_at,
                    identifiers=identifiers,
                    confidence=0.45,
                )
            )
            if len(records) >= max(1, min(limit, 100)):
                break
        return records


register_adapter(JobstreetIDAdapter())
