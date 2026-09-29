"""Hotels, places and restaurants at the destination."""

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..config import get_settings
from ..models.schemas import City, Hotel, Place, Restaurant
from ..services import links

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


class DemoDataMissingError(ValueError):
    pass


@dataclass
class DestinationData:
    hotels: list[Hotel]
    places: list[Place]
    restaurants: list[Restaurant]
    place_tags: dict[str, list[str]]  # extra interest tags per place id


def demo_destinations() -> list[str]:
    return sorted(p.stem.replace("-", " ").title() for p in FIXTURES.glob("*.json"))


def _fixture_path(city: City) -> Path:
    return FIXTURES / (re.sub(r"[^a-z0-9]+", "-", city.name.lower()).strip("-") + ".json")


def _from_fixture(city: City, checkin: date, checkout: date, pax: int) -> DestinationData:
    path = _fixture_path(city)
    if not path.exists():
        raise DemoDataMissingError(
            f"Demo mode only has data for: {', '.join(demo_destinations())}. "
            "Add API keys and set DEMO_MODE=false to plan other destinations."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    rooms = links.rooms_for(pax)
    nights = (checkout - checkin).days

    hotels = []
    for h in raw["hotels"]:
        hotel = Hotel(**h, rooms=rooms, total_price=h["nightly_price"] * rooms * nights)
        hotel.links = links.hotel_links(hotel.name, city, checkin, checkout, pax)
        hotels.append(hotel)

    places, tags = [], {}
    for p in raw["places"]:
        bookable = p.pop("bookable", False)
        tags[p["id"]] = p.pop("tags", [])
        place = Place(**p)
        place.links = links.activity_links(place.name, city, place.lat, place.lng, bookable)
        places.append(place)

    restaurants = []
    for r in raw["restaurants"]:
        rest = Restaurant(**r)
        rest.links = [links.Link(label="Map", url=links.google_maps(rest.lat, rest.lng, f"{rest.name}, {rest.area}"))]
        restaurants.append(rest)

    return DestinationData(hotels, places, restaurants, tags)


async def get_destination_data(city: City, checkin: date, checkout: date, pax: int) -> DestinationData:
    if get_settings().demo_mode:
        return _from_fixture(city, checkin, checkout, pax)
    from .live_destination import fetch_live  # SerpApi hotels + Google Maps (step 2)
    return await fetch_live(city, checkin, checkout, pax)
