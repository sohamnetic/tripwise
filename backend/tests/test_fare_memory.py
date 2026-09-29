"""Remembering real fares from live searches and using them for estimates later."""

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlmodel import delete

from app.db import RouteFare, get_session, init_db
from app.models.schemas import TransportOption
from app.providers import fare_memory, flights
from app.providers.geocode import resolve_city
from app.providers.transport import estimate_flights

FIX = Path(__file__).parent / "fixtures" / "live"
GOA, CCU, DEL = resolve_city("Goa"), resolve_city("Kolkata"), resolve_city("Delhi")
DAY = date(2026, 12, 3)


@pytest.fixture(autouse=True)
def clean():
    init_db()
    with get_session() as s:
        s.exec(delete(RouteFare))
        s.commit()


def _flight(price, service="6E 123 · non-stop", minutes=150, estimate=False):
    t = datetime(2026, 12, 3, 7, 0)
    return TransportOption(id=f"f{price}", mode="flight", carrier="IndiGo", service=service, from_city="Delhi",
                           to_city="Goa", depart=t, arrive=t + timedelta(minutes=minutes), duration_min=minutes,
                           price_per_person=price, total_price=price, is_estimate=estimate)


def test_remembers_cheapest_non_stop_and_takes_the_median_over_dates():
    fare_memory.remember("DEL", "GOI", DAY, [_flight(5200), _flight(4100, "AI 1 / AI 2 · 1 stop", 400), _flight(6000)])
    fare_memory.remember("DEL", "GOI", DAY + timedelta(days=7), [_flight(4800)])
    fare_memory.remember("DEL", "GOI", DAY + timedelta(days=14), [_flight(6400)])
    t = fare_memory.typical("DEL", "GOI")
    assert (t.price, t.samples, t.duration_min) == (5200, 3, 150)  # the 1-stop ₹4,100 doesn't count


def test_same_date_is_updated_not_duplicated():
    fare_memory.remember("DEL", "GOI", DAY, [_flight(5200)])
    fare_memory.remember("DEL", "GOI", DAY, [_flight(5600)])
    assert fare_memory.typical("DEL", "GOI").samples == 1 and fare_memory.typical("DEL", "GOI").price == 5600


def test_other_direction_is_used_and_old_or_estimated_fares_are_not():
    fare_memory.remember("GOI", "DEL", DAY, [_flight(5000)])
    assert fare_memory.typical("DEL", "GOI").price == 5000
    fare_memory.remember("DEL", "BOM", DAY, [_flight(3000, estimate=True)])
    assert fare_memory.typical("DEL", "BOM") is None
    with get_session() as s:
        s.add(RouteFare(id="DEL-CCU-old", route="DEL-CCU", travel_date=DAY, cheapest=4000, duration_min=130,
                        seen_at=datetime.now(timezone.utc) - timedelta(days=200)))
        s.commit()
    assert fare_memory.typical("DEL", "CCU") is None


def test_estimates_use_real_fares_when_known():
    distance_based = estimate_flights(DEL, GOA, DAY, 2, False, DAY, DAY + timedelta(days=4))[0]
    fare_memory.remember("DEL", "GOI", DAY, [_flight(4450, minutes=155)])
    real_based = estimate_flights(DEL, GOA, DAY, 2, False, DAY, DAY + timedelta(days=4))[0]
    assert real_based.price_per_person == 4450 != distance_based.price_per_person
    assert real_based.duration_min == 155 and real_based.is_estimate
    assert "1 real search on this route" in real_based.service
    assert distance_based.service.endswith("typical fare")


def test_live_search_feeds_the_memory():
    load = lambda name: json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))

    async def fake_serpapi(params, ttl_hours, stale_days=0):
        return load(f"flights_{params['departure_id']}_{params['arrival_id']}".lower())

    with patch.object(flights, "serpapi", fake_serpapi):
        out, back = asyncio.run(flights.search_flights(CCU, GOA, date(2026, 11, 12), date(2026, 11, 16), 2))
    t = fare_memory.typical("CCU", "GOI")
    assert t and t.samples == 1
    non_stop = [o.price_per_person for o in out if "non-stop" in o.service]
    assert t.price == min(non_stop)
