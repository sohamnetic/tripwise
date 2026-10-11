"""Remembers the fares live flight searches find, so that when live searches run out, a route's
estimate comes from real prices seen on it instead of a distance formula."""

import re
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlmodel import select

from ..db import RouteFare, get_session
from ..models.schemas import TransportOption

MAX_AGE_DAYS = 90  # fares change with season and demand; older sightings are dropped
# Estimating a hundred destinations for one chat message asks for a hundred routes; one query and a
# few minutes in memory beats a database round trip per route (slow from Vercel to Neon).
CACHE_SECONDS = 300
_cache: tuple[float, dict[str, list[tuple[int, int]]]] | None = None


def clear_cache() -> None:
    global _cache
    _cache = None


def _recent() -> dict[str, list[tuple[int, int]]]:
    """route → [(cheapest, duration_min)] for every recent sighting, cached briefly."""
    global _cache
    if _cache and time.monotonic() - _cache[0] < CACHE_SECONDS:
        return _cache[1]
    since = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    by_route: dict[str, list[tuple[int, int]]] = defaultdict(list)
    with get_session() as s:
        for r in s.exec(select(RouteFare).where(RouteFare.seen_at >= since)).all():
            by_route[r.route].append((r.cheapest, r.duration_min))
    _cache = (time.monotonic(), dict(by_route))
    return _cache[1]


@dataclass
class TypicalFare:
    price: int  # per person
    duration_min: int
    samples: int  # travel dates it's based on


def _route(frm: str, to: str) -> str:
    return f"{frm}-{to}"


def remember(frm: str, to: str, day: date, options: list[TransportOption]) -> None:
    """Store the cheapest of the flights with the fewest stops (a 20-hour two-stop itinerary
    isn't what people mean by the usual fare)."""
    flights = [o for o in options if o.mode == "flight" and not o.is_estimate]
    if not flights:
        return
    fewest = min(_stops(o.service) for o in flights)
    best = [o for o in flights if _stops(o.service) == fewest]
    now = datetime.now(timezone.utc)
    with get_session() as s:
        s.merge(RouteFare(
            id=f"{_route(frm, to)}-{day.isoformat()}", route=_route(frm, to), travel_date=day,
            cheapest=min(o.price_per_person for o in best),
            duration_min=int(statistics.median(o.duration_min for o in best)), seen_at=now,
        ))
        s.commit()
    clear_cache()


def _stops(service: str) -> int:
    """'6E 2451 · non-stop' → 0, 'AI 101 / AI 887 · 1 stop' → 1."""
    if "non-stop" in service:
        return 0
    m = re.search(r"(\d+) stops?", service)
    return int(m.group(1)) if m else 1


def typical(frm: str, to: str) -> TypicalFare | None:
    """The median of the cheapest fares seen on this route (either direction, since fares
    each way are usually similar), or None if no live search has covered it."""
    recent = _recent()
    rows = recent.get(_route(frm, to)) or recent.get(_route(to, frm))
    if not rows:
        return None
    return TypicalFare(
        price=int(statistics.median(price for price, _ in rows)),
        duration_min=int(statistics.median(minutes for _, minutes in rows)),
        samples=len(rows),
    )
