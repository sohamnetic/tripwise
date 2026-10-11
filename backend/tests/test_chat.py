""""Ask Tripwise": season ratings, rough costs, recommendations, reading plain messages, and the chat
endpoint with Gemini faked (no network)."""

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import delete

from app.config import get_settings
from app.db import ApiCall, ChatMessage, get_session, init_db
from app.main import app
from app.models.schemas import ChatTurn
from app.providers.geocode import resolve_city
from app.services import chat
from app.services.recommend import destinations, find_destinations, rough_cost, season

TODAY = date(2026, 10, 11)


@pytest.fixture(autouse=True)
def clean():
    init_db()
    with get_session() as s:
        s.exec(delete(ChatMessage))
        s.exec(delete(ApiCall))
        s.commit()


# ---- seasons ---------------------------------------------------------------------------------------

def test_seasons_follow_real_weather_and_closures():
    assert season("Goa", 7).rating == "Avoid" and "Monsoon" in season("Goa", 7).reason
    assert season("Goa", 12).rating == "Great"
    assert season("Manali", 5).rating in ("Great", "Good")
    leh = season("Leh", 1)
    assert leh.rating == "Avoid" and "cold" in leh.reason.lower()
    assert season("Jim Corbett", 8).rating == "Closed"
    assert season("Rishikesh", 7).note.startswith("River rafting")
    assert season("Jaipur", 5).rating in ("Okay", "Avoid") and "hot" in season("Jaipur", 5).reason.lower()


# ---- costs ------------------------------------------------------------------------------------------

KOL, GOA, BALI = resolve_city("Kolkata"), resolve_city("Goa"), resolve_city("Bali")
START = date(2026, 12, 10)


def test_costs_scale_with_trip_and_style():
    base = rough_cost(GOA, KOL, START, 4, 2, "balanced")
    assert rough_cost(GOA, KOL, START, 7, 2, "balanced").mid > base.mid
    assert rough_cost(GOA, KOL, START, 4, 4, "balanced").mid > base.mid
    assert rough_cost(GOA, KOL, START, 4, 2, "luxury").mid > rough_cost(GOA, KOL, START, 4, 2, "budget").mid
    assert base.low < base.mid < base.high and base.includes_travel
    assert base.transport + base.stay + base.daily == base.mid


def test_transport_follows_the_style_and_abroad_costs_more():
    assert rough_cost(GOA, KOL, START, 4, 2, "budget").transport_mode == "train"
    assert rough_cost(GOA, KOL, START, 4, 2, "luxury").transport_mode == "flight"
    assert rough_cost(BALI, KOL, START, 4, 2, "balanced").mid > rough_cost(GOA, KOL, START, 4, 2, "balanced").mid
    no_origin = rough_cost(GOA, None, START, 4, 2, "balanced")
    assert not no_origin.includes_travel and no_origin.transport == 0


# ---- recommending -----------------------------------------------------------------------------------

def test_december_beaches_from_kolkata():
    found = find_destinations(month=12, budget=60000, travellers=2, origin="Kolkata", interests=["beaches"], today=TODAY)
    names = [s.name for s in found]
    assert len(found) == 4 and "Kolkata" not in names
    assert any(n in names for n in ("Goa", "Port Blair", "Havelock Island", "Puri", "Digha", "Gokarna"))
    assert all("beaches" in s.tags for s in found) and all(s.season.rating in ("Great", "Good") for s in found)
    assert all(s.cost.fits_budget for s in found)
    assert found[0].prefill.origin == "Kolkata" and found[0].prefill.start_date == date(2026, 12, 10)


def test_closed_and_abroad_places_are_left_out_unless_asked():
    august = [s.name for s in find_destinations(month=8, interests=["wildlife"], limit=8, today=TODAY)]
    assert not {"Jim Corbett", "Ranthambore", "Gir", "Kaziranga"} & set(august)
    assert not any(s.name in ("Bali", "Dubai", "Bangkok") for s in find_destinations(month=1, limit=8, today=TODAY))
    abroad = find_destinations(month=1, interests=["abroad"], today=TODAY)
    assert all("abroad" in s.tags for s in abroad)


def test_a_tight_budget_prefers_what_fits():
    found = find_destinations(month=11, budget=15000, travellers=2, origin="Delhi", today=TODAY)
    assert found[0].cost.fits_budget or found[0].cost.low <= 15000 * 1.1


# ---- reading plain messages --------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Somewhere cool in May under ₹40k for 2 from Kolkata",
     {"month": 5, "budget": 40000, "travellers": 2, "origin": "Kolkata", "interests": ["cool"]}),
    ("family of 4 beach trip in december, budget 1.5 lakh from bombay",
     {"month": 12, "budget": 150000, "travellers": 4, "origin": "Mumbai", "interests": ["beaches"]}),
    ("Is Goa good in July?", {"month": 7, "destination": "Goa"}),
    ("Long weekend from Bengaluru", {"nights": 3, "origin": "Bengaluru"}),
    ("solo trip next month under 25000", {"month": 11, "travellers": 1, "budget": 25000}),
    ("luxury honeymoon in feb, 5 nights", {"month": 2, "style": "luxury", "travellers": 2, "nights": 5}),
])
def test_reading_trip_details(text, expected):
    got = chat.parse_request(text, TODAY)
    for key, value in expected.items():
        assert got.get(key) == value, (key, got)


# ---- the chat ----------------------------------------------------------------------------------------------

def _ask(*texts):
    return [ChatTurn(role="user" if i % 2 == 0 else "assistant", text=t) for i, t in enumerate(texts)]


def test_simple_mode_without_a_key():
    r = chat.answer(_ask("Beach trip in December under ₹60k for 2 from Kolkata"), TODAY)
    assert r.mode == "simple" and r.suggestions
    assert "December" in r.reply and "₹60,000" in r.reply


def test_simple_mode_about_one_place():
    r = chat.answer(_ask("Is Goa good in July?"), TODAY)
    assert r.mode == "simple" and [s.name for s in r.suggestions] == ["Goa"]
    assert "avoid" in r.reply.lower()


def test_simple_mode_remembers_earlier_details():
    r = chat.answer(_ask("Hills in May from Kolkata", "Here are some…", "make it under 30k"), TODAY)
    assert all(s.prefill.origin == "Kolkata" and s.season.month == 5 for s in r.suggestions)
    assert all(s.cost.fits_budget is not None for s in r.suggestions)


def test_gemini_uses_our_tools_and_the_cards_carry_our_numbers(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    replies = iter([
        {"role": "model", "parts": [{"functionCall": {"name": "find_destinations", "args": {
            "month": 5, "budget": 40000, "travellers": 2, "origin": "Kolkata", "interests": ["mountains"]}}}]},
        {"role": "model", "parts": [{"text": "May is lovely in the hills. Here are a few ideas."}]},
    ])
    sent = []

    def fake_gemini(contents, today, timeout=25):
        sent.append([dict(c) for c in contents])
        return next(replies)

    with patch.object(chat, "_gemini", fake_gemini):
        r = chat.answer(_ask("Somewhere cool in May under ₹40k for 2 from Kolkata"), TODAY)
    assert r.mode == "ai" and r.reply.startswith("May is lovely")
    expected = find_destinations(month=5, budget=40000, travellers=2, origin="Kolkata", interests=["mountains"], today=TODAY)
    assert [(s.name, s.cost.mid) for s in r.suggestions] == [(s.name, s.cost.mid) for s in expected]
    # the tool's result went back to the model as a function response
    response_turn = sent[1][-1]["parts"][0]["functionResponse"]
    assert response_turn["name"] == "find_destinations" and response_turn["response"]["places"]


def test_gemini_failure_falls_back_to_simple_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")

    def broken(contents, today, timeout=25):
        raise chat.GeminiUnavailable("HTTP 503")

    with patch.object(chat, "_gemini", broken):
        r = chat.answer(_ask("Beaches in January"), TODAY)
    assert r.mode == "simple" and r.suggestions


def test_gemini_daily_cap_is_respected(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "gemini_daily_limit", 1)
    with get_session() as s:
        s.add(ApiCall(provider="gemini", at=datetime.now(timezone.utc)))
        s.commit()
    with pytest.raises(chat.GeminiUnavailable, match="cap"):
        chat._gemini([], TODAY)  # refused before any network call
    assert chat.answer(_ask("Beaches in January"), TODAY).mode == "simple"


def test_chat_endpoint_and_visitor_limit(monkeypatch):
    monkeypatch.setattr(get_settings(), "chat_daily_messages", 2)
    body = {"messages": [{"role": "user", "text": "Hills in June under 40k from Delhi"}]}
    with TestClient(app) as c:
        first = c.post("/api/chat", json=body)
        assert first.status_code == 200 and first.json()["mode"] == "simple" and first.json()["suggestions"]
        assert c.post("/api/chat", json=body).status_code == 200
        limited = c.post("/api/chat", json=body)
        assert limited.status_code == 429 and "daily limit" in limited.json()["detail"]
        bad = c.post("/api/chat", json={"messages": [{"role": "assistant", "text": "hi"}]})
        assert bad.status_code == 422


def test_simple_mode_says_when_it_shortened_the_trip_to_fit():
    r = chat.answer(_ask("Somewhere in November under 15000 for 2 from Delhi"), TODAY)
    assert "2-night budget-style trip" in r.reply and all(s.cost.fits_budget for s in r.suggestions)


def test_budget_amount_is_not_a_travel_style():
    got = chat.parse_request("family of 4 beach trip in december, budget 1.5 lakh from bombay", TODAY)
    assert "style" not in got and got["budget"] == 150000
    r = chat.answer(_ask("family of 4 beach trip in december, budget 1.5 lakh from bombay"), TODAY)
    assert r.suggestions[0].name == "Goa"


def test_high_altitude_temperatures_are_marked_approximate():
    leh = season("Leh", 6)
    assert leh.weather.startswith("≈") and "approximate" in leh.note
    assert not season("Manali", 6).weather.startswith("≈")


def test_somewhere_cool_means_cool_temperatures():
    found = find_destinations(month=5, travellers=2, origin="Kolkata", interests=["cool"], today=TODAY)
    assert all(s.season.tmax <= 27 for s in found), [(s.name, s.season.tmax) for s in found]


def test_asking_about_one_place_in_a_month_gives_a_card():
    info, cards = chat.run_tool("destination_info", {"destination": "Goa", "month": 7}, TODAY)
    assert info["month"]["rating"] == "Avoid" and [c.name for c in cards] == ["Goa"]
    _, none = chat.run_tool("destination_info", {"destination": "Goa"}, TODAY)
    assert none == []


def test_tool_call_ids_are_echoed_back(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    replies = iter([
        {"role": "model", "parts": [{"functionCall": {"name": "estimate_trip", "args": {"destination": "Goa", "month": 12}, "id": "call_1"}}]},
        {"role": "model", "parts": [{"text": "December is great for Goa."}]},
    ])
    sent = []
    with patch.object(chat, "_gemini", lambda contents, today, timeout=25: (sent.append(contents), next(replies))[1]):
        chat.answer(_ask("Goa in December?"), TODAY)
    assert sent[-1][-1]["parts"][0]["functionResponse"]["id"] == "call_1"


def test_big_cities_only_when_asked_for():
    beaches = [s.name for s in find_destinations(month=12, travellers=2, origin="Kolkata", interests=["beaches"], today=TODAY)]
    assert "Mumbai" not in beaches and "Chennai" not in beaches
    cities = [s.name for s in find_destinations(month=12, interests=["cities"], today=TODAY)]
    assert all("cities" in destinations()[n]["tags"] for n in cities)
