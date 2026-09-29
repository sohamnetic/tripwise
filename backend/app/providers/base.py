"""SerpApi client with an SQLite cache, so the free quota (250 searches/month) lasts."""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlmodel import delete

from ..config import get_settings
from ..db import CacheEntry, get_session

log = logging.getLogger(__name__)
SERPAPI_URL = "https://serpapi.com/search.json"


class ProviderError(RuntimeError):
    pass


def _key(params: dict) -> str:
    raw = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str) -> dict | None:
    with get_session() as s:
        entry = s.get(CacheEntry, key)
        if not entry:
            return None
        expires = entry.expires_at if entry.expires_at.tzinfo else entry.expires_at.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return None
        return json.loads(entry.value)


def _cache_put(key: str, value: dict, ttl_hours: float) -> None:
    now = datetime.now(timezone.utc)
    with get_session() as s:
        # drop expired entries so the free database tier doesn't fill up with old searches
        s.exec(delete(CacheEntry).where(CacheEntry.expires_at < now))
        s.merge(CacheEntry(key=key, value=json.dumps(value), expires_at=now + timedelta(hours=ttl_hours)))
        s.commit()


async def serpapi(params: dict, ttl_hours: float) -> dict:
    """GET a SerpApi search, served from cache when fresh. `params` must not include the key."""
    settings = get_settings()
    if not settings.serpapi_key:
        raise ProviderError("SERPAPI_KEY is not set. Add it to backend/.env or turn DEMO_MODE back on.")
    key = _key(params)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    log.info("SerpApi request: engine=%s", params.get("engine"))
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.get(SERPAPI_URL, params={**params, "api_key": settings.serpapi_key})
    try:
        data = resp.json()
    except ValueError:
        raise ProviderError(f"SerpApi returned HTTP {resp.status_code}") from None
    if resp.status_code != 200 or "error" in data:
        err = data.get("error", f"HTTP {resp.status_code}")
        # "no results" is a valid, cacheable answer; anything else is a real failure
        if "hasn't returned any results" not in err:
            raise ProviderError(f"SerpApi: {err}")
    _cache_put(key, data, ttl_hours)
    return data
