import asyncio
from datetime import date

import pytest

from app.models.schemas import TripRequest
from app.providers.geocode import UnknownCityError, resolve_city
from app.providers.transport import estimate_buses, estimate_trains
from app.services.budget import BudgetTooLowError
from app.services.planner import build_plan


def make(**kw) -> TripRequest:
    base = dict(origin="Kolkata", destination="Goa", start_date=date(2026, 11, 12),
                end_date=date(2026, 11, 16), travellers=2, budget=60000, style="balanced",
                interests=["beaches", "history"])
    base.update(kw)
    return TripRequest(**base)


def plan(**kw):
    return asyncio.run(build_plan(make(**kw)))


def test_balanced_plan_fits_budget_and_is_consistent():
    p = plan()
    assert p.summary.within_budget and p.summary.total_cost <= 60000
    assert p.summary.total_cost == sum(l.spent for l in p.budget)
    assert len(p.days) == 5
    assert p.days[0].slots[0].kind == "arrival" and p.days[-1].slots[-1].kind == "departure"
    # every place in the itinerary exists in the data and has coordinates
    ids = {pl.id for pl in p.places}
    for d in p.days:
        for s in d.slots:
            if s.kind == "place":
                assert s.ref_id in ids and s.lat and s.lng
    # no place is visited twice
    visited = [s.ref_id for d in p.days for s in d.slots if s.kind == "place"]
    assert len(visited) == len(set(visited))


def test_slots_are_in_time_order():
    p = plan()
    for d in p.days:
        # times before 05:00 belong to the night after (e.g. back from a club at 00:15)
        times = [s.start if s.start >= "05:00" else f"+{s.start}" for s in d.slots
                 if s.kind not in ("arrival", "departure")]
        assert times == sorted(times, key=lambda x: (x.startswith("+"), x)), (d.number, times)


def test_tight_budget_uses_train_and_cheap_hotel():
    p = plan(budget=22000, style="budget")
    assert p.outbound.mode == "train"
    assert p.summary.total_cost <= 22000
    assert p.hotel.nightly_price <= 2200


def test_comfort_budget_gets_better_hotel():
    cheap = plan(budget=40000, style="budget")
    rich = plan(budget=250000, style="comfort")
    assert rich.hotel.stars > cheap.hotel.stars
    assert rich.outbound.mode == "flight"


def test_impossible_budget_reports_minimum():
    with pytest.raises(BudgetTooLowError) as e:
        plan(budget=3000)
    assert e.value.minimum > 3000


def test_group_of_five_needs_three_rooms():
    p = plan(travellers=5, budget=150000)
    assert p.hotel.rooms == 3 and p.summary.rooms == 3


def test_weekday_only_places_land_on_right_day():
    p = plan(start_date=date(2026, 11, 10), end_date=date(2026, 11, 15), interests=["shopping"], budget=80000)
    for d in p.days:
        for s in d.slots:
            if s.ref_id == "p-anjuna-market":
                assert d.date.weekday() == 2  # Wednesday
            if s.ref_id == "p-arpora-night-market":
                assert d.date.weekday() == 5  # Saturday


def test_balanced_mid_budget_flies_instead_of_40h_sleeper():
    p = plan(budget=60000, style="balanced", start_date=date(2026, 10, 29), end_date=date(2026, 11, 2))
    assert p.outbound.mode == "flight"
    assert p.summary.within_budget


def test_days_are_geographically_grouped_and_full_days_are_used():
    from app.services.scheduler import _km
    for style, budget in [("budget", 22000), ("balanced", 60000), ("comfort", 150000)]:
        p = plan(budget=budget, style=style, start_date=date(2026, 10, 29), end_date=date(2026, 11, 2))
        for d in p.days:
            stops = [s for s in d.slots if s.kind == "place"]
            for a in stops:
                for b in stops:
                    assert _km(a.lat, a.lng, b.lat, b.lng) <= 50, (style, d.number, a.title, b.title)
            if 1 < d.number < len(p.days):
                assert stops, (style, d.number, "full day with nothing planned")


def test_balanced_hotel_is_not_a_hostel_and_comfort_is_central():
    assert plan(budget=60000, style="balanced").hotel.stars >= 3
    assert plan(budget=150000, style="comfort").hotel.id == "h-sinquerim-spa"


def test_flight_preference_is_respected():
    assert plan(transport="flight", budget=50000, style="budget").outbound.mode == "flight"


def test_no_trains_to_manali_but_buses_from_delhi():
    delhi, manali = resolve_city("Delhi"), resolve_city("Manali")
    assert estimate_trains(delhi, manali, date(2026, 11, 12), 2, True) == []
    assert estimate_buses(delhi, manali, date(2026, 11, 12), 2, True)


def test_unknown_city():
    with pytest.raises(UnknownCityError):
        resolve_city("Atlantis")
