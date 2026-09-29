"""Live flight prices from SerpApi Google Flights.

We search each direction as a one-way trip for ONE adult, so the price is unambiguously
per person, then multiply by the number of travellers.
"""

import asyncio
from datetime import date, datetime

from ..models.schemas import City, Link, TransportOption
from ..services import links
from . import fare_memory
from .base import serpapi

FLIGHTS_TTL_HOURS = 6
MAX_OPTIONS = 6


def parse_flights(raw: dict, o: City, d: City, pax: int, tag: str, extra_links: list[Link]) -> list[TransportOption]:
    items = (raw.get("best_flights") or []) + (raw.get("other_flights") or [])
    opts: list[TransportOption] = []
    for i, item in enumerate(items):
        segs = item.get("flights") or []
        price = item.get("price")
        if not segs or not isinstance(price, (int, float)):
            continue
        try:
            depart = datetime.strptime(segs[0]["departure_airport"]["time"], "%Y-%m-%d %H:%M")
            arrive = datetime.strptime(segs[-1]["arrival_airport"]["time"], "%Y-%m-%d %H:%M")
        except (KeyError, ValueError):
            continue
        airlines = list(dict.fromkeys(s.get("airline", "") for s in segs if s.get("airline")))
        stops = len(segs) - 1
        numbers = " / ".join(s.get("flight_number", "") for s in segs if s.get("flight_number"))
        service = f"{numbers} · {'non-stop' if stops == 0 else f'{stops} stop' + ('s' if stops > 1 else '')}"
        duration = item.get("total_duration") or int((arrive - depart).total_seconds() // 60)
        pp = int(price)
        opts.append(TransportOption(
            id=f"{tag}-flight-{i}", mode="flight", carrier=" + ".join(airlines) or "Airline",
            service=service, from_city=o.name, to_city=d.name, depart=depart, arrive=arrive,
            duration_min=int(duration), price_per_person=pp, total_price=pp * pax, is_estimate=False,
            links=extra_links,
        ))
        if len(opts) >= MAX_OPTIONS:
            break
    return opts


def _params(frm: City, to: City, day: date) -> dict:
    return {
        "engine": "google_flights",
        "departure_id": frm.iata,
        "arrival_id": to.iata,
        "outbound_date": day.isoformat(),
        "type": 2,  # one-way
        "adults": 1,
        "currency": "INR",
        "gl": "in",
        "hl": "en",
    }


async def search_flights(o: City, d: City, start: date, end: date, pax: int):
    if o.iata == d.iata:
        return [], []
    out_raw, in_raw = await asyncio.gather(
        serpapi(_params(o, d, start), FLIGHTS_TTL_HOURS),
        serpapi(_params(d, o, end), FLIGHTS_TTL_HOURS),
    )
    # Our own links, not SerpApi's google_flights_url: that one repeats our search (one-way, one
    # adult), whereas the traveller needs a return search for the whole group.
    booking = links.flight_links(o, d, start, end, pax)
    out_opts = parse_flights(out_raw, o, d, pax, "out", booking)
    in_opts = parse_flights(in_raw, d, o, pax, "in", booking)
    # so later estimates for these routes can use real prices
    fare_memory.remember(o.iata, d.iata, start, out_opts)
    fare_memory.remember(d.iata, o.iata, end, in_opts)
    return out_opts, in_opts
