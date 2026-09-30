"""City lookup from the bundled table (airport codes, rail/road access, coordinates)."""

import json
import math
from functools import lru_cache
from pathlib import Path

from ..models.schemas import City, CityOption

_DATA = Path(__file__).resolve().parent.parent / "data" / "cities.json"


class UnknownCityError(ValueError):
    pass


@lru_cache
def _cities() -> list[dict]:
    return json.loads(_DATA.read_text(encoding="utf-8"))


def _to_city(row: dict) -> City:
    return City(
        name=row["name"],
        state=row["state"],
        country=row["country"],
        lat=row["lat"],
        lng=row["lng"],
        iata=row["iata"],
        has_rail=row["has_rail"],
        has_road=row["has_road"],
        international=row["country"] != "India",
    )


def search_cities(query: str, limit: int = 8) -> list[City]:
    q = query.strip().lower()
    if not q:
        return [_to_city(r) for r in _cities()[:limit]]
    starts, contains = [], []
    for row in _cities():
        names = [row["name"].lower(), *row["aliases"]]
        if any(n.startswith(q) for n in names):
            starts.append(row)
        elif any(q in n for n in names):
            contains.append(row)
    return [_to_city(r) for r in (starts + contains)[:limit]]


def all_city_options() -> list[CityOption]:
    return [CityOption(name=r["name"], state=r["state"], country=r["country"], aliases=r["aliases"]) for r in _cities()]


def resolve_city(name: str) -> City:
    q = name.strip().lower()
    for row in _cities():
        if q == row["name"].lower() or q in row["aliases"]:
            return _to_city(row)
    matches = search_cities(name, limit=1)
    if matches:
        return matches[0]
    raise UnknownCityError(f"Sorry, we don't know '{name}' yet. Try a nearby major city.")


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def city_distance_km(a: City, b: City) -> float:
    return haversine_km(a.lat, a.lng, b.lat, b.lng)
