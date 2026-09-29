"""Deterministic day-by-day itinerary builder.

Used directly in demo mode / when Claude isn't configured, and as the validator + cost
calculator for Claude's itinerary. Places are grouped by nearest-neighbour routing from
the hotel, so each day stays in one part of town.
"""

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from ..models.schemas import Day, Hotel, Place, Restaurant, Slot, TransportOption, TripRequest
from ..providers.geocode import haversine_km

DAY_START = time(9, 30)
DAYTIME_END = time(18, 30)
LUNCH_AFTER = time(12, 45)
DINNER_AT = time(20, 0)
ROAD_FACTOR, CITY_SPEED_KMPH = 1.3, 30
# Local travel by style: (₹ per km per vehicle, people per vehicle, minimum fare per leg).
# Budget ≈ scooter / shared transport, balanced ≈ app cab, comfort ≈ private car.
LOCAL_RATE = {"budget": (5, 2, 30), "balanced": (16, 4, 80), "comfort": (24, 4, 120)}
BREAKFAST_PP = 150
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

INTEREST_BOOST = 1.5
# Nearest-neighbour: how many km of detour one rating point is worth.
KM_PER_RATING_POINT = 2.5
REUSED_RESTAURANT_PENALTY = 400  # ₹ per previous visit, so meals vary even when few places are close
MEAL_RADIUS_KM = 6
# Restaurant choice by style: (weight on price, ₹ value of one rating point)
MEAL_WEIGHTS = {"budget": (1.0, 40), "balanced": (0.6, 200), "comfort": (0.2, 500)}
TREAT_MEAL_WEIGHTS = (0.0, 1500)  # "treat yourself" dinners: rating is all that matters
PLACE_OVERHEAD_MIN = 35  # travel + slack per stop when sizing a day
CLUSTER_KM = 15  # a day's places stay within this road distance of its anchor
FULL_DAY_MIN_CAPACITY = 480  # 09:30–18:30 minus an hour for lunch


@dataclass
class ScheduleInput:
    req: TripRequest
    arrival: datetime
    departure: datetime
    departure_mode: str
    hotel: Hotel
    places: list[Place]
    restaurants: list[Restaurant]
    place_tags: dict[str, list[str]]
    activity_budget: int
    food_budget: int
    city_lat: float
    city_lng: float
    # From Claude: day number → place ids, and day titles. None = choose places ourselves.
    assignment: dict[int, list[str]] | None = None
    titles: dict[int, str] | None = None
    exclude: set[str] | None = None  # place ids dropped to fit the budget
    city_name: str = ""  # places whose area is just the city name are left out of day titles


def _fmt(t: datetime) -> str:
    return t.strftime("%H:%M")


def _window(place: Place) -> tuple[time, time] | None:
    """Opening window from strings like '09:30–18:00' (close after midnight → 23:59)."""
    m = re.search(r"(\d{2}):(\d{2})\s*[–-]\s*(\d{2}):(\d{2})", place.hours)
    if not m:
        return None
    o, c = time(int(m.group(1)), int(m.group(2))), time(int(m.group(3)), int(m.group(4)))
    return o, (c if c > o else time(23, 59))


def _weekday_only(place: Place) -> int | None:
    m = re.match(r"(\w+?)s? ", place.hours.lower() + " ")
    if m and m.group(1) in WEEKDAYS:
        return WEEKDAYS.index(m.group(1))
    return None


def _opens_evening(place: Place) -> bool:
    m = re.search(r"(\d{2}):(\d{2})", place.hours)
    return bool(m) and int(m.group(1)) >= 17


def _km(a_lat, a_lng, b_lat, b_lng) -> float:
    return haversine_km(a_lat, a_lng, b_lat, b_lng) * ROAD_FACTOR


def _travel_min(km: float) -> int:
    if km < 0.6:  # next door: no travel leg (matches _Builder.travel)
        return 0
    return int(km / CITY_SPEED_KMPH * 60) + 10


def local_fare(style: str, pax: int, km: float) -> int:
    """Cost of one local leg for the whole group."""
    if km < 0.6:
        return 0
    rate, per_vehicle, min_fare = LOCAL_RATE[style]
    return max(min_fare, int(round(km * rate * math.ceil(pax / per_vehicle) / 10.0)) * 10)


class _Builder:
    def __init__(self, si: ScheduleInput):
        self.si = si
        pax = si.req.travellers
        days = si.req.nights + 1
        # Split the daily food budget between lunch and dinner caps (per person).
        self.breakfast_included = any("breakfast" in a.lower() for a in si.hotel.amenities)
        per_day_pp = si.food_budget / max(pax * days, 1)
        per_day_pp -= 0 if self.breakfast_included else BREAKFAST_PP
        self.lunch_cap = max(200, per_day_pp * 0.4)
        self.dinner_cap = max(250, per_day_pp * 0.6)

    def travel_cost(self, km: float) -> int:
        return local_fare(self.si.req.style, self.si.req.travellers, km)

    def travel(self, slots, t, lat, lng, to_lat, to_lng, label) -> datetime:
        km = _km(lat, lng, to_lat, to_lng)
        if km < 0.6:
            return t
        end = t + timedelta(minutes=_travel_min(km))
        slots.append(Slot(kind="travel", start=_fmt(t), end=_fmt(end), title=label,
                          cost=self.travel_cost(km), is_estimate=True, notes=f"~{km:.0f} km"))
        return end

    def meal(self, slots, t, lat, lng, cap, label, used: dict[str, int], near: tuple[float, float] | None = None):
        """Eat somewhere close to `near` (default: where we are now), travelling from (lat, lng)."""
        pax = self.si.req.travellers
        near_lat, near_lng = near or (lat, lng)

        price_w, rating_w = MEAL_WEIGHTS[self.si.req.style]
        if label == "Dinner" and self.si.req.treat_dinners:
            price_w, rating_w, cap = TREAT_MEAL_WEIGHTS[0], TREAT_MEAL_WEIGHTS[1], float("inf")

        def total_cost(r: Restaurant) -> float:
            # what this meal really costs: food + getting there, with a penalty above the cap
            over = max(0, r.cost_per_person - cap) * pax
            repeat = REUSED_RESTAURANT_PENALTY * used.get(r.id, 0)
            travel = self.travel_cost(_km(near_lat, near_lng, r.lat, r.lng))
            return price_w * r.cost_per_person * pax + over + travel + repeat - r.rating * rating_w

        # Only consider places nearby: the 3 closest, plus anything within MEAL_RADIUS_KM.
        dist = lambda r: _km(near_lat, near_lng, r.lat, r.lng)
        by_dist = sorted(self.si.restaurants, key=dist)
        radius = max(MEAL_RADIUS_KM, dist(by_dist[min(2, len(by_dist) - 1)]))
        nearby = [r for r in by_dist if dist(r) <= radius]
        r = min(nearby, key=total_cost)
        t = self.travel(slots, t, lat, lng, r.lat, r.lng, f"To {r.name}")
        end = t + timedelta(minutes=60 if label == "Lunch" else 75)
        slots.append(Slot(kind="meal", start=_fmt(t), end=_fmt(end), title=f"{label} at {r.name}",
                          ref_id=r.id, cost=r.cost_per_person * self.si.req.travellers,
                          is_estimate=True, lat=r.lat, lng=r.lng,
                          notes=f"{r.cuisine} · ~₹{r.cost_per_person}/person"))
        used[r.id] = used.get(r.id, 0) + 1
        return end, r.lat, r.lng


def _score(place: Place, interests: list[str], tags: list[str]) -> float:
    s = place.rating
    if interests and (place.category in interests or set(tags) & set(interests)):
        s += INTEREST_BOOST
    return s


def select_places(si: ScheduleInput) -> list[Place]:
    """Pick the best places that fit the activity budget, ordered by preference."""
    pax = si.req.travellers
    if si.assignment:
        by_id = {p.id: p for p in si.places}
        ranked = [by_id[i] for day in sorted(si.assignment) for i in si.assignment[day] if i in by_id]
    else:
        ranked = sorted(si.places, key=lambda p: -_score(p, si.req.interests, si.place_tags.get(p.id, [])))
    exclude = si.exclude or set()
    # Places the traveller added go first, even beyond the activity budget: they chose to spend on them.
    must = [p for p in si.places if p.id in si.req.must_include]
    picked, spend = list(must), sum(p.fee_per_person * pax for p in must)
    for p in ranked:
        if p.id in exclude or p in must:
            continue
        cost = p.fee_per_person * pax
        if spend + cost <= si.activity_budget:
            picked.append(p)
            spend += cost
    return picked


def _day_capacity(si: ScheduleInput, i: int, n_days: int, dep_buffer: int) -> int:
    """Minutes available for sightseeing on day i (0-based)."""
    d = si.req.start_date + timedelta(days=i)
    start = datetime.combine(d, DAY_START)
    end = datetime.combine(d, DAYTIME_END)
    if i == 0:
        start = max(start, si.arrival + timedelta(minutes=90))  # transfer + check-in
    if i == n_days - 1:
        start = max(start, datetime.combine(d, time(11, 0)))
        end = min(end, si.departure - timedelta(minutes=dep_buffer + 60))
    return max(0, int((end - start).total_seconds() // 60) - 60)  # minus lunch


def cluster_days(si: ScheduleInput, daytime: list[Place], evening: list[Place], dep_buffer: int) -> dict[int, list[str]]:
    """Split places into one geographic group per day, like a person planning
    'the North Goa day'. Full days are seeded by the best remaining place and filled with
    its nearest neighbours; arrival/departure days get what's closest to the hotel."""
    n_days = si.req.nights + 1
    hotel = si.hotel
    interests, tags = si.req.interests, si.place_tags
    cap = {i + 1: _day_capacity(si, i, n_days, dep_buffer) for i in range(n_days)}
    groups: dict[int, list[Place]] = {n: [] for n in cap}
    # traveller-added places anchor days first, then the best-scored ones
    left = sorted(daytime, key=lambda p: (p.id not in si.req.must_include, -_score(p, interests, tags.get(p.id, []))))
    cost = lambda p: p.duration_min + PLACE_OVERHEAD_MIN

    # weekday-only places must go on their weekday
    for p in list(left):
        wd = _weekday_only(p)
        if wd is None:
            continue
        match = [n for n in cap if (si.req.start_date + timedelta(days=n - 1)).weekday() == wd and cap[n] >= cost(p)]
        if match:
            groups[match[0]].append(p)
            cap[match[0]] -= cost(p)
        left.remove(p)

    def fill(n: int, lat: float, lng: float, radius: float):
        while True:
            fits = [p for p in left if cost(p) <= cap[n] and _km(lat, lng, p.lat, p.lng) <= radius]
            if not fits:
                return
            p = min(fits, key=lambda p: _km(lat, lng, p.lat, p.lng) - KM_PER_RATING_POINT * (p.rating - 4))
            groups[n].append(p)
            cap[n] -= cost(p)
            left.remove(p)

    # arrival/departure days first: short windows, so only what's close to the hotel
    for n in dict.fromkeys((1, n_days)):
        fill(n, hotel.lat, hotel.lng, CLUSTER_KM)
    # full days: anchor on the best remaining place and add its neighbours
    for n in range(2, n_days):
        if groups[n]:  # already anchored by a weekday-only place
            anchor = groups[n][0]
        else:
            # the anchor must be reachable, visitable and left again within the day
            round_trip = lambda p: 2 * _travel_min(_km(hotel.lat, hotel.lng, p.lat, p.lng))
            seeds = [p for p in left if cost(p) + round_trip(p) <= cap[n] + 60]
            if not seeds:
                continue
            anchor = seeds[0]  # best remaining
            groups[n].append(anchor)
            cap[n] -= cost(anchor)
            left.remove(anchor)
        fill(n, anchor.lat, anchor.lng, CLUSTER_KM)
    # leftover time anywhere: top up with places near each day's group
    for n in cap:
        pts = groups[n] or [hotel]
        fill(n, sum(p.lat for p in pts) / len(pts), sum(p.lng for p in pts) / len(pts), CLUSTER_KM * 1.5)

    # one evening place per day (not the departure day), near that day's group
    ev_left = sorted(evening, key=lambda p: (p.id not in si.req.must_include, -_score(p, interests, tags.get(p.id, []))))
    for n in range(1, n_days):
        d = si.req.start_date + timedelta(days=n - 1)
        options = [p for p in ev_left if _weekday_only(p) in (None, d.weekday())]
        if not options:
            continue
        pts = groups[n] or [hotel]
        clat = sum(p.lat for p in pts) / len(pts)
        clng = sum(p.lng for p in pts) / len(pts)
        # weekday-only evenings first (they have no other chance), then nearest
        p = min(options, key=lambda p: (_weekday_only(p) is None, _km(clat, clng, p.lat, p.lng)))
        groups[n].append(p)
        ev_left.remove(p)

    return {n: [p.id for p in ps] for n, ps in groups.items()}


def build_days(si: ScheduleInput) -> tuple[list[Day], list[Place]]:
    """Returns (days, places not scheduled)."""
    b = _Builder(si)
    req, hotel = si.req, si.hotel
    pool = select_places(si)
    daytime = [p for p in pool if not _opens_evening(p)]
    evening = [p for p in pool if _opens_evening(p)]
    used_rest: dict[str, int] = {}  # restaurant id → meals eaten there
    days: list[Day] = []
    n_days = req.nights + 1
    dep_buffer = 150 if si.departure_mode == "flight" else 90
    assignment = si.assignment or cluster_days(si, daytime, evening, dep_buffer)

    for i in range(n_days):
        d: date = req.start_date + timedelta(days=i)
        slots: list[Slot] = []
        lat, lng = hotel.lat, hotel.lng
        first, last = i == 0, i == n_days - 1
        t = datetime.combine(d, DAY_START)
        day_end = datetime.combine(d, DAYTIME_END)
        # Only that day's group (from Claude or cluster_days) is considered.
        allowed = set(assignment.get(i + 1, []))
        today = lambda pool: [p for p in pool if p.id in allowed]

        if first:
            arr = max(si.arrival, datetime.combine(d, time(0, 0)))
            slots.append(Slot(kind="arrival", start=_fmt(arr), end=_fmt(arr), title=f"Arrive in {req.destination}"))
            t = b.travel(slots, arr, si.city_lat, si.city_lng, hotel.lat, hotel.lng, f"Transfer to {hotel.name}")
            slots.append(Slot(kind="checkin", start=_fmt(t), end=_fmt(t + timedelta(minutes=30)),
                              title=f"Check in / drop bags at {hotel.name}", lat=hotel.lat, lng=hotel.lng))
            t = max(t + timedelta(minutes=30), datetime.combine(d, DAY_START))
        elif not b.breakfast_included:
            slots.append(Slot(kind="meal", start="08:30", end="09:15", title="Breakfast near the hotel",
                              cost=BREAKFAST_PP * req.travellers, is_estimate=True))
        leave = si.departure - timedelta(minutes=dep_buffer)
        if last:
            co = min(datetime.combine(d, time(10, 30)), leave - timedelta(minutes=30))
            slots.append(Slot(kind="checkout", start=_fmt(co), end=_fmt(co + timedelta(minutes=30)),
                              title="Check out (leave luggage at reception)", lat=hotel.lat, lng=hotel.lng))
            t = max(t, co + timedelta(minutes=30))
            day_end = min(day_end, leave - timedelta(minutes=60))

        # --- daytime: nearest-neighbour over remaining places ---
        lunch_done = False
        while True:
            if not lunch_done and t.time() >= LUNCH_AFTER and t < day_end:
                t, lat, lng = b.meal(slots, t, lat, lng, b.lunch_cap, "Lunch", used_rest)
                lunch_done = True

            def start_at(p: Place) -> datetime | None:
                """When we could start visiting p, or None if it doesn't fit today."""
                wd = _weekday_only(p)
                if wd is not None and wd != d.weekday():
                    return None
                reached = t + timedelta(minutes=_travel_min(_km(lat, lng, p.lat, p.lng)))
                begin, close = reached, day_end
                win = _window(p)
                if win:
                    begin = max(reached, datetime.combine(d, win[0]))
                    close = min(close, datetime.combine(d, win[1]))
                if begin - reached > timedelta(hours=2):  # don't idle for hours waiting for it to open
                    return None
                return begin if begin + timedelta(minutes=p.duration_min) <= close else None

            options = [p for p in today(daytime) if start_at(p)]
            if not options:
                break
            # places the traveller added come first, so they're never squeezed out by the clock
            nxt = min(options, key=lambda p: (p.id not in req.must_include, _km(lat, lng, p.lat, p.lng) - KM_PER_RATING_POINT * (p.rating - 4)))
            begin = start_at(nxt)
            daytime.remove(nxt)
            t = b.travel(slots, t, lat, lng, nxt.lat, nxt.lng, f"To {nxt.name}")
            t = max(t, begin)
            end = t + timedelta(minutes=nxt.duration_min)
            slots.append(Slot(kind="place", start=_fmt(t), end=_fmt(end), title=nxt.name, ref_id=nxt.id,
                              cost=nxt.fee_per_person * req.travellers, is_estimate=nxt.fee_is_estimate,
                              lat=nxt.lat, lng=nxt.lng, notes=nxt.description))
            t, lat, lng = end, nxt.lat, nxt.lng

        lunch_at = max(t, datetime.combine(d, time(13, 0)))
        lunch_ok = lunch_at + timedelta(minutes=90) <= leave if last else t.time() < time(16, 0)
        if not lunch_done and lunch_ok:
            t, lat, lng = b.meal(slots, lunch_at, lat, lng, b.lunch_cap, "Lunch", used_rest)

        # --- evening ---
        if not last:
            t = max(t, datetime.combine(d, time(17, 30)))

            def still_open(p: Place) -> bool:
                win = _window(p)
                if _weekday_only(p) not in (None, d.weekday()) or not win:
                    return False
                start = max(t, datetime.combine(d, win[0]))
                return start <= datetime.combine(d, win[1]) - timedelta(minutes=30)

            ev = [p for p in today(evening) if still_open(p)]
            if ev:
                p = min(ev, key=lambda p: _km(lat, lng, p.lat, p.lng) - KM_PER_RATING_POINT * (p.rating - 4))
                opens = re.search(r"(\d{2}):(\d{2})", p.hours)
                open_at = datetime.combine(d, time(int(opens.group(1)), int(opens.group(2))))
                if open_at.hour >= 21:  # late-night spot: have dinner first
                    t, lat, lng = b.meal(slots, max(t, datetime.combine(d, time(19, 30))), lat, lng, b.dinner_cap, "Dinner", used_rest)
                    dinner_done = True
                else:
                    dinner_done = False
                t = b.travel(slots, max(t, open_at - timedelta(minutes=30)), lat, lng, p.lat, p.lng, f"To {p.name}")
                t = max(t, open_at)
                end = t + timedelta(minutes=p.duration_min)
                slots.append(Slot(kind="place", start=_fmt(t), end=_fmt(end), title=p.name, ref_id=p.id,
                                  cost=p.fee_per_person * req.travellers, is_estimate=p.fee_is_estimate,
                                  lat=p.lat, lng=p.lng, notes=p.description))
                evening.remove(p)
                t, lat, lng = end, p.lat, p.lng
                if not dinner_done:
                    t, lat, lng = b.meal(slots, max(t, datetime.combine(d, DINNER_AT)), lat, lng, b.dinner_cap, "Dinner", used_rest)
            else:  # no evening plans: head back and eat near the hotel
                t, lat, lng = b.meal(slots, max(t, datetime.combine(d, DINNER_AT)), lat, lng, b.dinner_cap, "Dinner",
                                     used_rest, near=(hotel.lat, hotel.lng))
            b.travel(slots, t, lat, lng, hotel.lat, hotel.lng, "Back to hotel")
        else:
            t = b.travel(slots, t, lat, lng, hotel.lat, hotel.lng, "Back to hotel for luggage")
            b.travel(slots, max(t, leave - timedelta(minutes=60)), hotel.lat, hotel.lng, si.city_lat, si.city_lng,
                     "Head to the " + ("airport" if si.departure_mode == "flight" else "station"))
            slots.append(Slot(kind="departure", start=_fmt(si.departure), end=_fmt(si.departure),
                              title=f"Depart {req.destination}"))

        places_today = [s for s in slots if s.kind == "place"]
        areas = []
        for s in places_today:
            area = next((p.area for p in si.places if p.id == s.ref_id), None)
            if area and area not in areas and area.lower() != si.city_name.lower():  # "Goa" alone says nothing
                areas.append(area)
        title = " & ".join(areas[:2]) or "Relax & explore"
        if si.titles and si.titles.get(i + 1):
            title = si.titles[i + 1]
        elif first:
            title = f"Arrival · {title}"
        elif last:
            title = f"{title} · Departure"
        days.append(Day(number=i + 1, date=d, title=title, slots=slots, cost=sum(s.cost for s in slots)))

    return days, daytime + evening
