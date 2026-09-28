"""Career acquisition adapters."""
from __future__ import annotations

from xninetzy.os.career.acquisition.adapters.remoteok_career import (
    RemoteOkCareerAdapter, build_remoteok_career_adapter,
)
from xninetzy.os.career.acquisition.adapters.research_browser_career import (
    ResearchBrowserCareerAdapter, build_research_browser_career_adapter,
)

__all__ = [
    "RemoteOkCareerAdapter", "build_remoteok_career_adapter",
    "ResearchBrowserCareerAdapter", "build_research_browser_career_adapter",
]
