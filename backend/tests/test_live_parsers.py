"""Parsers for SerpApi responses, tested on trimmed responses in SerpApi's documented shape."""

from datetime import date

from app.providers.flights import parse_flights
from app.providers.geocode import resolve_city
from app.providers.live_destination import _cost_per_person, parse_hotels, parse_hours, parse_places, parse_restaurants

CCU, GOI = resolve_city("Kolkata"), resolve_city("Goa")

FLIGHTS = {
    "best_flights": [{
        "flights": [{
            "departure_airport": {"id": "CCU", "time": "2026-11-12 06:10"},
            "arrival_airport": {"id": "GOX", "time": "2026-11-12 08:55"},
            "airline": "IndiGo", "flight_number": "6E 5321", "duration": 165,
        }],
        "total_duration": 165, "price": 6123,
    }],
    "other_flights": [
        {"flights": [
            {"departure_airport": {"time": "2026-11-12 10:00"}, "arrival_airport": {"time": "2026-11-12 12:30"},
             "airline": "Air India", "flight_number": "AI 771"},
            {"departure_airport": {"time": "2026-11-12 14:00"}, "arrival_airport": {"time": "2026-11-12 15:30"},
             "airline": "Air India", "flight_number": "AI 663"},
        ], "total_duration": 330, "price": 7450},
        {"flights": [], "price": 5000},  # malformed: skipped
        {"flights": [{"departure_airport": {"time": "2026-11-12 10:00"}, "arrival_airport": {"time": "2026-11-12 12:00"}}]},  # no price
    ],
}


def test_parse_flights_per_person_times_pax():
    opts = parse_flights(FLIGHTS, CCU, GOI, 3, "out", [])
    assert len(opts) == 2
    first, second = opts
    assert first.carrier == "IndiGo" and first.price_per_person == 6123 and first.total_price == 6123 * 3
    assert "non-stop" in first.service and not first.is_estimate
    assert second.carrier == "Air India" and "1 stop" in second.service and second.duration_min == 330


def test_parse_hours():
    assert parse_hours("9 AM–6 PM") == "09:00–18:00"
    assert parse_hours("9:30 AM–5:30 PM") == "09:30–17:30"
    assert parse_hours("10 AM–1 PM, 2–5:30 PM") == "10:00–17:30"
    assert parse_hours("6–10 PM") == "18:00–22:00"
    assert parse_hours("Open 24 hours") == "Open 24 hours"
    assert parse_hours("Closed") == "Closed today"
    assert parse_hours(None) == "Hours not listed"


def test_parse_hotels_rooms_and_nights():
    raw = {"properties": [
        {"name": "Sea Breeze Inn", "rate_per_night": {"extracted_lowest": 2800},
         "gps_coordinates": {"latitude": 15.55, "longitude": 73.75}, "overall_rating": 4.2, "reviews": 900,
         "extracted_hotel_class": 3, "amenities": ["Pool"], "link": "https://example.com"},
        {"name": "No Price Hotel", "gps_coordinates": {"latitude": 15.5, "longitude": 73.8}},
    ]}
    hotels = parse_hotels(raw, GOI, date(2026, 11, 12), date(2026, 11, 16), 3)
    assert len(hotels) == 1
    h = hotels[0]
    assert h.rooms == 2 and h.total_price == 2800 * 2 * 4
    assert h.links[0].label == "Hotel website"


def test_parse_places_classifies_and_estimates():
    raw = {"local_results": [
        {"title": "Fort Aguada", "place_id": "abc", "gps_coordinates": {"latitude": 15.49, "longitude": 73.77},
         "rating": 4.4, "types": ["Fort", "Tourist attraction"], "operating_hours": {"monday": "9:30 AM–6 PM"}},
        {"title": "Baga Beach", "place_id": "def", "gps_coordinates": {"latitude": 15.55, "longitude": 73.75},
         "type": "Beach"},
        {"title": "Shut Museum", "gps_coordinates": {"latitude": 15.5, "longitude": 73.8}, "type": "Museum",
         "operating_hours": {"monday": "Closed", "tuesday": "Closed"}},
    ]}
    places, tags = parse_places(raw, GOI)
    assert [p.name for p in places] == ["Fort Aguada", "Baga Beach"]
    fort, beach = places
    assert fort.category == "history" and fort.fee_is_estimate and fort.hours == "09:30–18:00"
    assert beach.category == "beaches" and beach.fee_per_person == 0


def test_restaurant_cost_parsing():
    assert _cost_per_person("₹200–400") == 300
    assert _cost_per_person("₹1,000+") == 1000
    assert _cost_per_person("₹₹") == 500
    assert _cost_per_person(None) == 450
    assert _cost_per_person(None, ["Cafe"]) == 250 and _cost_per_person(None, ["Steak house"]) == 1200
    raw = {"local_results": [{"title": "Shack", "gps_coordinates": {"latitude": 15.5, "longitude": 73.7},
                              "price": "₹400–600", "type": "Seafood restaurant"}]}
    assert parse_restaurants(raw, GOI)[0].cost_per_person == 500
