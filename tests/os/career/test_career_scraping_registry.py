"""Test that new career scraping tools are registered in the canonical registry."""

from __future__ import annotations

from xninetzy.tools.registry import get_all_tools


def test_canonical_registry_contains_new_career_tools() -> None:
    tools = get_all_tools()
    names = {getattr(t, "name", None) for t in tools}
    for required in {
        "career_scrape_diagnose",
        "career_scrape_run",
        "career_clear_cache",
        "career_validate_source",
        "career_source_health",
    }:
        assert required in names, f"missing tool: {required}"


def test_existing_kaggle_tools_still_present() -> None:
    """Regression: Kaggle tools must still be registered (no breakage)."""

    tools = get_all_tools()
    names = {getattr(t, "name", None) for t in tools}
    for existing in {
        "career_search_jobs",
        "career_get_job",
        "career_adapter_health",
        "career_run_eval",
        "career_open_application",
        "career_fill_application",
    }:
        assert existing in names, f"regression: missing {existing}"
