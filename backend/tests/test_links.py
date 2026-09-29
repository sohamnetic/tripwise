from datetime import date
from urllib.parse import parse_qs, urlparse

from app.providers.geocode import resolve_city
from app.services import links

CCU, GOI = resolve_city("Kolkata"), resolve_city("goa")
OUT, BACK = date(2026, 11, 12), date(2026, 11, 16)


def test_skyscanner_uses_iata_and_short_dates():
    url = links.skyscanner(CCU, GOI, OUT, BACK, 2)
    assert "/ccu/goi/261112/261116/" in url
    assert "adultsv2=2" in url


def test_makemytrip_flights_round_trip():
    q = parse_qs(urlparse(links.makemytrip_flights(CCU, GOI, OUT, BACK, 3)).query)
    assert q["itinerary"] == ["CCU-GOI-12/11/2026_GOI-CCU-16/11/2026"]
    assert q["paxType"] == ["A-3_C-0_I-0"]
    assert q["intl"] == ["false"]


def test_booking_com_rooms_and_dates():
    q = parse_qs(urlparse(links.booking_com("Test Hotel, Goa", OUT, BACK, 5)).query)
    assert q["checkin"] == ["2026-11-12"] and q["checkout"] == ["2026-11-16"]
    assert q["no_rooms"] == ["3"]
    assert q["selected_currency"] == ["INR"]


def test_redbus_route_and_date():
    url = links.bus_links(resolve_city("Delhi"), resolve_city("Manali"), date(2026, 11, 12))[0].url
    assert "/bus-tickets/delhi-to-manali?" in url and "onward=12-Nov-2026" in url and "doj=12-Nov-2026" in url


def test_hotel_links_skip_makemytrip():
    labels = [l.label for l in links.hotel_links("Test Hotel", GOI, OUT, BACK, 2)]
    assert labels == ["Booking.com", "Google Hotels"]


# URL patterns checked by hand in a browser (Sep 2026).
def test_package_urls_india():
    urls = {p.provider: p.url for p in links.packages(resolve_city("Jaipur"), 4)}
    assert urls["MakeMyTrip Holidays"] == "https://www.makemytrip.com/holidays-india/jaipur-travel-packages.html"
    assert urls["Thrillophilia"] == "https://www.thrillophilia.com/cities/jaipur/tours"
    assert urls["Yatra"] == "https://www.yatra.com/india-tour-packages/holidays-in-jaipur"
    assert "klook.com" in urls["Klook"]
    goa = {p.provider: p.url for p in links.packages(GOI, 4)}
    assert goa["Thrillophilia"] == "https://www.thrillophilia.com/states/goa/tours"
    assert {p.provider: p.url for p in links.packages(resolve_city("Havelock Island"), 3)}["MakeMyTrip Holidays"].endswith(
        "/havelock-island-travel-packages.html")


def test_package_urls_abroad_avoid_indian_package_sites():
    providers = [p.provider for p in links.packages(resolve_city("Bali"), 5)]
    assert providers == ["Klook", "Google"]
