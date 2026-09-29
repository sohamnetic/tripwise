"""Sights and restaurants from free, open data, for when Google results (via SerpApi) aren't
available.

- Sights: Wikidata's well-known places near the city, ranked by how many Wikipedia language
  editions cover them, plus Wikivoyage's "See" and "Do" listings, written by travellers and
  often with prices and opening hours.
- Beaches: OpenStreetMap via Geoapify. Wikidata records Calangute as a village rather than a
  beach, so each beach is ranked by how well known its village is.
- Restaurants: OpenStreetMap via Geoapify, near the main sights, plus Wikivoyage "Eat" listings.

None of these have star ratings, so `rating` only ranks places here and `rating_known` is False.
"""

import asyncio
import html
import math
import re
from difflib import SequenceMatcher

from ..config import get_settings
from ..models.schemas import City, Link, Place, Restaurant
from ..services import links
from .base import ProviderError, cached_get
from .geocode import haversine_km
from .live_destination import (ADMIN_AREA, INTERNATIONAL_FEE_MULTIPLIER, _classify, _cost_per_person, clean_name,
                               dedupe_places, parse_hours)

WIKIDATA_URL = "https://query.wikidata.org/sparql"
WIKIVOYAGE_URL = "https://en.wikivoyage.org/w/api.php"
GEOAPIFY_URL = "https://api.geoapify.com/v2/places"
# Wikimedia asks API users to identify themselves with a contact URL.
HEADERS = {"User-Agent": "Tripwise/1.0 (budget trip planner; https://github.com/sohamnetic/tripwise)"}
OPEN_TTL_HOURS = 24 * 30  # sights and restaurants barely change
RADIUS_KM = 30
MAX_PLACES = 40

# Wikidata types (the English labels of "instance of") that make a place worth visiting…
SIGHT_TYPES = re.compile(
    r"\b(temple|church|cathedral|basilica|chapel|mosque|masjid|dargah|gurdwara|monastery|stupa|shrine|fort|fortress|"
    r"castle|palace|museum|gallery|monument|memorial|mausoleum|tomb|ruins|archaeological|world heritage|beach|"
    r"waterfall|lake|reservoir|dam|garden|park|wildlife|sanctuary|protected area|zoo|aquarium|valley|mountain pass|"
    r"viewpoint|cave|island|lighthouse|ghat|arch|stepwell|observatory|tourist attraction|market|bazaar|bridge|"
    r"planetarium|minaret|tower|square)\b", re.I)
# …and ones that don't, even if they match above (e.g. "industrial park", "river island|village").
NOT_SIGHT_TYPES = re.compile(
    r"\b(village|town|city|settlement|hamlet|district|taluk|tehsil|constituency|state|region|river|stream|airport|"
    r"aerodrome|railway|station|school|college|university|institute|hospital|stadium|cricket|hotel|road|highway|"
    r"tunnel|company|organization|battle|siege|operation|festival|tournament|outbreak|language|dialect|territorial|"
    r"locality|quarter|electoral|library|official residence|port|naval|research|industrial|technology|business|"
    r"mountain range|summit|census|diocese|archdiocese|eparchy|parish)\b", re.I)
SETTLEMENT_TYPES = re.compile(r"\b(village|town|city|settlement|hamlet|locality|quarter|census town|hill station)\b", re.I)
MIN_LINKS_FOR_BRIDGE = 15  # Howrah Bridge yes, every road bridge no
SNACKS = re.compile(r"\b(tea|coffee|coffee shop|ice cream|kulfi|juice|dessert|cake|donut|frozen yogurt|bubble tea|"
                    r"sweets?|bakery|confectionery|chaat|pan|paan)\b", re.I)
SNACK_NAMES = re.compile(r"\b(tea|chai|kulfi|gulfi|ice ?cream|juice|lassi|sweets|bakery|bakers|paan)\b", re.I)
CHAINS = re.compile(r"\b(domino'?s|mcdonald'?s|kfc|pizza hut|subway|starbucks|burger king|cafe coffee day|ccd|"
                    r"barista|dunkin|baskin|haldiram'?s|wow! momo|la pino'?z)\b", re.I)


def _fame(links_count: int) -> float:
    """Our ranking score on the same scale as Google ratings: 2 Wikipedia editions → 4.2,
    10 → 4.5, 25+ → 4.75, capped at 4.8."""
    return round(min(4.8, 3.9 + 0.18 * math.log2(links_count + 1)), 2)


# ---- Wikidata ---------------------------------------------------------------------------------

def wikidata_query(city: City, km: int = RADIUS_KM) -> str:
    return f"""
SELECT ?item ?itemLabel ?itemDescription ?lat ?lon ?links (GROUP_CONCAT(DISTINCT ?tl; separator="|") AS ?types) WHERE {{
  SERVICE wikibase:around {{ ?item wdt:P625 ?coord. bd:serviceParam wikibase:center "Point({city.lng} {city.lat})"^^geo:wktLiteral;
                             wikibase:radius "{km}". }}
  ?item wikibase:sitelinks ?links. FILTER(?links >= 2)
  ?item wdt:P31 ?t. ?t rdfs:label ?tl. FILTER(LANG(?tl) = "en")
  BIND(geof:latitude(?coord) AS ?lat) BIND(geof:longitude(?coord) AS ?lon)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}} GROUP BY ?item ?itemLabel ?itemDescription ?lat ?lon ?links ORDER BY DESC(?links) LIMIT 300"""


def parse_wikidata(raw: dict, city: City) -> tuple[list[Place], dict[str, list[str]], list[tuple[str, int, float, float]]]:
    """Returns (sights, extra interest tags per sight, nearby settlements as (name, links, lat, lng))."""
    places: list[Place] = []
    tags: dict[str, list[str]] = {}
    settlements: list[tuple[str, int, float, float]] = []
    seen: set[str] = set()
    for b in (raw.get("results") or {}).get("bindings") or []:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        name = b.get("itemLabel", {}).get("value", "")
        if qid in seen or not name or re.fullmatch(r"Q\d+", name):
            continue
        seen.add(qid)
        types = [t for t in b.get("types", {}).get("value", "").split("|") if t]
        type_text = " | ".join(types)
        lat, lng, n_links = float(b["lat"]["value"]), float(b["lon"]["value"]), int(b["links"]["value"])
        if NOT_SIGHT_TYPES.search(type_text):
            if SETTLEMENT_TYPES.search(type_text):
                settlements.append((name, n_links, lat, lng))
            continue
        if not SIGHT_TYPES.search(type_text):
            continue
        if re.search(r"\bbridge\b", type_text, re.I) and n_links < MIN_LINKS_FOR_BRIDGE:
            continue
        category, fee, minutes = _classify(types, name)
        if city.international:
            fee *= INTERNATIONAL_FEE_MULTIPLIER
        desc = b.get("itemDescription", {}).get("value") or types[0]
        place = Place(
            id=f"p-wd-{qid}", name=clean_name(name, city), category=category, area=city.name,
            rating=_fame(n_links), rating_known=False, lat=lat, lng=lng, fee_per_person=fee, fee_is_estimate=True,
            duration_min=minutes, hours="Hours not listed", description=desc[:1].upper() + desc[1:],
        )
        place.links = links.activity_links(place.name, city, lat, lng, category == "adventure" or fee >= 500)
        places.append(place)
        tags[place.id] = [_classify([t])[0] for t in types[1:]]
    return places, tags, settlements


def nearest_area(lat: float, lng: float, settlements: list[tuple[str, int, float, float]], city: City, max_km: float = 6) -> str:
    near = [(haversine_km(lat, lng, s[2], s[3]), s[0]) for s in settlements]
    near = [n for n in near if n[0] <= max_km]
    return clean_name(min(near)[1], city) if near else city.name


# ---- Wikivoyage ---------------------------------------------------------------------------------

LISTING = re.compile(r"\{\{\s*(see|do|eat|listing|marker)\s*\n?\s*\|(.*?)\}\}", re.S | re.I)


def _unwiki(text: str) -> str:
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", text)  # [[target|label]] → label
    text = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", text)  # [url label] → label
    text = re.sub(r"<ref[^>]*>.*?</ref>|<[^>]+>|'{2,}", "", text, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def listing_fields(body: str) -> dict[str, str]:
    body = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", body)  # so "|" inside links doesn't split fields
    return {m.group(1).lower(): m.group(2).strip() for m in re.finditer(r"\|\s*([a-z_]+)\s*=\s*([^|]*)", "|" + body)}


def parse_fee(price: str) -> int | None:
    """'₹50 (Indians), ₹300 (foreigners)' → 50 (the Indian rate comes first); 'Free' → 0."""
    m = re.search(r"(?:₹|rs\.?|inr)\s*(\d[\d,]*)", price, re.I)
    if m:
        return int(m.group(1).replace(",", ""))
    if re.search(r"\bfree\b", price, re.I):
        return 0
    return None


def _clean_hours(text: str) -> str:
    h = parse_hours(_unwiki(text)) if text else "Hours not listed"
    # Only the forms the scheduler understands; anything else ("closed Mondays") could be misread.
    return h if re.fullmatch(r"\d{2}:\d{2}–\d{2}:\d{2}|Open 24 hours", h) else "Hours not listed"


def _first_sentence(text: str, limit: int = 180) -> str:
    text = _unwiki(re.sub(r"\{\{[^{}]*\}\}", "", text))
    sentence = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    return sentence if len(sentence) <= limit else sentence[:limit].rsplit(" ", 1)[0] + "…"


def parse_wikivoyage(raw: dict, city: City) -> tuple[list[tuple[Place, str | None]], list[Restaurant]]:
    """Returns ([(sight, its Wikidata id if given)], restaurants). Listings without coordinates,
    or implausibly far away, are skipped."""
    wikitext = ((raw.get("parse") or {}).get("wikitext") or {}).get("*", "")
    sights: list[tuple[Place, str | None]] = []
    food: list[Restaurant] = []
    for i, (kind, body) in enumerate(LISTING.findall(wikitext)):
        f = listing_fields(body)
        kind = kind.lower() if kind.lower() in ("see", "do", "eat") else f.get("type", "").lower()
        name = _unwiki(f.get("name", ""))
        try:
            lat, lng = float(f.get("lat", "")), float(f.get("long", ""))
        except ValueError:
            continue
        if kind not in ("see", "do", "eat") or not name or haversine_km(lat, lng, city.lat, city.lng) > RADIUS_KM * 1.5:
            continue
        content = _first_sentence(f.get("content", "") or f.get("description", ""))
        if kind == "eat":
            if SNACK_NAMES.search(name):
                continue
            rest = Restaurant(
                id=f"r-wv-{i}", name=clean_name(name, city), cuisine="Local favourite", area=city.name, rating=4.35,
                rating_known=False, lat=lat, lng=lng, cost_per_person=_cost_per_person(f.get("price") or None, [content]),
            )
            rest.links = [Link(label="Map", url=links.google_maps(lat, lng, f"{rest.name}, {city.name}"))]
            food.append(rest)
            continue
        category, fee, minutes = _classify([], f"{name} {content}")
        if kind == "do" and category == "sightseeing":
            category = "adventure" if re.search(r"trek|raft|paraglid|dive|surf|kayak|safari", content, re.I) else category
        listed_fee = parse_fee(f.get("price", ""))
        place = Place(
            id=f"p-wv-{re.sub(r'[^a-z0-9]+', '-', name.lower())[:40]}", name=clean_name(name, city), category=category,
            area=city.name, rating=4.35, rating_known=False, lat=lat, lng=lng,
            fee_per_person=fee if listed_fee is None else listed_fee, fee_is_estimate=listed_fee is None,
            duration_min=minutes, hours=_clean_hours(f.get("hours", "")), description=content or "Recommended by Wikivoyage",
        )
        place.links = links.activity_links(place.name, city, lat, lng, category == "adventure" or place.fee_per_person >= 500)
        sights.append((place, f.get("wikidata") or None))
    return sights, food


# ---- Geoapify (OpenStreetMap) ----------------------------------------------------------------------

def _geo_area(props: dict, city: City) -> str:
    for key in ("suburb", "district", "city", "county"):
        value = props.get(key)
        if value and value.lower() not in (city.name.lower(), city.state.lower()) and not ADMIN_AREA.search(value):
            return clean_name(value, city)
    return city.name


def parse_geo_beaches(raw: dict, city: City, settlements: list[tuple[str, int, float, float]]) -> list[Place]:
    places = []
    for feat in raw.get("features") or []:
        p = feat.get("properties") or {}
        if not p.get("name"):
            continue
        name = clean_name(p["name"], city)
        words = set(re.findall(r"[a-z]+", name.lower())) - {"beach", "the", "of"}
        # a beach is as well known as the village it's named after (Calangute Beach ↔ Calangute)
        fame = max((s[1] for s in settlements if set(re.findall(r"[a-z]+", s[0].lower())) & words), default=1)
        place = Place(
            id=f"p-geo-{p.get('place_id', '')[:32]}", name=name, category="beaches", area=_geo_area(p, city),
            rating=_fame(fame), rating_known=False, lat=p["lat"], lng=p["lon"], fee_per_person=0,
            fee_is_estimate=True, duration_min=120, hours="Open 24 hours", description="Beach",
        )
        place.links = links.activity_links(place.name, city, place.lat, place.lng, False)
        places.append(place)
    return places


def parse_geo_restaurants(raw: dict, city: City) -> list[Restaurant]:
    out = []
    for feat in raw.get("features") or []:
        p = feat.get("properties") or {}
        raw_tags = (p.get("datasource") or {}).get("raw") or {}
        if not p.get("name"):
            continue
        cuisines = [c.strip().replace("_", " ").lower() for c in str(raw_tags.get("cuisine", "")).split(";") if c.strip()]
        if (cuisines and all(SNACKS.search(c) for c in cuisines)) or SNACK_NAMES.search(p["name"]):
            continue  # a tea stall or ice-cream shop, not somewhere for lunch or dinner
        is_cafe = "catering.cafe" in (p.get("categories") or [])
        types = cuisines + (["cafe"] if is_cafe else [])
        score = 4.0 + 0.15 * bool(cuisines) + 0.1 * bool(raw_tags.get("website") or raw_tags.get("opening_hours"))
        if CHAINS.search(p["name"]):
            score -= 0.3  # suggest local places over chains
        rest = Restaurant(
            id=f"r-geo-{p.get('place_id', '')[:32]}", name=clean_name(p["name"], city),
            cuisine=", ".join(c.title() for c in cuisines[:2]) or ("Cafe" if is_cafe else "Restaurant"),
            area=_geo_area(p, city), rating=round(score, 2), rating_known=False, lat=p["lat"], lng=p["lon"],
            cost_per_person=_cost_per_person(None, types),
        )
        rest.links = [Link(label="Map", url=links.google_maps(rest.lat, rest.lng, f"{rest.name}, {rest.area}"))]
        out.append(rest)
    return out


def drop_spelling_variants(places: list[Place], km: float = 5) -> list[Place]:
    """Wikidata and Wikivoyage spell some places differently ('Bhrigu Lake' / 'Brighu Lake',
    'Rehala Falls' / 'Rahala waterfalls'): drop close matches nearby, keeping the better known."""
    def norm(name: str) -> str:
        return re.sub(r"waterfalls?|falls", "falls", name.lower())
    kept: list[Place] = []
    for p in sorted(places, key=lambda p: -p.rating):
        if any(SequenceMatcher(None, norm(p.name), norm(k.name)).ratio() >= 0.8
               and haversine_km(p.lat, p.lng, k.lat, k.lng) <= km for k in kept):
            continue
        kept.append(p)
    return kept


def _food_centres(city: City, places: list[Place], n: int = 3, apart_km: float = 6) -> list[tuple[float, float]]:
    """Where to look for restaurants: the city centre plus the best sights far from it."""
    centres = [(city.lat, city.lng)]
    for p in sorted(places, key=lambda p: -p.rating):
        if len(centres) >= n:
            break
        if all(haversine_km(p.lat, p.lng, a, b) > apart_km for a, b in centres):
            centres.append((p.lat, p.lng))
    return centres


# ---- putting it together -----------------------------------------------------------------------------

def _geo_params(categories: str, lat: float, lng: float, radius_km: float, limit: int) -> dict:
    return {"categories": categories, "filter": f"circle:{lng},{lat},{int(radius_km * 1000)}",
            "bias": f"proximity:{lng},{lat}", "limit": limit, "lang": "en"}


async def _geoapify(params: dict) -> dict:
    key = get_settings().geoapify_key
    if not key:
        raise ProviderError("GEOAPIFY_KEY is not set.")
    return await cached_get(GEOAPIFY_URL, params, OPEN_TTL_HOURS, secret={"apiKey": key})


async def fetch_open(city: City) -> tuple[list[Place], dict[str, list[str]], list[Restaurant], list[Link]]:
    """(sights, extra interest tags, restaurants, credits). Raises ProviderError if there isn't
    enough to plan with."""
    wd_raw, wv_raw, beach_raw = await asyncio.gather(
        cached_get(WIKIDATA_URL, {"query": wikidata_query(city), "format": "json"}, OPEN_TTL_HOURS, headers=HEADERS),
        cached_get(WIKIVOYAGE_URL, {"action": "parse", "page": city.name, "prop": "wikitext", "format": "json",
                                    "redirects": 1}, OPEN_TTL_HOURS, headers=HEADERS),
        _geoapify(_geo_params("beach", city.lat, city.lng, RADIUS_KM, 60)),
        return_exceptions=True,
    )
    for r in (wd_raw, wv_raw, beach_raw):
        if isinstance(r, BaseException) and not isinstance(r, ProviderError):
            raise r
    credits: list[Link] = []
    places: list[Place] = []
    tags: dict[str, list[str]] = {}
    settlements: list[tuple[str, int, float, float]] = []
    food: list[Restaurant] = []

    if isinstance(wd_raw, dict):
        places, tags, settlements = parse_wikidata(wd_raw, city)
        for p in places:
            p.area = nearest_area(p.lat, p.lng, settlements, city)
        if places:
            credits.append(Link(label="Wikidata", url="https://www.wikidata.org/"))
    if isinstance(wv_raw, dict) and "parse" in wv_raw:
        wv_sights, food = parse_wikivoyage(wv_raw, city)
        by_qid = {p.id.removeprefix("p-wd-"): p for p in places}
        for sight, qid in wv_sights:
            known = by_qid.get(qid or "")
            if known:  # the same place: take Wikivoyage's traveller-written details
                known.description = sight.description
                known.rating = min(4.8, known.rating + 0.1)
                if not sight.fee_is_estimate:
                    known.fee_per_person, known.fee_is_estimate = sight.fee_per_person, False
                if sight.hours != "Hours not listed":
                    known.hours = sight.hours
            else:
                sight.area = nearest_area(sight.lat, sight.lng, settlements, city)
                places.append(sight)
                tags[sight.id] = []
        if wv_sights or food:
            title = wv_raw["parse"].get("title", city.name).replace(" ", "_")
            credits.append(Link(label="Wikivoyage (CC BY-SA)", url=f"https://en.wikivoyage.org/wiki/{title}"))
    if isinstance(beach_raw, dict):
        beaches = parse_geo_beaches(beach_raw, city, settlements)
        places += beaches
        tags.update({b.id: [] for b in beaches})

    places = drop_spelling_variants(dedupe_places(places, city))[:MAX_PLACES]
    if len(places) < 3:
        raise ProviderError(f"Not enough open data about {city.name} to plan a trip.")

    if get_settings().geoapify_key:
        results = await asyncio.gather(
            *(_geoapify(_geo_params("catering.restaurant,catering.cafe", lat, lng, 5, 40))
              for lat, lng in _food_centres(city, places)),
            return_exceptions=True,
        )
        seen = {r.name.lower() for r in food}
        for raw in results:
            if isinstance(raw, dict):
                for r in parse_geo_restaurants(raw, city):
                    if r.name.lower() not in seen:
                        seen.add(r.name.lower())
                        food.append(r)
    if any(p.id.startswith("p-geo-") for p in places) or any(r.id.startswith("r-geo-") for r in food):
        credits += [Link(label="© OpenStreetMap contributors", url="https://www.openstreetmap.org/copyright"),
                    Link(label="Powered by Geoapify", url="https://www.geoapify.com/")]
    if not food:
        raise ProviderError(f"Couldn't find restaurants in {city.name} in the open data.")
    return places, {p.id: tags.get(p.id, []) for p in places}, food, credits
