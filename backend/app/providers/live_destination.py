"""Live hotels (SerpApi Google Hotels) and places/restaurants (SerpApi Google Maps).

Google doesn't publish entry fees, so place fees and visit durations are estimated from the
place type and flagged `fee_is_estimate`.
"""

import asyncio
import re
import unicodedata
from datetime import date

from ..models.schemas import City, Hotel, Link, Place, Restaurant
from ..services import links
from .base import ProviderError, serpapi
from .destination import DestinationData
from .geocode import haversine_km

HOTELS_TTL_HOURS = 12
PLACES_TTL_HOURS = 24 * 30  # sights and restaurants barely change, so one search lasts a month
PLACES_STALE_DAYS = 60  # if a live search isn't possible, an older Google list is still good

# (keywords in the place's Google types or its name, our interest category, fee per person, minutes).
# Matched as whole words, first rule wins. Google often types beaches etc. only as
# "Tourist attraction", so the name matters as much as the type.
PLACE_RULES: list[tuple[tuple[str, ...], str, int, int]] = [
    (("beach", "beaches"), "beaches", 0, 120),
    (("water park", "amusement park", "theme park"), "adventure", 1200, 240),
    (("adventure", "water sports", "paragliding", "rafting", "scuba", "trek", "trekking"), "adventure", 1500, 180),
    (("museum", "gallery"), "history", 100, 90),
    (("fort", "fortress", "palace", "castle", "monument", "historical", "heritage", "archaeological", "tomb", "jail", "memorial", "ruins", "caves"), "history", 50, 75),
    (("temple", "church", "mosque", "gurudwara", "cathedral", "basilica", "monastery", "shrine", "mandir", "dargah"), "history", 0, 45),
    (("waterfall", "waterfalls", "falls", "national park", "wildlife", "sanctuary", "lake", "garden", "park", "viewpoint",
      "view point", "view", "point", "hill", "peak", "valley", "ghat", "dam", "nature", "lighthouse"), "nature", 0, 75),
    (("market", "bazaar", "mall", "shopping"), "shopping", 0, 90),
    (("night club", "nightclub", "pub", "lounge"), "nightlife", 800, 150),
    (("zoo", "aquarium"), "nature", 150, 120),
]
DEFAULT_RULE = ("", "sightseeing", 0, 60)
INTERNATIONAL_FEE_MULTIPLIER = 4  # entry fees abroad are typically much higher in INR terms
PLUS_CODE = re.compile(r"^[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}\b", re.I)


def _classify(types: list[str], name: str = "") -> tuple[str, int, int]:
    for text in (" ".join(types).lower(), name.lower()):
        for keys, cat, fee, mins in PLACE_RULES:
            if any(re.search(rf"\b{re.escape(k)}\b", text) for k in keys):
                return cat, fee, mins
    return DEFAULT_RULE[1], DEFAULT_RULE[2], DEFAULT_RULE[3]


MAX_NAME = 42
# Google Maps "attractions" sometimes include hotels, taxis and shops; skip those.
NOT_ATTRACTIONS = re.compile(
    r"\b(hotel|resort|lodging|homestay|guest ?house|hostel|villa|cottage|camp(ing|site)?|igloo stay|taxi|cab|car rental|"
    r"travel agency|tour operator|tour agency|restaurant|cafe|bar|store|shop|real estate|parking)\b", re.I)
STRONG_NOT_ATTRACTION = re.compile(r"\b(taxi|cabs?|rentals?|hotel|resorts?|homestay|igloo stay|tours? (and|&) travels?)\b", re.I)
# Administrative bits of Indian addresses that aren't neighbourhood names.
ADMIN_AREA = re.compile(r"nagar nigam|municipal|corp\.|\(part\)|\bward\b|district|tehsil|taluk|division|\bzone\b", re.I)


def clean_name(name: str, city: City) -> str:
    """Tidy business names from Google:
    'Bogmallo Beach Resort - 5 Star Hotel in Goa' → 'Bogmallo Beach Resort'
    'Calangute Beach, Goa' → 'Calangute Beach'
    '𝗧𝗵𝗲 𝗵𝗲𝗮𝗹𝘁𝗵𝘆 𝗸𝗶𝘁𝗰𝗵𝗲𝗻 pure veg…' → 'The healthy kitchen pure veg…'
    'BABUMOSHAI MULTI CUISINE FOOD JOINT' → 'Babumoshai Multi Cuisine Food Joint'"""
    name = unicodedata.normalize("NFKC", name).strip()
    # keep Latin letters (incl. accents), digits and common punctuation; drop other scripts and emoji
    name = "".join(c for c in name if c.isascii() or unicodedata.category(c).startswith("L") and ord(c) < 0x250)
    name = re.split(r"\s+[-–|:]\s+|\s*-\s+(?=[A-Z])|\s*,\s*|\s+\(|\s+near\s+|-(?=A\s)", name)[0].strip(" -&,.")
    short = re.sub(rf"\s*\b{re.escape(city.name)}$", "", name, flags=re.I).strip()
    # 'Calangute Beach Goa' → 'Calangute Beach', but keep 'Old Goa' and 'Churches and Convents of Goa'
    if short and not re.fullmatch(r"(?i)old|new|north|south|east|west|upper|lower|greater|central", short) \
            and not re.search(r"(?i)\b(of|in|at|the|and|&)$", short):
        name = short
    if name.isupper() and len(name) > 4:
        name = name.title()
    if len(name) > MAX_NAME:
        name = name[:MAX_NAME].rsplit(" ", 1)[0].rstrip(" &-,")
    return re.sub(r"\s{2,}", " ", name) or city.name


def area_of(address: str | None, city: City) -> str:
    """The neighbourhood: the last part of the address that isn't a plus code, a house
    number, an administrative label, the city/state, or a PIN code.
    'FQX8+9HJ, Candolim, Goa 403515' → 'Candolim'."""
    if not address:
        return city.name
    skip = {city.name.lower(), city.state.lower(), city.country.lower()}
    parts = []
    for part in (p.strip() for p in address.split(",")):
        part = re.sub(r"\s+(Rural|Urban)$", "", part)
        if not part or PLUS_CODE.match(part) or re.search(r"\d", part) or part.lower() in skip or ADMIN_AREA.search(part):
            continue
        parts.append(part)
    return parts[-1] if parts else city.name


STOPWORDS = {"the", "of", "and", "a", "view", "point", "viewpoint", "full", "garden", "park", "temple", "falls", "fall",
             "waterfall", "waterfalls", "beach", "fort", "palace", "lake", "top", "hill", "sri", "shri", "old", "new"}


def _tokens(name: str) -> set[str]:
    words = {re.sub(r"'s$", "", w) for w in re.findall(r"[a-z']+", name.lower())}
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def dedupe_places(places: list[Place], city: City) -> list[Place]:
    """Drop near-duplicates ('Raja's Seat' / 'Raja Seat Garden' / 'The seat of the king'):
    places within 1.5 km that share a distinctive word. Keeps the better-rated one."""
    city_words = _tokens(city.name)
    kept: list[Place] = []
    for p in sorted(places, key=lambda p: -p.rating):
        words = _tokens(p.name) - city_words
        if any(words & (_tokens(k.name) - city_words) and haversine_km(p.lat, p.lng, k.lat, k.lng) < 1.5 for k in kept):
            continue
        kept.append(p)
    order = {p.id: i for i, p in enumerate(places)}
    return sorted(kept, key=lambda p: order[p.id])


def _to_24h(t: str, meridiem_hint: str | None) -> str | None:
    m = re.match(r"\s*(\d{1,2})(?::(\d{2}))?\s*([AP]M)?", t, re.I)
    if not m:
        return None
    h, mins = int(m.group(1)), int(m.group(2) or 0)
    ampm = (m.group(3) or meridiem_hint or "").upper()
    if ampm == "PM" and h != 12:
        h += 12
    if ampm == "AM" and h == 12:
        h = 0
    return f"{h % 24:02d}:{mins:02d}"


def parse_hours(text: str | None) -> str:
    """'9 AM–6 PM' → '09:00–18:00'; '10 AM–1 PM, 2–5:30 PM' → '10:00–17:30'."""
    if not text:
        return "Hours not listed"
    t = text.replace(" ", " ").replace(" ", " ").strip()
    if "24 hours" in t.lower():
        return "Open 24 hours"
    if t.lower().startswith("closed"):
        return "Closed today"
    ranges = [r.strip() for r in t.split(",") if "–" in r or "-" in r]
    if not ranges:
        return t
    first = re.split(r"[–-]", ranges[0])
    last = re.split(r"[–-]", ranges[-1])
    close_hint = re.search(r"[AP]M", last[1], re.I)
    open_hint = re.search(r"[AP]M", first[0], re.I) or re.search(r"[AP]M", first[1], re.I)
    opens = _to_24h(first[0], open_hint.group(0) if open_hint else None)
    closes = _to_24h(last[1], close_hint.group(0) if close_hint else None)
    return f"{opens}–{closes}" if opens and closes else t


def _first_hours(operating_hours: dict | None) -> str:
    if not operating_hours:
        return "Hours not listed"
    # the dict starts with today's weekday; take the first day that isn't closed
    for value in operating_hours.values():
        parsed = parse_hours(value)
        if parsed != "Closed today":
            return parsed
    return "Closed today"


def parse_hotels(raw: dict, city: City, checkin: date, checkout: date, pax: int) -> list[Hotel]:
    rooms = links.rooms_for(pax)
    nights = (checkout - checkin).days
    hotels = []
    for i, p in enumerate(raw.get("properties") or []):
        rate = (p.get("rate_per_night") or {}).get("extracted_lowest")
        gps = p.get("gps_coordinates") or {}
        if not rate or "latitude" not in gps:
            continue
        nightly = int(rate)
        name = clean_name(p["name"], city)
        hotel_links = links.hotel_links(name, city, checkin, checkout, pax)
        if p.get("link"):
            hotel_links.insert(0, Link(label="Hotel website", url=p["link"]))
        hotels.append(Hotel(
            # property_token is stable across searches, so a hotel the traveller picked survives a re-search
            id=f"h-{p.get('property_token') or re.sub(r'[^a-z0-9]+', '-', name.lower())[:40]}",
            name=name, area=p.get("neighborhood") or city.name,
            rating=float(p.get("overall_rating") or 0), reviews=int(p.get("reviews") or 0),
            stars=int(p.get("extracted_hotel_class") or 0), nightly_price=nightly,
            lat=gps["latitude"], lng=gps["longitude"], amenities=(p.get("amenities") or [])[:6],
            rooms=rooms, total_price=nightly * rooms * nights, links=hotel_links,
        ))
    return hotels


def parse_places(raw: dict, city: City) -> tuple[list[Place], dict[str, list[str]]]:
    places, tags = [], {}
    for r in raw.get("local_results") or []:
        gps = r.get("gps_coordinates") or {}
        if "latitude" not in gps or not r.get("title"):
            continue
        types = r.get("types") or ([r["type"]] if r.get("type") else [])
        if (types and NOT_ATTRACTIONS.search(types[0])) or STRONG_NOT_ATTRACTION.search(r["title"]):
            continue  # a hotel, taxi service, shop… listed among "attractions"
        category, fee, minutes = _classify(types, r["title"])
        if city.international:
            fee *= INTERNATIONAL_FEE_MULTIPLIER
        hours = _first_hours(r.get("operating_hours"))
        if hours == "Closed today":
            continue
        pid = f"p-{r.get('place_id') or r.get('data_id') or len(places)}"
        bookable = category == "adventure" or fee >= 500
        place = Place(
            id=pid, name=clean_name(r["title"], city), category=category, area=area_of(r.get("address"), city),
            rating=float(r.get("rating") or 4.0), lat=gps["latitude"], lng=gps["longitude"],
            fee_per_person=fee, fee_is_estimate=True, duration_min=minutes, hours=hours,
            description=r.get("description") or (types[0] if types else "Popular spot"),
        )
        place.links = links.activity_links(place.name, city, place.lat, place.lng, bookable)
        places.append(place)
        tags[pid] = [_classify([t])[0] for t in types[1:]]
    places = dedupe_places(places, city)
    return places, {p.id: tags[p.id] for p in places}


PRICE_LEVEL = {"₹": 250, "₹₹": 500, "₹₹₹": 1000, "₹₹₹₹": 2000, "$": 800, "$$": 1500, "$$$": 3000, "$$$$": 5000}


# Typical cost per person when Google shows no price, by restaurant type (checked in order).
TYPE_COST: list[tuple[tuple[str, ...], int]] = [
    (("fine dining", "cocktail bar", "lounge", "steak house", "wine bar"), 1200),
    (("bar", "bistro", "seafood", "continental", "italian", "japanese", "pan-asian", "european", "brewpub"), 700),
    (("cafe", "coffee", "bakery", "fast food", "vegetarian", "south indian", "street food", "dhaba", "snack", "tea", "sweet"), 250),
]
DEFAULT_COST = 450


def _cost_per_person(price: str | None, types: list[str] = ()) -> int:
    if not price:
        text = " ".join(types).lower()
        for keys, cost in TYPE_COST:
            if any(re.search(rf"\b{re.escape(k)}\b", text) for k in keys):
                return cost
        return DEFAULT_COST
    price = price.replace(",", "")
    nums = [int(n) for n in re.findall(r"\d+", price)]
    if nums:
        return int(sum(nums[:2]) / min(len(nums), 2))
    return PRICE_LEVEL.get(price.strip(), 400)


def parse_restaurants(raw: dict, city: City) -> list[Restaurant]:
    out = []
    for r in raw.get("local_results") or []:
        gps = r.get("gps_coordinates") or {}
        if "latitude" not in gps or not r.get("title"):
            continue
        types = r.get("types") or ([r["type"]] if r.get("type") else [])
        rest = Restaurant(
            id=f"r-{r.get('place_id') or r.get('data_id') or len(out)}", name=clean_name(r["title"], city),
            cuisine=", ".join(types[:2]) or "Restaurant", area=area_of(r.get("address"), city),
            rating=float(r.get("rating") or 4.0), lat=gps["latitude"], lng=gps["longitude"],
            cost_per_person=_cost_per_person(r.get("price"), types),
        )
        rest.links = [Link(label="Map", url=links.google_maps(rest.lat, rest.lng, f"{rest.name}, {rest.area}"))]
        out.append(rest)
    return out


def _maps_params(query: str, city: City) -> dict:
    return {"engine": "google_maps", "type": "search", "q": query,
            "ll": f"@{city.lat},{city.lng},12z", "hl": "en", "gl": "in"}


# Typical price per room per night when live hotel prices aren't available:
# (label, stars, price in India, price abroad).
HOTEL_TIERS = [
    ("Budget hotel or guesthouse", 2, 1500, 3500),
    ("Mid-range hotel", 3, 3200, 6500),
    ("Upscale hotel", 4, 6500, 12000),
]


def estimate_hotels(city: City, places: list[Place], checkin: date, checkout: date, pax: int) -> list[Hotel]:
    """Three typical stays (budget / mid-range / upscale), placed among the top sights and
    flagged as estimates, with links to search real hotels for the dates."""
    rooms = links.rooms_for(pax)
    nights = (checkout - checkin).days
    top = sorted(places, key=lambda p: -p.rating)[:10]
    lat = sorted(p.lat for p in top)[len(top) // 2] if top else city.lat
    lng = sorted(p.lng for p in top)[len(top) // 2] if top else city.lng
    search = f"hotels in {city.name}"
    hotel_links = [
        Link(label="Booking.com", url=links.booking_com(city.name, checkin, checkout, pax)),
        Link(label="Google Hotels", url=links.google_hotels(search)),
    ]
    hotels = []
    for label, stars, india, abroad in HOTEL_TIERS:
        nightly = abroad if city.international else india
        hotels.append(Hotel(
            id=f"h-est-{stars}", name=label, area=f"Central {city.name}", rating=4.0, reviews=0, stars=stars,
            nightly_price=nightly, lat=lat, lng=lng, rooms=rooms, total_price=nightly * rooms * nights,
            links=hotel_links, is_estimate=True,
        ))
    return hotels


async def fetch_live(city: City, checkin: date, checkout: date, pax: int) -> DestinationData:
    hotel_params = {
        "engine": "google_hotels", "q": f"hotels in {city.name}",
        "check_in_date": checkin.isoformat(), "check_out_date": checkout.isoformat(),
        "adults": min(pax, 2),  # price one room; we multiply by the number of rooms
        "currency": "INR", "gl": "in", "hl": "en",
    }
    # Each search can fail on its own (daily cap, quota used up). Sights and food then come from
    # an older Google copy or, failing that, open data; hotels fall back to typical prices.
    hotels_raw, places_raw, food_raw = await asyncio.gather(
        serpapi(hotel_params, HOTELS_TTL_HOURS),
        serpapi(_maps_params(f"top tourist attractions in {city.name}", city), PLACES_TTL_HOURS, PLACES_STALE_DAYS),
        serpapi(_maps_params(f"popular restaurants in {city.name}", city), PLACES_TTL_HOURS, PLACES_STALE_DAYS),
        return_exceptions=True,
    )
    for result in (hotels_raw, places_raw, food_raw):
        if isinstance(result, BaseException) and not isinstance(result, ProviderError):
            raise result
    places, tags = parse_places(places_raw, city) if isinstance(places_raw, dict) else ([], {})
    restaurants = parse_restaurants(food_raw, city) if isinstance(food_raw, dict) else []
    credits: list[Link] = []
    if not places or not restaurants:
        from .open_places import fetch_open
        try:
            open_places, open_tags, open_food, credits = await fetch_open(city)
        except ProviderError:
            raise ProviderError(
                f"We've used today's live searches and couldn't find enough about {city.name} in open data. "
                "Try again tomorrow, or pick a nearby destination."
            ) from None
        if not places:
            places, tags = open_places, open_tags
        if not restaurants:
            restaurants = open_food
    hotels = [] if isinstance(hotels_raw, ProviderError) else parse_hotels(hotels_raw, city, checkin, checkout, pax)
    if not hotels:  # no live prices for these dates: typical prices instead
        hotels = estimate_hotels(city, places, checkin, checkout, pax)
    return DestinationData(hotels, places, restaurants, tags, credits)
