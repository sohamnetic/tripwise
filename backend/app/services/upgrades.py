"""Ways to spend leftover budget: a better hotel, activities that didn't make the cut, and
faster or comfier transport.

`candidate_upgrades` proposes options with a rough cost so obviously unaffordable ones are
skipped; the planner then re-plans with each one applied to get the exact change in total
(see planner.price_upgrades), and `limit_per_kind` keeps the best few."""

from ..models.schemas import Day, Hotel, Place, Restaurant, TransportOption, TripOverrides, TripRequest, Upgrade
from ..providers.geocode import haversine_km
from .scheduler import FULL_DAY_MIN_CAPACITY, ROAD_FACTOR, _travel_min, local_fare

MAX_PER_KIND = {"activity": 3, "dining": 1, "hotel": 2, "transport": 2}
CANDIDATES_PER_KIND = {"hotel": 4, "activity": 6, "transport": 3}
MIN_HOURS_SAVED = 3  # only suggest faster transport if it saves real time


def _hotel_upgrades(req: TripRequest, current: Hotel, hotels: list[Hotel], budget_left: int) -> list[Upgrade]:
    better = [
        h for h in hotels
        if h.id != current.id
        and (h.stars > current.stars or h.rating >= current.rating + 0.2)
        and 0 < h.total_price - current.total_price <= budget_left
    ]
    better.sort(key=lambda h: (h.stars, h.rating), reverse=True)
    out = []
    for h in better[: CANDIDATES_PER_KIND["hotel"]]:
        perks = ", ".join(h.amenities[:3])
        if h.is_estimate:  # a kind of stay at a typical price, not a real listing
            kind = h.name[0].lower() + h.name[1:]
            title = f"Upgrade to {'an' if kind[0] in 'aeiou' else 'a'} {kind}"
            detail = f"{h.stars}★ · typical price. Choose the actual hotel on Booking.com."
        else:
            title = f"Stay at {h.name}"
            detail = f"{h.stars}★ · rated {h.rating} · {h.area}" + (f" · {perks}" if perks else "")
        out.append(Upgrade(
            id=f"hotel:{h.id}", kind="hotel", title=title, detail=detail,
            extra_cost=h.total_price - current.total_price,
            apply=TripOverrides(hotel_id=h.id),
        ))
    return out


def _activity_upgrades(req: TripRequest, hotel: Hotel, places: list[Place], days: list[Day], budget_left: int) -> list[Upgrade]:
    visited = {s.ref_id for d in days for s in d.slots if s.kind == "place"}
    candidates = []
    for p in places:
        if p.id in visited or p.id in req.must_include:
            continue
        km = haversine_km(hotel.lat, hotel.lng, p.lat, p.lng) * ROAD_FACTOR
        if 2 * _travel_min(km) + p.duration_min > FULL_DAY_MIN_CAPACITY:
            continue  # can't be done as a day trip from this hotel
        extra = p.fee_per_person * req.travellers + 2 * local_fare(req.style, req.travellers, km)
        if 0 < extra <= budget_left:
            interest = p.category in req.interests
            candidates.append((interest, p.fee_per_person > 0, p.rating, p, extra))
    candidates.sort(key=lambda c: (c[0], c[1], c[2]), reverse=True)
    out = []
    for _, _, _, p, extra in candidates[: CANDIDATES_PER_KIND["activity"]]:
        fee = f"₹{p.fee_per_person:,}/person" if p.fee_per_person else "free entry"
        out.append(Upgrade(
            id=f"place:{p.id}", kind="activity",
            title=f"Add {p.name}",
            detail=f"{p.description} ({fee}, plus getting there)",
            extra_cost=extra,
            apply=TripOverrides(must_include=[p.id]),
        ))
    return out


def _transport_upgrades(req: TripRequest, out: TransportOption, back: TransportOption,
                        outbound: list[TransportOption], inbound: list[TransportOption], budget_left: int) -> list[Upgrade]:
    current_cost = out.total_price + back.total_price
    current_min = out.duration_min + back.duration_min
    ups: list[Upgrade] = []

    # 1) a faster mode (e.g. fly instead of a 40-hour train)
    pairs = [(o, i) for o in outbound for i in inbound if o.mode == i.mode and o.mode != out.mode]
    faster = [p for p in pairs if current_min - (p[0].duration_min + p[1].duration_min) >= MIN_HOURS_SAVED * 60]
    # the cheapest faster pair, and the one that leaves the most time at the destination
    cheapest = min(faster, key=lambda p: p[0].total_price + p[1].total_price) if faster else None
    most_time = min(faster, key=lambda p: (p[0].arrive - p[1].depart).total_seconds()) if faster else None
    picks = {(p[0].id, p[1].id): p for p in (cheapest, most_time) if p}
    for o, i in picks.values():
        extra = o.total_price + i.total_price - current_cost
        if 0 < extra <= budget_left:
            hours = round((current_min - o.duration_min - i.duration_min) / 60)
            ups.append(Upgrade(
                id=f"transport:{o.id}:{i.id}", kind="transport",
                title=f"Take the {o.mode} instead ({o.carrier}, back at {i.depart:%H:%M})",
                detail=f"Saves about {hours} hours of travel there and back.",
                extra_cost=extra,
                apply=TripOverrides(transport_ids=[o.id, i.id]),
            ))

    # 2) a more comfortable class/option on the same mode (e.g. Sleeper → AC 3-tier)
    same = [(o, i) for o in outbound for i in inbound
            if o.mode == out.mode == i.mode and o.carrier == out.carrier and o.service == i.service
            and o.total_price + i.total_price > current_cost]
    if same:
        o, i = min(same, key=lambda p: p[0].total_price + p[1].total_price)
        extra = o.total_price + i.total_price - current_cost
        if extra <= budget_left and o.mode != "flight":
            ups.append(Upgrade(
                id=f"transport:{o.id}:{i.id}", kind="transport",
                title=f"Upgrade to {o.service}",
                detail="More comfortable berths, air-conditioned and less crowded.",
                extra_cost=extra,
                apply=TripOverrides(transport_ids=[o.id, i.id]),
            ))
    return ups[: CANDIDATES_PER_KIND["transport"]]


def _dining_upgrade(req: TripRequest, restaurants: list[Restaurant]) -> list[Upgrade]:
    if req.treat_dinners or not restaurants:
        return []
    best = sorted(restaurants, key=lambda r: -r.rating)[:2]
    return [Upgrade(
        id="dining:treat", kind="dining",
        title="Treat yourself to nicer dinners",
        detail=f"Every dinner at the best-rated restaurant near you, e.g. {' or '.join(r.name for r in best)}.",
        extra_cost=0,  # priced by the planner
        apply=TripOverrides(treat_dinners=True),
    )]


def candidate_upgrades(req: TripRequest, remaining: int, hotel: Hotel, hotels: list[Hotel], places: list[Place],
                       restaurants: list[Restaurant], days: list[Day], out: TransportOption, back: TransportOption,
                       outbound: list[TransportOption], inbound: list[TransportOption]) -> list[Upgrade]:
    if remaining <= 0:
        return []
    return (
        _activity_upgrades(req, hotel, places, days, remaining)
        + _dining_upgrade(req, restaurants)
        + _hotel_upgrades(req, hotel, hotels, remaining)
        + _transport_upgrades(req, out, back, outbound, inbound, remaining)
    )


def limit_per_kind(ups: list[Upgrade]) -> list[Upgrade]:
    """Keep the first few of each kind (candidates arrive best-first), cheapest first overall.
    Swaps that push out a planned place rank after clean additions of the same kind."""
    kept: list[Upgrade] = []
    for kind, n in MAX_PER_KIND.items():
        mine = [u for u in ups if u.kind == kind]
        mine.sort(key=lambda u: "You'd skip" in u.detail)  # stable: keeps best-first order otherwise
        kept += mine[:n]
    return sorted(kept, key=lambda u: u.extra_cost)
