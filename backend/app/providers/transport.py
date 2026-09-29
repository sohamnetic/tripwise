"""Transport options between two cities.

Trains and buses have no public fare API in India, so they are always distance-based
estimates (clearly flagged). Flights come from SerpApi Google Flights in live mode and
from a deterministic simulation in demo mode.
"""

from datetime import date, datetime, time, timedelta

from ..config import get_settings
from ..models.schemas import City, TransportOption
from ..services import links
from .geocode import city_distance_km

# Rough Indian Railways fare per km (per person) by class, plus a floor.
TRAIN_CLASSES = [
    ("Sleeper (SL)", 0.55, 200),
    ("AC 3-tier (3A)", 1.25, 500),
    ("AC 2-tier (2A)", 1.85, 800),
]
BUS_RATE_PER_KM, BUS_FLOOR, BUS_MAX_KM = 1.9, 400, 1400
RAIL_SPEED_KMPH, BUS_SPEED_KMPH = 52, 45
DETOUR = 1.3  # rail/road distance vs straight line

DEMO_AIRLINES = [
    ("IndiGo", "6E", time(6, 10), 1.00),
    ("Akasa Air", "QP", time(9, 45), 1.06),
    ("Air India", "AI", time(14, 30), 1.18),
    ("Air India Express", "IX", time(19, 5), 1.09),
]


def _round50(x: float) -> int:
    return int(round(x / 50.0)) * 50


def _flight_fare(km: float, international: bool) -> float:
    return 6000 + 3.2 * km if international else 1800 + 2.9 * km


def _demo_flights(o: City, d: City, day: date, pax: int, back: bool, back_date: date, out_date: date) -> list[TransportOption]:
    km = city_distance_km(o, d)
    base = _flight_fare(km, o.international or d.international)
    minutes = int(45 + km / 7.5)
    flink = links.flight_links(d if back else o, o if back else d, out_date, back_date, pax)
    opts = []
    for i, (name, code, dep, mult) in enumerate(DEMO_AIRLINES):
        depart = datetime.combine(day, dep)
        if back:  # return flights leave in the afternoon/evening
            depart = datetime.combine(day, time(12 + i * 2, 20))
        pp = _round50(base * mult)
        opts.append(TransportOption(
            id=f"{'in' if back else 'out'}-flight-{i}",
            mode="flight", carrier=name, service=f"{code} {400 + i * 137 + int(km) % 97}",
            from_city=o.name, to_city=d.name,
            depart=depart, arrive=depart + timedelta(minutes=minutes), duration_min=minutes,
            price_per_person=pp, total_price=pp * pax, is_estimate=True, links=flink,
        ))
    return opts


def _ground_depart(day: date, minutes: int, outbound: bool) -> datetime:
    """Outbound overnight journeys arrive at 08:00 on the trip start; short ones leave at 06:00.
    Return journeys leave at 17:30 on the last day."""
    if not outbound:
        return datetime.combine(day, time(17, 30))
    if minutes > 10 * 60:
        return datetime.combine(day, time(8, 0)) - timedelta(minutes=minutes)
    return datetime.combine(day, time(6, 0))


def estimate_trains(o: City, d: City, day: date, pax: int, outbound: bool) -> list[TransportOption]:
    if not (o.has_rail and d.has_rail) or o.international or d.international:
        return []
    km = city_distance_km(o, d) * DETOUR
    minutes = int(km / RAIL_SPEED_KMPH * 60) + 30
    depart = _ground_depart(day, minutes, outbound)
    tag = "out" if outbound else "in"
    opts = []
    for i, (cls, rate, floor) in enumerate(TRAIN_CLASSES):
        pp = _round50(max(floor, rate * km))
        opts.append(TransportOption(
            id=f"{tag}-train-{i}", mode="train", carrier="Indian Railways", service=cls,
            from_city=o.name, to_city=d.name, depart=depart,
            arrive=depart + timedelta(minutes=minutes), duration_min=minutes,
            price_per_person=pp, total_price=pp * pax, is_estimate=True,
            links=links.train_links(o, d),
        ))
    return opts


def estimate_buses(o: City, d: City, day: date, pax: int, outbound: bool) -> list[TransportOption]:
    if not (o.has_road and d.has_road) or o.country != d.country:
        return []
    km = city_distance_km(o, d) * DETOUR
    if km > BUS_MAX_KM:
        return []
    minutes = int(km / BUS_SPEED_KMPH * 60) + 30
    depart = _ground_depart(day, minutes, outbound)
    pp = _round50(max(BUS_FLOOR, BUS_RATE_PER_KM * km))
    return [TransportOption(
        id=f"{'out' if outbound else 'in'}-bus-0", mode="bus", carrier="Private operators",
        service="AC sleeper", from_city=o.name, to_city=d.name, depart=depart,
        arrive=depart + timedelta(minutes=minutes), duration_min=minutes,
        price_per_person=pp, total_price=pp * pax, is_estimate=True, links=links.bus_links(o, d, depart.date()),
    )]


async def search_transport(o: City, d: City, start: date, end: date, pax: int) -> tuple[list[TransportOption], list[TransportOption]]:
    """Returns (outbound options, return options) across all modes."""
    settings = get_settings()
    if settings.demo_mode:
        out_f = _demo_flights(o, d, start, pax, False, end, start)
        in_f = _demo_flights(d, o, end, pax, True, end, start)
    else:
        from .flights import search_flights  # live SerpApi flights (step 2)
        out_f, in_f = await search_flights(o, d, start, end, pax)

    outbound = out_f + estimate_trains(o, d, start, pax, True) + estimate_buses(o, d, start, pax, True)
    inbound = in_f + estimate_trains(d, o, end, pax, False) + estimate_buses(d, o, end, pax, False)
    return outbound, inbound
