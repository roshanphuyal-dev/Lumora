"""Provider-neutral paper search result contract (ADR 0013,
`docs/adr/0013-paper-search-integration.md`).

`ai.paper_search.arxiv_client`/`ai.paper_search.semantic_scholar_client` each normalize
their provider's raw response into `PaperSearchResult` -- mirrors
`ai/internet_search/schemas.py:InternetSearchResult`'s shape almost exactly, adjusted for
paper metadata (authors/abstract/venue/citation_count) instead of web title/snippet. ADR
0013's synthesis-pass decision (same as ADR 0012's for `INTERNET_SEARCH`) means this is
always Gemini's grounding material, never returned to a student directly
(`ai/orchestrator/orchestrator.py:_run_paper_search`).
"""

from __future__ import annotations

import enum
import re
from datetime import date, datetime

from pydantic import BaseModel, Field

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_query(query: str) -> str:
    """Trim/collapse internal whitespace, casefold.

    Same rule and reasoning as `ai/internet_search/schemas.py:normalize_query` -- kept as
    a separate function rather than imported across packages, same layering precedent as
    `ai/prompts/internet_search_synthesis_v1.py`'s `SearchResultItemInput` duplicating
    rather than importing `ai.internet_search.schemas.InternetSearchItem`. Used both to
    populate `PaperSearchResult.normalized_query` and as the cache-key basis
    (`ai/paper_search/cache.py`) -- the two must stay in sync, hence one shared function.
    """
    return _WHITESPACE_RE.sub(" ", query.strip()).casefold()


class PaperSearchProvider(enum.StrEnum):
    """Which provider produced a `PaperSearchResult` (ADR 0013)."""

    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"


class PaperSearchItem(BaseModel):
    """One paper result, normalized across providers.

    `citation_count` is always `None` for arXiv results -- arXiv's API doesn't provide it
    (ADR 0013). `pdf_url` points at the provider's outbound PDF link; this codebase never
    downloads/proxies/stores the PDF itself (arXiv's terms explicitly withhold that
    permission for metadata-only storage, ADR 0013).
    """

    title: str
    authors: tuple[str, ...] = Field(default_factory=tuple)
    abstract: str | None = None
    publication_date: date | None = None
    url: str
    pdf_url: str | None = None
    venue: str | None = None
    citation_count: int | None = None


class PaperSearchResult(BaseModel):
    """A provider-neutral paper search response -- grounding material for Gemini to
    synthesize from, never returned to a student directly (ADR 0013's synthesis-pass
    decision: paper search results are never the answer, mirroring
    `InternetSearchResult`'s same contract).
    """

    query: str
    normalized_query: str
    provider: PaperSearchProvider
    results: tuple[PaperSearchItem, ...] = Field(default_factory=tuple)
    fetched_at: datetime
