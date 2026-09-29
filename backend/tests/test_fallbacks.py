"""What happens when live searches aren't possible (daily cap, quota used up, SerpApi down),
and the per-visitor limits. No network."""

import asyncio
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import delete

from app.config import get_settings
from app.db import ApiCall, CacheEntry, PlanRequest, get_session, init_db
from app.main import app
from app.models.schemas import TripRequest
from app.providers import base, flights, live_destination, open_places
from app.providers.base import ProviderError, SearchLimitError, serpapi
from app.providers.geocode import resolve_city
from app.providers.transport import search_transport
from app.services import limits
from app.services.planner import build_plan
from tests.open_fixtures import replay

FIX = Path(__file__).parent / "fixtures" / "live"
load = lambda name: json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))
GOA, CCU = resolve_city("Goa"), resolve_city("Kolkata")
START, END = date(2026, 11, 12), date(2026, 11, 16)


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    with get_session() as s:
        for table in (ApiCall, CacheEntry, PlanRequest):
            s.exec(delete(table))
        s.commit()


@pytest.fixture
def live(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "serpapi_key", "test-key")
    return settings


def _serpapi_answers(monkeypatch, handler):
    """Route SerpApi's HTTP calls to `handler(request) -> httpx.Response`."""
    real = httpx.AsyncClient
    monkeypatch.setattr(base.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


# ---- the SerpApi client ---------------------------------------------------------------

def test_daily_cap_stops_live_searches(live, monkeypatch):
    monkeypatch.setattr(live, "serpapi_daily_limit", 2)
    calls = []
    _serpapi_answers(monkeypatch, lambda r: calls.append(r) or httpx.Response(200, json={"ok": len(calls)}))
    asyncio.run(serpapi({"q": "a"}, 1))
    asyncio.run(serpapi({"q": "b"}, 1))
    assert asyncio.run(serpapi({"q": "a"}, 1)) == {"ok": 1}  # cached answers are free
    with pytest.raises(SearchLimitError):
        asyncio.run(serpapi({"q": "c"}, 1))
    assert len(calls) == 2


def test_out_of_searches_uses_an_older_copy_when_allowed(live, monkeypatch):
    key = base._key({"q": "sights"})
    with get_session() as s:
        s.add(CacheEntry(key=key, value=json.dumps({"old": True}),
                         expires_at=datetime.now(timezone.utc) - timedelta(days=3)))
        s.commit()
    _serpapi_answers(monkeypatch, lambda r: httpx.Response(429, json={"error": "Your account has run out of searches."}))
    assert asyncio.run(serpapi({"q": "sights"}, 1, stale_days=60)) == {"old": True}
    with pytest.raises(SearchLimitError):
        asyncio.run(serpapi({"q": "sights"}, 1))  # no older copy allowed (e.g. flight prices)


def test_network_failure_is_a_provider_error(live, monkeypatch):
    def down(request):
        raise httpx.ConnectError("down")
    _serpapi_answers(monkeypatch, down)
    with pytest.raises(ProviderError):
        asyncio.run(serpapi({"q": "x"}, 1))


# ---- fallbacks ----------------------------------------------------------------------------

async def _no_searches(params, ttl_hours, stale_days=0):
    raise SearchLimitError("Today's live searches are used up.")


def test_flights_fall_back_to_estimates(live):
    with patch.object(flights, "serpapi", _no_searches):
        out, back = asyncio.run(search_transport(CCU, GOA, START, END, 2))
    est = [o for o in out + back if o.mode == "flight"]
    assert est and all(o.is_estimate and o.carrier == "Any airline" for o in est)
    assert any(o.mode == "train" for o in out)  # other modes are unaffected


async def _hotels_down(params, ttl_hours, stale_days=0):
    if params["engine"] == "google_hotels":
        raise SearchLimitError("used up")
    return load("goa_restaurants" if "restaurant" in params["q"] else "goa_attractions")


def test_hotels_fall_back_to_typical_prices(live):
    with patch.object(live_destination, "serpapi", _hotels_down):
        data = asyncio.run(live_destination.fetch_live(GOA, START, END, 3))
    assert [h.stars for h in data.hotels] == [2, 3, 4, 5]
    h = data.hotels[0]
    assert h.is_estimate and h.rooms == 2 and h.total_price == h.nightly_price * 2 * 4
    assert h.links and "booking.com" in h.links[0].url
    assert data.places and data.restaurants


def test_no_google_and_no_open_data_gives_a_clear_message(live):
    async def nothing(city):
        raise ProviderError("no open data")
    with patch.object(live_destination, "serpapi", _no_searches), patch.object(open_places, "fetch_open", nothing), \
            pytest.raises(ProviderError, match="Try again tomorrow"):
        asyncio.run(live_destination.fetch_live(GOA, START, END, 2))


def test_open_data_when_google_isnt_available(live, monkeypatch):
    monkeypatch.setattr(live, "geoapify_key", "test-key")
    with patch.object(live_destination, "serpapi", _no_searches), patch.object(open_places, "cached_get", replay("Goa")):
        data = asyncio.run(live_destination.fetch_live(GOA, START, END, 2))
    assert {"Basilica of Bom Jesus", "Fort Aguada", "Calangute Beach"} <= {p.name for p in data.places}
    assert all(not p.rating_known for p in data.places) and all(not r.rating_known for r in data.restaurants)
    assert all(h.is_estimate for h in data.hotels)
    assert {c.label for c in data.credits} >= {"Wikidata", "© OpenStreetMap contributors", "Powered by Geoapify"}


def test_whole_plan_from_open_data(live, monkeypatch):
    """Manali with no Google results at all: sights from Wikidata + Wikivoyage, food from OpenStreetMap."""
    monkeypatch.setattr(live, "geoapify_key", "test-key")
    req = TripRequest(origin="Delhi", destination="Manali", start_date=START, end_date=END,
                      travellers=2, budget=45000, style="balanced", interests=["nature"], transport="any")
    with patch.object(flights, "serpapi", _no_searches), patch.object(live_destination, "serpapi", _no_searches), \
            patch.object(open_places, "cached_get", replay("Manali")):
        p = asyncio.run(build_plan(req))
    visited = [s.title for d in p.days for s in d.slots if s.kind == "place"]
    assert len(visited) >= 5 and p.summary.within_budget
    assert any("Wikivoyage" in c.label for c in p.credits)
    meals = [s for d in p.days for s in d.slots if s.kind == "meal"]
    assert meals and all(s.cost > 0 for s in meals)


def test_whole_plan_with_no_live_prices_is_labelled(live):
    req = TripRequest(origin="Kolkata", destination="Goa", start_date=START, end_date=END,
                      travellers=2, budget=60000, style="balanced", interests=["beaches"], transport="flight")
    with patch.object(flights, "serpapi", _no_searches), patch.object(live_destination, "serpapi", _hotels_down):
        p = asyncio.run(build_plan(req))
    assert p.hotel.is_estimate and p.outbound.is_estimate
    assert any("Live flight and hotel prices weren't available" in w for w in p.warnings)
    for u in p.upgrades:
        if u.id.startswith("hotel:h-est"):  # no made-up ratings for typical-price stays
            assert "rated" not in u.detail and u.title.startswith("Upgrade to a")


# ---- per-visitor limits ----------------------------------------------------------------------

def test_new_trips_are_limited_but_replans_are_not(monkeypatch):
    monkeypatch.setattr(get_settings(), "visitor_daily_trips", 2)
    monkeypatch.setattr(get_settings(), "visitor_daily_requests", 5)
    limits.check_and_record("me", "a")
    limits.check_and_record("me", "b")
    limits.check_and_record("me", "a")  # replanning trip a is fine
    with pytest.raises(limits.LimitReachedError, match="2 new trips"):
        limits.check_and_record("me", "c")
    limits.check_and_record("someone-else", "c")  # limits are per visitor
    limits.check_and_record("me", "b")
    limits.check_and_record("me", "a")
    with pytest.raises(limits.LimitReachedError, match="come back tomorrow"):
        limits.check_and_record("me", "a")  # the overall cap on requests


def test_old_requests_stop_counting(monkeypatch):
    monkeypatch.setattr(get_settings(), "visitor_daily_trips", 1)
    with get_session() as s:
        s.add(PlanRequest(client="me", trip_key="old", at=datetime.now(timezone.utc) - timedelta(hours=25)))
        s.commit()
    limits.check_and_record("me", "new")


def test_api_says_429_when_over_the_limit(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "visitor_daily_trips", 1)
    me = hashlib.sha256(b"tripwise:testclient").hexdigest()[:24]
    with get_session() as s:
        s.add(PlanRequest(client=me, trip_key="kolkata|jaipur|2026-11-12|2026-11-16"))
        s.commit()
    body = {"origin": "Kolkata", "destination": "Goa", "start_date": "2026-11-12", "end_date": "2026-11-16",
            "travellers": 2, "budget": 60000, "style": "balanced", "interests": [], "transport": "any"}
    with TestClient(app) as c:
        r = c.post("/api/trips", json=body)
    assert r.status_code == 429 and "new trips today" in r.json()["detail"]


def test_ip_is_hashed_and_proxy_address_used():
    from starlette.requests import Request
    req = Request({"type": "http", "headers": [(b"x-forwarded-for", b"203.0.113.9, 10.0.0.1")], "client": ("10.0.0.1", 1)})
    cid = limits.client_id(req)
    assert "203.0.113.9" not in cid and cid == hashlib.sha256(b"tripwise:203.0.113.9").hexdigest()[:24]


def test_a_bug_in_open_data_gives_a_message_not_a_crash(live):
    async def broken(city):
        raise TypeError("expected string or bytes-like object")
    with patch.object(live_destination, "serpapi", _no_searches), patch.object(open_places, "fetch_open", broken), \
            pytest.raises(ProviderError, match="Try again tomorrow"):
        asyncio.run(live_destination.fetch_live(GOA, START, END, 2))
