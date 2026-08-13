"""Wikimedia Commons / Openverse image search clients.

ADR 0010 (`docs/adr/0010-topic-image-retrieval.md`).

The only place these two APIs are called (.claude/rules/ai.md) — nothing outside `ai/`
should call them directly. Used by the orchestrator's `TaskType.TOPIC_IMAGE_SEARCH`
(`ai/orchestrator/orchestrator.py`): Wikimedia Commons primary, Openverse fallback, no LLM
synthesis step — this is a retrieval feature, not a generation one.

Both providers are keyless for the tier this MVP needs:
- **Wikimedia Commons** (`commons.wikimedia.org/w/api.php`) — fully keyless, no auth at all.
- **Openverse** (`api.openverse.org`) — anonymous requests work out of the box at a lower
  rate limit (100 req/hour at the time this was written); an optional OAuth2 client-
  credentials app (`OPENVERSE_CLIENT_ID`/`OPENVERSE_CLIENT_SECRET`, registered at
  https://api.openverse.org/v1/auth_tokens/register/) raises that ceiling, per Openverse's
  own docs. Confirmed here: the anonymous tier is what's actually used unless both env vars
  are set — there's no hard requirement to register an app for this fallback to work.

Per `docs/SECURITY.md#ai-specific-risks`, a student's study topic leaves the system to a
third-party provider here, same as any other AI-adjacent external call — treated the same
way: never logged (query text/response bodies are never included in log output or in the
error messages these clients raise, since exception `str()`s of HTTP errors can embed the
request URL/query params).
"""

from __future__ import annotations

import os
import re

import httpx

from ai.image_search.cache import get_cached_result, set_cached_result
from ai.orchestrator.schemas import TopicImageResult

_WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"
_OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"
_OPENVERSE_TOKEN_URL = "https://api.openverse.org/v1/auth_tokens/token/"
_TIMEOUT_SECONDS = 15.0
_USER_AGENT = (
    "Lumora-AI-Tutor/1.0 (educational study tool; topic image retrieval, ADR 0010)"
)


class WikimediaError(RuntimeError):
    """Raised when the Wikimedia Commons API call fails or is misconfigured."""


class OpenverseError(RuntimeError):
    """Raised when the Openverse API call fails or is misconfigured."""


class WikimediaClient:
    """Thin wrapper around the Wikimedia Commons `action=query` search API. Keyless."""

    async def search_image(self, query: str) -> TopicImageResult | None:
        """Return the best Commons image match for `query`, or `None` if there isn't a
        usable one (a real, expected outcome for niche topics — ADR 0010's Tradeoffs
        section — not an error).
        """
        cache_hit, cached = await get_cached_result(query, "wikimedia")
        if cache_hit:
            return cached

        result = await self._fetch(query)
        await set_cached_result(query, "wikimedia", result)
        return result

    async def _fetch(self, query: str) -> TopicImageResult | None:
        """The only place the Wikimedia Commons HTTP call happens."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
                response = await http_client.get(
                    _WIKIMEDIA_API_URL,
                    headers={"User-Agent": _USER_AGENT},
                    params={
                        "action": "query",
                        "generator": "search",
                        "gsrsearch": query,
                        "gsrnamespace": "6",  # File namespace — includes non-image media.
                        "gsrlimit": "1",
                        "prop": "imageinfo",
                        "iiprop": "url|mime|extmetadata",
                        "format": "json",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # normalize every failure to WikimediaError;
            # deliberately not interpolating `exc` (its `str()` can embed the request URL,
            # which carries the raw query text — never logged, per docs/SECURITY.md).
            error_name = exc.__class__.__name__
            raise WikimediaError(
                f"Wikimedia Commons search failed: {error_name}"
            ) from exc

        return _parse_wikimedia_result(payload)


class OpenverseClient:
    """Thin wrapper around the Openverse image search API.

    Anonymous/keyless by default. If `OPENVERSE_CLIENT_ID`/`OPENVERSE_CLIENT_SECRET` are
    both set, an OAuth2 client-credentials token is fetched and used for a higher rate
    limit — optional, not required for this fallback to function.
    """

    def __init__(
        self, client_id: str | None = None, client_secret: str | None = None
    ) -> None:
        self._client_id = client_id or os.environ.get("OPENVERSE_CLIENT_ID")
        self._client_secret = client_secret or os.environ.get("OPENVERSE_CLIENT_SECRET")

    async def search_image(self, query: str) -> TopicImageResult | None:
        """Return the best Openverse image match for `query`, or `None` if there isn't a
        usable one (same "no good match is a real outcome" contract as `WikimediaClient`).
        """
        cache_hit, cached = await get_cached_result(query, "openverse")
        if cache_hit:
            return cached

        result = await self._fetch(query)
        await set_cached_result(query, "openverse", result)
        return result

    async def _fetch(self, query: str) -> TopicImageResult | None:
        """The only place the Openverse HTTP call happens."""
        try:
            headers = {"User-Agent": _USER_AGENT}
            auth_header = await self._auth_header()
            if auth_header:
                headers.update(auth_header)

            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
                response = await http_client.get(
                    _OPENVERSE_API_URL,
                    headers=headers,
                    params={"q": query, "page_size": "1"},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # normalize every failure to OpenverseError;
            # deliberately not interpolating `exc` for the same raw-query-text reason as
            # `WikimediaClient._fetch`.
            raise OpenverseError(
                f"Openverse search failed: {exc.__class__.__name__}"
            ) from exc

        return _parse_openverse_result(payload)

    async def _auth_header(self) -> dict[str, str] | None:
        """Exchange `OPENVERSE_CLIENT_ID`/`OPENVERSE_CLIENT_SECRET` for a bearer token, or
        `None` if either is unset (anonymous request).

        Fetches a fresh token per search rather than caching one across calls — this is
        the low-traffic fallback path (Wikimedia is primary), so the extra round trip isn't
        worth the added complexity of tracking token expiry.
        """
        if not self._client_id or not self._client_secret:
            return None
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http_client:
                response = await http_client.post(
                    _OPENVERSE_TOKEN_URL,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "client_credentials",
                    },
                )
                response.raise_for_status()
                token = response.json().get("access_token")
        except Exception:  # noqa: BLE001 - token fetch is an optional rate-limit boost;
            # fall back to an anonymous request rather than failing the whole search.
            return None
        return {"Authorization": f"Bearer {token}"} if token else None


def _parse_wikimedia_result(payload: dict) -> TopicImageResult | None:
    pages = payload.get("query", {}).get("pages")
    if not isinstance(pages, dict) or not pages:
        return None

    page = next(iter(pages.values()))
    imageinfo = page.get("imageinfo")
    if not isinstance(imageinfo, list) or not imageinfo:
        return None
    info = imageinfo[0]

    mime_type = info.get("mime")
    image_url = info.get("url")
    source_url = info.get("descriptionurl")
    extmetadata = info.get("extmetadata") or {}
    license_value = _extmetadata_value(
        extmetadata, "LicenseShortName"
    ) or _extmetadata_value(extmetadata, "License")
    attribution = _strip_html(_extmetadata_value(extmetadata, "Artist"))

    # Attribution/license are required fields (ADR 0010) — a Commons page missing either
    # isn't a usable result. Skip it (treat as no match) rather than fabricate a generic
    # placeholder that would misrepresent the actual licensing terms.
    if (
        not isinstance(mime_type, str)
        or not mime_type.lower().startswith("image/")
        or not image_url
        or not source_url
        or not license_value
        or not attribution
    ):
        return None

    return TopicImageResult(
        image_url=image_url,
        attribution=attribution,
        license=license_value,
        source_url=source_url,
    )


def _extmetadata_value(extmetadata: dict, key: str) -> str | None:
    entry = extmetadata.get(key)
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _strip_html(value: str | None) -> str | None:
    """Wikimedia's `Artist` extmetadata field is often an HTML fragment (e.g. a linked
    username) — strip tags for a plain-text attribution string. Not a full HTML parser,
    just enough to drop `<...>` markup; entities (`&amp;` etc.) are left as-is since the
    result is display text, not re-parsed HTML.
    """
    if value is None:
        return None
    text = re.sub(r"<[^>]+>", "", value).strip()
    return text or None


def _parse_openverse_result(payload: dict) -> TopicImageResult | None:
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return None
    result = results[0]

    image_url = result.get("url")
    source_url = result.get("foreign_landing_url")
    attribution = result.get("attribution")
    license_name = result.get("license")
    license_version = result.get("license_version")
    license_value = (
        f"{license_name.upper()} {license_version}".strip() if license_name else None
    )

    # Same required-fields contract as `_parse_wikimedia_result` — skip rather than
    # fabricate a placeholder attribution/license.
    if not image_url or not source_url or not license_value or not attribution:
        return None

    return TopicImageResult(
        image_url=image_url,
        attribution=attribution,
        license=license_value,
        source_url=source_url,
    )
