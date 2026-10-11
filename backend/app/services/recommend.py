"""Where to go, and roughly what it costs: the data behind "Ask Tripwise".

Plain Python, no network:
- seasons come from data/climate.json (six years of real daily weather per destination) plus a
  short list of known closures in data/destinations.json
- costs come from the same estimators the planner falls back to when live prices aren't
  available (distance-based fares, fares remembered from live searches, hotel price tiers)
"""

import json
import math
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from ..models.schemas import City, CostEstimate, PlanPrefill, SeasonInfo, Suggestion, TransportOption
from ..providers.geocode import city_distance_km, resolve_city
from ..providers.live_destination import HOTEL_TIERS
from ..providers.transport import estimate_buses, estimate_flights, estimate_trains
from .budget import _score
from .links import rooms_for

DATA = Path(__file__).resolve().parents[1] / "data"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]

# Food, local travel and activities per person per day, by style (in line with budget.SPLITS);
# about twice as much abroad.
DAILY_PER_PERSON = {"budget": 900, "balanced": 1500, "comfort": 2500, "luxury": 4500}
ABROAD_DAILY_FACTOR = 2.0
HOTEL_TIER_BY_STYLE = {"budget": 0, "balanced": 1, "comfort": 2, "luxury": 3}
ESTIMATE_SPREAD = 0.12
HIGH_ALTITUDE_M = 3000  # shown as a range: these are estimates, not quotes

# Chat interests (destination tags) and the planner's interests that go with them.
TAG_TO_PLANNER = {"beaches": ["beaches"], "mountains": ["nature", "adventure"], "heritage": ["history"],
                  "spiritual": ["history"], "wildlife": ["nature"], "backwaters": ["nature"],
                  "cities": ["food", "shopping"], "abroad": []}
INTEREST_TAGS = {
    "cool": set(),  # "somewhere cool": judged by the actual temperature, any kind of place
    "beaches": {"beaches"}, "mountains": {"mountains"}, "snow": {"mountains"}, "heritage": {"heritage"},
    "history": {"heritage"}, "spiritual": {"spiritual"}, "wildlife": {"wildlife"}, "backwaters": {"backwaters"},
    "cities": {"cities"}, "abroad": {"abroad"}, "nature": {"mountains", "wildlife", "backwaters"},
    "adventure": {"mountains"}, "food": {"cities"}, "nightlife": {"cities", "beaches"}, "shopping": {"cities"},
}


@lru_cache
def _climate() -> dict[str, list[dict]]:
    return json.loads((DATA / "climate.json").read_text(encoding="utf-8"))


@lru_cache
def destinations() -> dict[str, dict]:
    return {d["name"]: d for d in json.loads((DATA / "destinations.json").read_text(encoding="utf-8"))}


# ---- seasons -------------------------------------------------------------------------------------

def _temps(lo: float, hi: float) -> str:
    """'14–25°C', or '−8 to −2°C' when below zero (a dash between minus signs is hard to read)."""
    fmt = lambda t: f"{t:.0f}".replace("-", "−")
    return f"{fmt(lo)} to {fmt(hi)}°C" if lo < 0 else f"{fmt(lo)}–{fmt(hi)}°C"


def _rain_words(rainy_days: float, hi: float, monsoon: bool) -> str:
    if rainy_days < 2:
        return "dry"
    if rainy_days < 6:
        return "a few showers" if hi >= 4 else "a few snowy days"
    what = "snow or rain" if hi < 10 else "monsoon rain" if monsoon and rainy_days >= 12 else "rain"
    return f"{what} on ~{rainy_days:.0f} days"


def season(name: str, month: int) -> SeasonInfo:
    """How good `month` is for a destination: weather first, known closures override it."""
    dest = destinations()[name]
    m = _climate()[name][month - 1]
    hi, lo, wet, mm = m["tmax"], m["tmin"], m["rainy_days"], m["rain_mm"]
    mountains = "mountains" in dest["tags"]
    # The weather data reads very high places too cold (Leh: up to ~6°C low in spring), so say so.
    approx = dest.get("elevation_m", 0) >= HIGH_ALTITUDE_M
    temps = ("≈" if approx else "") + _temps(lo, hi)

    # (penalty, reason) for each problem; the biggest one explains the rating
    problems: list[tuple[int, str]] = []
    monsoon = 6 <= month <= 9 and "abroad" not in dest["tags"]
    kind = "Snow and rain" if hi < 10 else "Monsoon" if monsoon else "Wet"
    # In the snow season of a mountain place, snowfall is the attraction, so count it lightly.
    # Scored by how much falls: a hill station's short afternoon showers or Bali's tropical downpours
    # aren't a Goa monsoon (700+ mm). In a mountain place's cold months, it's mostly snow, the draw.
    snow_season = mountains and hi < 10
    wet_weight = 0.4 if snow_season else 1.0
    if mm > 350:
        problems.append((60, f"{kind}: very heavy rain (~{wet:.0f} wet days)"))
    elif mm > 220:
        problems.append((40, f"{kind}: heavy rain (~{wet:.0f} wet days)"))
    elif mm > 120:
        problems.append((22, f"Quite wet: ~{wet:.0f} rainy days"))
    elif mm > 50:
        problems.append((10, f"Some showers (~{wet:.0f} days)"))
    if hi >= 37.5:
        problems.append((45, f"Very hot: ~{hi:.0f}°C"))
    elif hi >= 35:
        problems.append((28, f"Hot: ~{hi:.0f}°C"))
    elif hi >= 33.5:
        problems.append((15, f"Warm: ~{hi:.0f}°C"))
    if lo >= 25.5 and hi >= 31:  # nights that never cool down: sticky by the sea, punishing inland
        problems.append((22, f"Hot days and warm nights: {_temps(lo, hi)}"))
    if mountains:  # snow is part of the draw, so cold days cost less here
        if hi < -2:
            problems.append((35, f"Freezing: highs of {hi:.0f}°C"))
        elif hi < 4:
            problems.append((15, f"Snowy and cold: highs of {hi:.0f}°C"))
    elif hi < 5:
        problems.append((40, f"Very cold: highs of {hi:.0f}°C"))
    elif hi < 12:
        problems.append((20, f"Chilly: highs of {hi:.0f}°C"))
    if lo < -8:
        problems.append((25, f"Bitterly cold nights: ~{lo:.0f}°C"))
    elif lo < -3:
        problems.append((10, f"Freezing nights: ~{lo:.0f}°C"))

    problems = [(int(p * wet_weight) if r.startswith((kind, "Quite wet", "Some showers")) else p, r) for p, r in problems]
    score = max(0, 100 - sum(p for p, _ in problems))
    rain = _rain_words(wet, hi, monsoon)
    weather = f"{temps} · {rain}"
    big = sorted((p for p in problems if p[0] >= 12), reverse=True)[:2]  # the one or two that matter
    if big:
        reason = big[0][1] + (f"; {big[1][1][0].lower()}{big[1][1][1:]}" if len(big) > 1 else "")
    else:
        reason = f"{'Snowy' if snow_season else 'Pleasant'}: {temps}, {rain}"
    rating = "Great" if score >= 80 else "Good" if score >= 62 else "Okay" if score >= 42 else "Avoid"

    note = "Temperatures are approximate this high up; sunny days often feel warmer." if approx else ""
    for c in dest["closures"]:
        if month not in c["months"]:
            continue
        if c["level"] == "closed":
            rating, score, reason = "Closed", 0, c["reason"]
        elif c["level"] == "avoid":
            rating, score, reason = "Avoid", min(score, 35), c["reason"]
        else:
            note = c["reason"]
    return SeasonInfo(month=month, rating=rating, score=score, reason=reason, weather=weather,
                      tmax=hi, tmin=lo, rainy_days=wet, note=note)


def best_months(name: str) -> list[str]:
    return [MONTHS[m - 1] for m in range(1, 13) if season(name, m).rating in ("Great", "Good")]


# ---- costs ------------------------------------------------------------------------------------------

def _best_transport(o: City, d: City, start: date, end: date, pax: int, style: str) -> tuple[TransportOption, TransportOption] | None:
    """The best return journey for the style, among modes that go both ways."""
    out = estimate_flights(o, d, start, pax, False, start, end) + estimate_trains(o, d, start, pax, True) + estimate_buses(o, d, start, pax, True)
    back = estimate_flights(d, o, end, pax, True, start, end) + estimate_trains(d, o, end, pax, False) + estimate_buses(d, o, end, pax, False)
    pairs = []
    for mode in ("flight", "train", "bus"):
        outs = [x for x in out if x.mode == mode]
        backs = [x for x in back if x.mode == mode]
        if outs and backs:
            pairs.append((min(outs, key=lambda x: _score(x, style, pax)), min(backs, key=lambda x: _score(x, style, pax))))
    if not pairs:
        return None
    return min(pairs, key=lambda p: _score(p[0], style, pax) + _score(p[1], style, pax))


def _hours_label(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def rough_cost(dest: City, origin: City | None, start: date, nights: int, travellers: int, style: str,
               budget: int | None = None) -> CostEstimate:
    end = start + timedelta(days=nights)
    abroad = dest.international
    transport, mode, label, hours = 0, None, "", None
    if origin and origin.name != dest.name:
        best = _best_transport(origin, dest, start, end, travellers, style)
        if best:
            out, back = best
            transport = out.total_price + back.total_price
            mode = out.mode
            label = f"{out.mode.capitalize()} · ~{_hours_label(out.duration_min)} each way"
            hours = round(out.duration_min / 60, 1)
    _, _, india, overseas = HOTEL_TIERS[HOTEL_TIER_BY_STYLE[style]]
    stay = (overseas if abroad else india) * rooms_for(travellers) * nights
    daily = int(DAILY_PER_PERSON[style] * (ABROAD_DAILY_FACTOR if abroad else 1) * travellers * (nights + 1))
    mid = transport + stay + daily
    low = int(math.floor(mid * (1 - ESTIMATE_SPREAD) / 500) * 500)
    high = int(math.ceil(mid * (1 + ESTIMATE_SPREAD) / 500) * 500)
    fits = None if budget is None else mid <= budget
    return CostEstimate(
        low=low, high=high, mid=mid, transport=transport, stay=stay, daily=daily, transport_mode=mode,
        transport_label=label, travel_hours=hours, includes_travel=bool(origin and transport), nights=nights,
        travellers=travellers, style=style, fits_budget=fits, over_by=max(0, mid - budget) if budget else 0,
    )


# ---- recommending ---------------------------------------------------------------------------------

def trip_start(month: int | None, start: date | None, today: date) -> date:
    """The start date to price: the one given, else the 10th of the next such month."""
    if start:
        return start
    month = month or (today.month % 12) + 1
    year = today.year if (month, 10) > (today.month, today.day) else today.year + 1
    return date(year, month, 10)


def _suggestion(name: str, origin: City | None, start: date, nights: int, travellers: int, style: str,
                budget: int | None, interests: list[str]) -> Suggestion:
    dest_city = resolve_city(name)
    d = destinations()[name]
    cost = rough_cost(dest_city, origin, start, nights, travellers, style, budget)
    planner_interests = sorted({i for t in d["tags"] for i in TAG_TO_PLANNER.get(t, [])}
                               | {i for i in interests if i in ("beaches", "food", "history", "nightlife", "nature", "shopping", "adventure")})
    prefill = PlanPrefill(
        origin=origin.name if origin else None, destination=name, start_date=start,
        end_date=start + timedelta(days=nights), travellers=travellers,
        budget=budget or int(math.ceil(cost.high / 1000) * 1000), style=style, interests=planner_interests[:4],
    )
    return Suggestion(name=name, tagline=d["tagline"], tags=d["tags"], season=season(name, start.month), cost=cost, prefill=prefill)


def find_destinations(*, month: int | None = None, start: date | None = None, nights: int = 4,
                      budget: int | None = None, travellers: int = 2, origin: str | None = None,
                      style: str = "balanced", interests: list[str] | None = None, limit: int = 4,
                      today: date | None = None) -> list[Suggestion]:
    """The best places for a time, budget, origin and interests (whichever are known), best first.
    If nothing fits a tight budget, it prices a budget-style trip and then a shorter one, the way a
    travel agent would; the cards show the style and nights actually priced. A traveller who asked
    for comfort or luxury keeps it."""
    args = dict(month=month, start=start, budget=budget, travellers=travellers, origin=origin,
                interests=interests, limit=limit, today=today)
    found = _rank(nights=nights, style=style, **args)
    if not budget or any(s.cost.fits_budget for s in found) or style not in ("balanced", "budget"):
        return found
    for n, st in ((nights, "budget"), (min(nights, 2), "budget")):
        retry = _rank(nights=n, style=st, **args)
        if any(s.cost.fits_budget for s in retry):
            return retry
    return found


def _rank(*, month: int | None, start: date | None, nights: int, budget: int | None, travellers: int,
          origin: str | None, style: str, interests: list[str] | None, limit: int,
          today: date | None) -> list[Suggestion]:
    """The best places for a time (and budget, origin and interests, when known), best first.
    Closed places are left out; places far over budget only fill in if there's nothing else."""
    today = today or date.today()
    start = trip_start(month, start, today)
    nights = max(1, min(14, nights))
    travellers = max(1, min(10, travellers))
    interests = [i.lower() for i in (interests or [])]
    wanted = set().union(*(INTEREST_TAGS.get(i, set()) for i in interests)) if interests else set()
    origin_city = resolve_city(origin) if origin else None

    scored = []
    for name, d in destinations().items():
        if origin_city and name == origin_city.name:
            continue
        tags = set(d["tags"])
        if "abroad" in tags and "abroad" not in wanted:
            continue  # only suggest going abroad when asked
        s = season(name, start.month)
        if s.rating == "Closed":
            continue
        fit = 0.0
        if wanted:
            fit = 25 if tags & wanted else -30
        if "cities" in tags and "cities" not in wanted:
            fit -= 15  # big cities are mostly where people travel from: Mumbai isn't a beach holiday
        if "cool" in interests:  # escaping the heat: what counts is how warm the days get
            fit += 25 if s.tmax <= 24 else 12 if s.tmax <= 27 else -5 if s.tmax <= 30 else -35
        scored.append((s.score * 0.6 + fit, name))
    # Price every candidate that suits the interests (cheap: no network), so ties on season don't
    # drop good options before their cost and distance are known.
    scored.sort(key=lambda x: -x[0])
    if wanted:
        scored = [x for x in scored if x[0] > 0] or scored
    picks = []
    for base, name in scored:
        sug = _suggestion(name, origin_city, start, nights, travellers, style, budget, interests)
        score = base
        if budget:
            over = sug.cost.mid - budget
            score -= max(0, over) / budget * 120  # over budget sinks fast
            score += 6 if over <= 0 else 0
            score -= 6 * min(1.0, sug.cost.mid / budget)  # between two that fit, the cheaper one is better value
        if sug.cost.travel_hours:
            score -= min(20, sug.cost.travel_hours * (3 if nights <= 3 else 1.5))  # long journeys eat short trips
        picks.append((score, sug))
    picks.sort(key=lambda p: -p[0])
    fitting = [s for _, s in picks if not budget or s.cost.low <= budget * 1.1]
    rest = [s for _, s in picks if s not in fitting]
    return (fitting + rest)[:max(1, min(limit, 8))]


def estimate_trip(destination: str, *, origin: str | None = None, month: int | None = None, start: date | None = None,
                  nights: int = 4, travellers: int = 2, style: str = "balanced", budget: int | None = None,
                  today: date | None = None) -> Suggestion:
    name = resolve_city(destination).name
    start = trip_start(month, start, today or date.today())
    return _suggestion(name, resolve_city(origin) if origin else None, start, max(1, min(14, nights)),
                       max(1, min(10, travellers)), style, budget, [])


def destination_info(destination: str, month: int | None = None) -> dict:
    name = resolve_city(destination).name
    d = destinations()[name]
    info = {"name": name, "tagline": d["tagline"], "tags": d["tags"], "best_months": best_months(name),
            "closures": [{"months": [MONTHS[m - 1] for m in c["months"]], "level": c["level"], "reason": c["reason"]}
                         for c in d["closures"]]}
    if month:
        info["month"] = season(name, month).model_dump()
    return info
