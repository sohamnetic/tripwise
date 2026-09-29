"""The Luxury travel style, on real saved Kolkata → Goa search results (5★ hotels at real prices)."""

import asyncio
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import get_settings
from app.models.schemas import TripRequest
from app.providers import flights, live_destination
from app.services.planner import build_plan

FIX = Path(__file__).parent / "fixtures" / "live"
load = lambda name: json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


async def _saved(params, ttl_hours, stale_days=0):
    engine = params["engine"]
    if engine == "google_flights":
        return load(f"flights_{params['departure_id']}_{params['arrival_id']}".lower())
    if engine == "google_hotels":
        return load("goa_hotels")
    return load("goa_restaurants" if "restaurant" in params["q"] else "goa_attractions")


def _plan(monkeypatch, budget, style):
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    req = TripRequest(origin="Kolkata", destination="Goa", start_date=date(2026, 11, 12), end_date=date(2026, 11, 16),
                      travellers=2, budget=budget, style=style, interests=["beaches", "food"])
    with patch.object(flights, "serpapi", _saved), patch.object(live_destination, "serpapi", _saved):
        return asyncio.run(build_plan(req))


def _dinner_pp(plan):
    dinners = [s for d in plan.days for s in d.slots if s.kind == "meal" and s.title.startswith("Dinner")]
    return sum(s.cost for s in dinners) / len(dinners) / plan.request.travellers


def test_luxury_gets_a_5_star_and_fine_dining_when_the_budget_allows(monkeypatch):
    lux = _plan(monkeypatch, 150000, "luxury")
    comfort = _plan(monkeypatch, 150000, "comfort")
    assert lux.hotel.stars == 5 and lux.summary.within_budget
    assert _dinner_pp(lux) >= 1200 and _dinner_pp(lux) > _dinner_pp(comfort)
    assert not any("5★" in w for w in lux.warnings)


def test_luxury_says_when_the_budget_cant_reach_5_stars(monkeypatch):
    p = _plan(monkeypatch, 60000, "luxury")
    assert p.hotel.stars < 5 and p.summary.within_budget
    note = next(w for w in p.warnings if "5★" in w)
    assert "more would get the cheapest 5★" in note


def test_luxury_offers_more_premium_5_star_stays(monkeypatch):
    p = _plan(monkeypatch, 700000, "luxury")
    hotel_ups = [u for u in p.upgrades if u.kind == "hotel"]
    assert any("ITC Grand" in u.title and u.title.startswith("Go luxury") for u in hotel_ups)
    assert all(0 < u.extra_cost <= p.summary.remaining for u in p.upgrades)


@pytest.mark.parametrize("style", ["budget", "balanced", "comfort", "luxury"])
def test_every_style_fits_its_budget(monkeypatch, style):
    p = _plan(monkeypatch, 100000, style)
    assert p.summary.within_budget and p.days
