"""Provider-neutral internet search result contract (ADR 0012,
`docs/adr/0012-internet-search-integration.md`).

`ai.internet_search.tavily_client`/`ai.internet_search.brave_client` each normalize their
provider's raw response into `InternetSearchResult` -- deliberately excludes Tavily's
`answer` field and any Brave-specific metadata: ADR 0012's synthesis-pass decision means a
provider-generated answer is never a supported field here, only ranked retrieval results
for Gemini to synthesize from (`ai/orchestrator/orchestrator.py:_run_internet_search`).
"""

from __future__ import annotations

import enum
import re
from datetime import datetime

from pydantic import BaseModel, Field

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_query(query: str) -> str:
    """Trim/collapse internal whitespace, casefold.

    Preserves punctuation/dates/quoted phrases/domain filters -- those change search
    meaning, so only whitespace/case are normalized (ADR 0012). Used both to populate
    `InternetSearchResult.normalized_query` and as the cache-key basis
    (`ai/internet_search/cache.py`) -- the two must stay in sync, hence one shared function.
    """
    return _WHITESPACE_RE.sub(" ", query.strip()).casefold()


class SearchProvider(enum.StrEnum):
    """Which provider produced an `InternetSearchResult` (ADR 0012)."""

    TAVILY = "tavily"
    BRAVE = "brave"


class InternetSearchItem(BaseModel):
    """One ranked search result, normalized across providers."""

    title: str
    url: str
    snippet: str
    published_at: datetime | None = None
    score: float | None = None


class InternetSearchResult(BaseModel):
    """A provider-neutral search response -- grounding material for Gemini to synthesize
    from, never returned to a student directly (ADR 0012's synthesis-pass decision: search
    results are never the answer).
    """

    query: str
    normalized_query: str
    provider: SearchProvider
    results: tuple[InternetSearchItem, ...] = Field(default_factory=tuple)
    fetched_at: datetime
