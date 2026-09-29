"""SerpApi client with a database cache, so the free quota (250 searches/month) lasts.

When the daily cap is reached or SerpApi fails (e.g. the month's searches are used up), callers
that allow it get an older cached copy; otherwise a ProviderError, and the caller falls back to
estimates.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlmodel import delete, func, select

from ..config import get_settings
from ..db import ApiCall, CacheEntry, get_session

log = logging.getLogger(__name__)
SERPAPI_URL = "https://serpapi.com/search.json"
KEEP_EXPIRED_DAYS = 60  # expired entries stay this long as a fallback for data that barely changes


class ProviderError(RuntimeError):
    pass


class SearchLimitError(ProviderError):
    """Today's share of the free searches is used up (or the month's are)."""


def _key(params: dict) -> str:
    raw = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _cache_get(key: str, stale_days: float = 0) -> dict | None:
    """The cached value if fresh, or expired by less than `stale_days`."""
    with get_session() as s:
        entry = s.get(CacheEntry, key)
        if not entry:
            return None
        if _aware(entry.expires_at) + timedelta(days=stale_days) < datetime.now(timezone.utc):
            return None
        return json.loads(entry.value)


def _cache_put(key: str, value: dict, ttl_hours: float) -> None:
    now = datetime.now(timezone.utc)
    with get_session() as s:
        # drop long-expired entries so the free database tier doesn't fill up with old searches
        s.exec(delete(CacheEntry).where(CacheEntry.expires_at < now - timedelta(days=KEEP_EXPIRED_DAYS)))
        s.merge(CacheEntry(key=key, value=json.dumps(value), expires_at=now + timedelta(hours=ttl_hours)))
        s.commit()


def searches_today(provider: str) -> int:
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    with get_session() as s:
        return s.exec(select(func.count()).select_from(ApiCall)
                      .where(ApiCall.provider == provider, ApiCall.at >= midnight)).one()


def _record_search(provider: str) -> None:
    now = datetime.now(timezone.utc)
    with get_session() as s:
        s.exec(delete(ApiCall).where(ApiCall.at < now - timedelta(days=40)))
        s.add(ApiCall(provider=provider, at=now))
        s.commit()


async def _fetch(params: dict) -> dict:
    settings = get_settings()
    if not settings.serpapi_key:
        raise ProviderError("SERPAPI_KEY is not set. Add it to backend/.env or turn DEMO_MODE back on.")
    if settings.serpapi_daily_limit and searches_today("serpapi") >= settings.serpapi_daily_limit:
        raise SearchLimitError("Today's live searches are used up.")
    log.info("SerpApi request: engine=%s", params.get("engine"))
    _record_search("serpapi")
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.get(SERPAPI_URL, params={**params, "api_key": settings.serpapi_key})
    except httpx.HTTPError as e:
        raise ProviderError(f"SerpApi unreachable: {type(e).__name__}") from None
    try:
        data = resp.json()
    except ValueError:
        raise ProviderError(f"SerpApi returned HTTP {resp.status_code}") from None
    if resp.status_code != 200 or "error" in data:
        err = data.get("error", f"HTTP {resp.status_code}")
        # "no results" is a valid, cacheable answer; anything else is a real failure
        if "hasn't returned any results" not in err:
            if "run out of searches" in err.lower() or resp.status_code == 429:
                raise SearchLimitError(f"SerpApi: {err}")
            raise ProviderError(f"SerpApi: {err}")
    return data


async def serpapi(params: dict, ttl_hours: float, stale_days: float = 0) -> dict:
    """GET a SerpApi search, served from cache when fresh. `params` must not include the key.
    If a live search isn't possible, a copy expired by less than `stale_days` is used instead."""
    key = _key(params)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        data = await _fetch(params)
    except ProviderError as e:
        stale = _cache_get(key, stale_days) if stale_days else None
        if stale is not None:
            log.info("SerpApi unavailable (%s); using an older cached copy", e)
            return stale
        raise
    _cache_put(key, data, ttl_hours)
    return data


async def cached_get(url: str, params: dict, ttl_hours: float, secret: dict | None = None,
                     headers: dict | None = None) -> dict:
    """GET a free JSON API (Wikidata, Wikivoyage, Geoapify), cached like SerpApi searches but
    with no daily cap. `secret` (e.g. an API key) is sent but kept out of the cache key."""
    key = _key({"url": url, **params})
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(timeout=25, headers=headers) as client:
            resp = await client.get(url, params={**params, **(secret or {})})
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        stale = _cache_get(key, KEEP_EXPIRED_DAYS)
        if stale is not None:
            return stale
        raise ProviderError(f"{url.split('/')[2]} unavailable: {type(e).__name__}") from None
    _cache_put(key, data, ttl_hours)
    return data
