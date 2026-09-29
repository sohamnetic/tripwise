"""Deep links to real booking sites. Pure functions: no network, easy to unit-test."""

import math
import re
from datetime import date
from urllib.parse import quote_plus, urlencode

from ..models.schemas import City, Link, Package


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---- flights -------------------------------------------------------------

def google_flights(o: City, d: City, out: date, back: date, adults: int) -> str:
    q = f"Flights to {d.iata} from {o.iata} on {out.isoformat()} through {back.isoformat()} for {adults} adults"
    return "https://www.google.com/travel/flights?" + urlencode({"q": q, "curr": "INR", "hl": "en-IN"})


def skyscanner(o: City, d: City, out: date, back: date, adults: int) -> str:
    return (
        f"https://www.skyscanner.co.in/transport/flights/{o.iata.lower()}/{d.iata.lower()}/"
        f"{out:%y%m%d}/{back:%y%m%d}/?adultsv2={adults}&currency=INR"
    )


def makemytrip_flights(o: City, d: City, out: date, back: date, adults: int) -> str:
    itinerary = f"{o.iata}-{d.iata}-{out:%d/%m/%Y}_{d.iata}-{o.iata}-{back:%d/%m/%Y}"
    params = {
        "itinerary": itinerary,
        "tripType": "R",
        "paxType": f"A-{adults}_C-0_I-0",
        "intl": str(o.international or d.international).lower(),
        "cabinClass": "E",
    }
    return "https://www.makemytrip.com/flight/search?" + urlencode(params, safe="/_-")


def flight_links(o: City, d: City, out: date, back: date, adults: int) -> list[Link]:
    return [
        Link(label="Google Flights", url=google_flights(o, d, out, back, adults)),
        Link(label="Skyscanner", url=skyscanner(o, d, out, back, adults)),
        Link(label="MakeMyTrip", url=makemytrip_flights(o, d, out, back, adults)),
    ]


# ---- trains & buses ------------------------------------------------------

def train_links(o: City, d: City) -> list[Link]:
    q = quote_plus(f"trains from {o.name} to {d.name}")
    return [
        Link(label="IRCTC", url="https://www.irctc.co.in/nget/train-search"),
        Link(label="Compare trains", url=f"https://www.google.com/search?q={q}"),
    ]


def bus_links(o: City, d: City, day: date | None = None) -> list[Link]:
    url = f"https://www.redbus.in/bus-tickets/{_slug(o.name)}-to-{_slug(d.name)}"
    if day:  # redBus opens the route page on this date
        url += "?" + urlencode({"onward": f"{day:%d-%b-%Y}", "doj": f"{day:%d-%b-%Y}"})
    return [Link(label="redBus", url=url)]


# ---- hotels --------------------------------------------------------------

def rooms_for(travellers: int) -> int:
    return math.ceil(travellers / 2)


def booking_com(search: str, checkin: date, checkout: date, adults: int) -> str:
    params = {
        "ss": search,
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "group_adults": adults,
        "no_rooms": rooms_for(adults),
        "selected_currency": "INR",
    }
    return "https://www.booking.com/searchresults.html?" + urlencode(params)


def google_hotels(search: str) -> str:
    return "https://www.google.com/travel/search?" + urlencode({"q": search, "curr": "INR"})


def hotel_links(hotel_name: str, city: City, checkin: date, checkout: date, adults: int) -> list[Link]:
    search = f"{hotel_name}, {city.name}"
    # (MakeMyTrip's hotel search needs its internal city codes, so a plain link just lands on
    # its hotels home page; we leave it out.)
    return [
        Link(label="Booking.com", url=booking_com(search, checkin, checkout, adults)),
        Link(label="Google Hotels", url=google_hotels(search)),
    ]


# ---- places --------------------------------------------------------------

def google_maps(lat: float, lng: float, name: str | None = None) -> str:
    query = f"{name}" if name else f"{lat},{lng}"
    return "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": query})


def activity_links(name: str, city: City, lat: float, lng: float, bookable: bool) -> list[Link]:
    links = [Link(label="Map", url=google_maps(lat, lng, f"{name}, {city.name}"))]
    if bookable:
        q = f"{name} {city.name}"
        # (GetYourGuide's search URL ignores the query when opened directly, so only Klook.)
        links.append(Link(label="Klook", url="https://www.klook.com/en-IN/search/result/?" + urlencode({"query": q})))
    return links


# ---- packages ------------------------------------------------------------

# Destinations that Thrillophilia files under /states/ rather than /cities/.
THRILLOPHILIA_STATES = {"goa", "lakshadweep"}


def packages(city: City, nights: int) -> list[Package]:
    """Package pages checked by hand (Sep 2026) for Jaipur, Goa, Coorg, Manali and Havelock."""
    slug = _slug(city.name)
    klook = Package(provider="Klook", title=f"Things to do in {city.name}",
                    url="https://www.klook.com/en-IN/search/result/?" + urlencode({"query": city.name}))
    if city.international:
        return [
            klook,
            Package(provider="Google", title=f"{city.name} packages from India",
                    url="https://www.google.com/search?" + urlencode({"q": f"{city.name} tour packages from India"})),
        ]
    kind = "states" if slug in THRILLOPHILIA_STATES else "cities"
    return [
        Package(provider="MakeMyTrip Holidays", title=f"{city.name} holiday packages",
                url=f"https://www.makemytrip.com/holidays-india/{slug}-travel-packages.html"),
        Package(provider="Thrillophilia", title=f"{city.name} tour packages",
                url=f"https://www.thrillophilia.com/{kind}/{slug}/tours"),
        Package(provider="Yatra", title=f"{city.name} tour packages",
                url=f"https://www.yatra.com/india-tour-packages/holidays-in-{slug}"),
        klook,
    ]
