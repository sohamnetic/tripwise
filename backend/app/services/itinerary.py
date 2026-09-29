"""Claude picks and groups places into days. It never sees or produces prices for the plan;
the scheduler turns its choices into timed slots and all costs are computed in Python.

If no API key is set, or the call fails, the deterministic scheduler is used on its own.
"""

import json
import logging
from dataclasses import dataclass
from datetime import timedelta

import anthropic
from pydantic import BaseModel

from ..config import get_settings
from ..models.schemas import City, Hotel, Place, TripRequest

log = logging.getLogger(__name__)

SYSTEM = """You are an expert Indian travel planner. You choose which attractions a traveller \
visits on each day of their trip and give practical local tips.

Rules:
- Use ONLY place ids from the list you are given. Never invent places.
- Group places that are close together (use lat/lng and area) on the same day to minimise travel.
- Respect opening hours and weekday-only places (e.g. a Wednesday market only on a Wednesday).
- Arrival and departure days are lighter; full days get 2-4 places, fewer if a place takes 4+ hours.
- Favour the traveller's interests, but keep some variety.
- Keep the sum of fee_per_person x travellers within the activity budget.
- Evening places (opening at 17:00 or later) go last in a day's list.
- Tips must be specific to the destination and practical (transport, timing, etiquette, safety, what to carry). \
Do not mention prices."""


class DayPick(BaseModel):
    day: int
    title: str
    place_ids: list[str]


class ItineraryPicks(BaseModel):
    days: list[DayPick]
    tips: list[str]


@dataclass
class AiItinerary:
    assignment: dict[int, list[str]]
    titles: dict[int, str]
    tips: list[str]


def _payload(req: TripRequest, dest: City, hotel: Hotel, places: list[Place], tags: dict[str, list[str]],
             arrival, departure, activity_budget: int) -> str:
    days = []
    for i in range(req.nights + 1):
        d = req.start_date + timedelta(days=i)
        info = {"day": i + 1, "date": d.isoformat(), "weekday": d.strftime("%A")}
        if i == 0:
            info["arrives_at"] = arrival.strftime("%H:%M")
        if i == req.nights:
            info["departs_at"] = departure.strftime("%H:%M")
        days.append(info)
    return json.dumps({
        "destination": f"{dest.name}, {dest.state}, {dest.country}",
        "travellers": req.travellers,
        "style": req.style,
        "interests": req.interests,
        "activity_budget_inr": activity_budget,
        "hotel": {"name": hotel.name, "area": hotel.area, "lat": round(hotel.lat, 4), "lng": round(hotel.lng, 4)},
        "days": days,
        "places": [
            {"id": p.id, "name": p.name, "category": p.category, "tags": tags.get(p.id, []), "area": p.area,
             "rating": p.rating, "lat": round(p.lat, 4), "lng": round(p.lng, 4),
             "fee_per_person": p.fee_per_person, "duration_min": p.duration_min, "hours": p.hours}
            for p in places
        ],
    }, ensure_ascii=False)


def validate(picks: ItineraryPicks, places: list[Place], n_days: int) -> AiItinerary:
    """Drop unknown ids, duplicates and out-of-range days."""
    known = {p.id for p in places}
    seen: set[str] = set()
    assignment, titles = {}, {}
    for day in picks.days:
        if not 1 <= day.day <= n_days:
            continue
        ids = [i for i in day.place_ids if i in known and i not in seen]
        seen.update(ids)
        assignment[day.day] = ids
        titles[day.day] = day.title.strip()[:60]
    return AiItinerary(assignment, titles, [t.strip() for t in picks.tips if t.strip()][:6])


async def plan_with_claude(req: TripRequest, dest: City, hotel: Hotel, places: list[Place],
                           tags: dict[str, list[str]], arrival, departure, activity_budget: int) -> AiItinerary | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=120)
    try:
        response = await client.beta.messages.parse(
            model=settings.anthropic_model,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{
                "role": "user",
                "content": "Plan which places to visit on each day of this trip.\n\n"
                           + _payload(req, dest, hotel, places, tags, arrival, departure, activity_budget),
            }],
            output_format=ItineraryPicks,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIError as e:
        log.warning("Claude itinerary failed, using built-in planner: %s", e)
        return None
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        log.warning("Claude itinerary stopped with %s, using built-in planner", response.stop_reason)
        return None
    ai = validate(response.parsed_output, places, req.nights + 1)
    return ai if any(ai.assignment.values()) else None
