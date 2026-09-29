import asyncio
from datetime import date, datetime

from app.models.schemas import TripRequest
from app.providers.destination import _from_fixture
from app.providers.geocode import resolve_city
from app.services.itinerary import DayPick, ItineraryPicks, plan_with_claude, validate
from app.services.scheduler import ScheduleInput, build_days

GOA = resolve_city("Goa")
REQ = TripRequest(origin="Kolkata", destination="Goa", start_date=date(2026, 11, 12),
                  end_date=date(2026, 11, 15), travellers=2, budget=60000)
DATA = _from_fixture(GOA, REQ.start_date, REQ.end_date, 2)


def test_validate_drops_unknown_duplicate_and_out_of_range():
    picks = ItineraryPicks(days=[
        DayPick(day=1, title="Beaches", place_ids=["p-baga-beach", "p-made-up", "p-calangute-beach"]),
        DayPick(day=2, title="Old Goa", place_ids=["p-bom-jesus", "p-baga-beach"]),
        DayPick(day=9, title="Nope", place_ids=["p-se-cathedral"]),
    ], tips=["Rent a scooter", " "])
    ai = validate(picks, DATA.places, n_days=4)
    assert ai.assignment == {1: ["p-baga-beach", "p-calangute-beach"], 2: ["p-bom-jesus"]}
    assert ai.titles[2] == "Old Goa"
    assert ai.tips == ["Rent a scooter"]


def test_scheduler_follows_assignment():
    hotel = next(h for h in DATA.hotels if h.id == "h-candolim-sands")
    assignment = {2: ["p-bom-jesus", "p-se-cathedral"], 3: ["p-palolem-beach"]}
    si = ScheduleInput(
        req=REQ, arrival=datetime(2026, 11, 12, 9, 0),
        departure=datetime(2026, 11, 15, 16, 0), departure_mode="flight",
        hotel=hotel, places=DATA.places, restaurants=DATA.restaurants, place_tags=DATA.place_tags,
        activity_budget=10000, food_budget=10000, city_lat=GOA.lat, city_lng=GOA.lng,
        assignment=assignment, titles={2: "Churches of Old Goa"},
    )
    days, _ = build_days(si)
    visited = {d.number: [s.ref_id for s in d.slots if s.kind == "place"] for d in days}
    assert visited[1] == [] and visited[4] == []
    assert set(visited[2]) == {"p-bom-jesus", "p-se-cathedral"}
    assert visited[3] == ["p-palolem-beach"]
    assert days[1].title == "Churches of Old Goa"


def test_no_api_key_means_no_claude_call():
    hotel = DATA.hotels[0]
    result = asyncio.run(plan_with_claude(REQ, GOA, hotel, DATA.places, DATA.place_tags,
                                          datetime(2026, 11, 12, 9),
                                          datetime(2026, 11, 15, 16), 5000))
    assert result is None
