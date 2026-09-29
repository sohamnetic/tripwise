"""Parsers and the full planner, run on real SerpApi responses saved from a live Kolkata → Goa
search (tests/fixtures/live). No network, no quota used."""

import asyncio
import json
import re
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app.models.schemas import TripRequest
from app.providers import flights, live_destination
from app.providers.geocode import resolve_city
from app.providers.live_destination import PLUS_CODE, area_of, clean_name, parse_hotels, parse_places, parse_restaurants
from app.services.planner import build_plan

FIX = Path(__file__).parent / "fixtures" / "live"
GOA, CCU = resolve_city("Goa"), resolve_city("Kolkata")
load = lambda name: json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


def test_area_and_name_cleanup():
    assert area_of("FQX8+9HJ, Candolim, Goa", GOA) == "Candolim"
    assert area_of("9V3M+QG9, Consua, Goa 403712", GOA) == "Consua"
    assert area_of("FQVH+43H, Goa 403001", GOA) == "Goa"
    assert area_of("1152, opp. Our Lady Of Health Chapel, Mazal Waddo, Anjuna, Goa 403509", GOA) == "Anjuna"
    assert clean_name("Bogmallo Beach Resort - 5 Star Hotel in Goa", GOA) == "Bogmallo Beach Resort"
    assert clean_name("Calangute Beach, Goa", GOA) == "Calangute Beach"
    assert clean_name("Nerul Eat Street Restaurant and Bar- Serves tasty Goan and Seafood", GOA) == "Nerul Eat Street Restaurant and Bar"


def test_messy_real_world_names():
    manali = resolve_city("Manali")
    fancy = "𝗧𝗵𝗲 𝗵𝗲𝗮𝗹𝘁𝗵𝘆 𝗸𝗶𝘁𝗰𝗵𝗲𝗻 pure veg & vegan restaurant & best juices הקפה הטוב ביותר , 𝐛𝐞𝐬𝐭 coffee"
    cleaned = clean_name(fancy, manali)
    assert cleaned.startswith("The healthy kitchen") and len(cleaned) <= 42 and cleaned.isascii()
    assert clean_name("BABUMOSHAI MULTI CUISINE FOOD JOINT", manali) == "Babumoshai Multi Cuisine Food Joint"
    jaipur = resolve_city("Jaipur")
    assert clean_name("The Collectors Loft-A Luxury Private Suit Near Jaipur City Center", jaipur) == "The Collectors Loft"
    assert area_of("Amer, Jaipur Heritage (M Corp.) (Part), Jaipur, Rajasthan 302002", jaipur) == "Amer"
    assert area_of("Jaipur Nagar Nigam Area, Jaipur, Rajasthan", jaipur) == "Jaipur"


def test_real_attractions_skip_hotels_taxis_and_duplicates():
    for city in ("manali", "jaipur", "coorg"):
        c = resolve_city(city)
        places, _ = parse_places(load(f"{city}_attractions"), c)
        names = [p.name.lower() for p in places]
        assert not any(re.search(r"\b(taxi|igloo stay|hotel|resort)\b", n) for n in names), names
        seat = [n for n in names if "seat" in n]
        assert len(seat) <= 1, seat  # Raja's Seat / Raja Seat Garden / The seat of the king
        jogini = [n for n in names if "jogini" in n]
        assert len(jogini) <= 1, jogini


def test_real_places_have_clean_areas_and_beaches_are_beaches():
    places, _ = parse_places(load("goa_attractions"), GOA)
    assert len(places) >= 15
    for p in places:
        assert not PLUS_CODE.match(p.area) and not re.search(r"\d", p.area), p.area
        if re.search(r"\bbeach\b", p.name, re.I):
            assert p.category == "beaches", p.name


def test_real_hotels_and_restaurants():
    hotels = parse_hotels(load("goa_hotels"), GOA, date(2026, 11, 12), date(2026, 11, 16), 2)
    assert len(hotels) >= 10
    assert all(h.nightly_price > 0 and h.total_price == h.nightly_price * 4 for h in hotels)
    assert all(" - " not in h.name for h in hotels)
    assert len({h.id for h in hotels}) == len(hotels)
    rests = parse_restaurants(load("goa_restaurants"), GOA)
    assert len(rests) >= 10 and all(150 <= r.cost_per_person <= 3000 for r in rests)
    assert len({r.cost_per_person for r in rests}) > 1  # estimated from type, not one flat default


def test_real_flights_are_per_person_prices():
    out = flights.parse_flights(load("flights_ccu_goi"), CCU, GOA, 2, "out", [])
    assert out and all(o.total_price == o.price_per_person * 2 and not o.is_estimate for o in out)
    assert all(o.depart.date() == date(2026, 11, 12) for o in out)


def test_full_live_plan_from_saved_responses(monkeypatch):
    """The whole planner in live mode, with SerpApi answered from the saved files."""
    from app.config import get_settings

    async def fake_serpapi(params, ttl_hours, stale_days=0):
        eng = params["engine"]
        if eng == "google_flights":
            return load(f"flights_{params['departure_id']}_{params['arrival_id']}".lower())
        if eng == "google_hotels":
            return load("goa_hotels")
        return load("goa_restaurants" if "restaurant" in params["q"] else "goa_attractions")

    monkeypatch.setattr(get_settings(), "demo_mode", False)
    with patch.object(flights, "serpapi", fake_serpapi), patch.object(live_destination, "serpapi", fake_serpapi):
        req = TripRequest(origin="Kolkata", destination="Goa", start_date=date(2026, 11, 12), end_date=date(2026, 11, 16),
                          travellers=2, budget=60000, style="balanced", interests=["beaches", "food"])
        p = asyncio.run(build_plan(req))

    assert p.data_mode == "live" and p.summary.within_budget
    # balanced travellers get AC 3-tier rather than 40 hours in Sleeper
    assert p.outbound.mode == "flight" or p.outbound.service != "Sleeper (SL)"
    for d in p.days:
        assert "+" not in d.title, d.title  # no plus codes in day titles
    assert any(s.kind == "place" for d in p.days for s in d.slots)
    for u in p.upgrades:
        assert 0 < u.extra_cost <= p.summary.remaining
