"""Parsing open data (Wikidata, Wikivoyage, OpenStreetMap via Geoapify) into sights and restaurants."""

import asyncio
from unittest.mock import patch

import pytest

from app.config import get_settings
from app.models.schemas import Place
from app.providers import open_places
from app.providers.geocode import resolve_city
from app.providers.live_destination import clean_name
from app.providers.open_places import (_first_sentence, drop_spelling_variants, listing_fields, parse_fee,
                                       parse_wikidata, parse_wikivoyage)
from tests.open_fixtures import replay

GOA, JAIPUR = resolve_city("Goa"), resolve_city("Jaipur")


def _row(qid, name, types, links, lat=15.5, lng=73.9, desc=""):
    return {"item": {"value": f"http://www.wikidata.org/entity/{qid}"}, "itemLabel": {"value": name},
            "itemDescription": {"value": desc}, "lat": {"value": str(lat)}, "lon": {"value": str(lng)},
            "links": {"value": str(links)}, "types": {"value": types}}


def test_wikidata_keeps_sights_and_skips_everything_else():
    raw = {"results": {"bindings": [
        _row("Q1", "Basilica of Bom Jesus", "church building|minor basilica", 25),
        _row("Q2", "Dabolim Airport", "airport", 33),
        _row("Q3", "Calangute", "village in India", 29),
        _row("Q4", "Mandovi River", "river", 24),
        _row("Q5", "Goa University", "university", 8),
        _row("Q6", "Zuari Bridge", "road bridge", 3),
        _row("Q7", "Q4501091", "built structure", 2),
        _row("Q8", "Roman Catholic Diocese of Goa", "diocese|cathedral", 12),
        _row("Q9", "Fort Aguada", "fort", 12),
    ]}}
    places, tags, settlements = parse_wikidata(raw, GOA)
    assert [p.name for p in places] == ["Basilica of Bom Jesus", "Fort Aguada"]
    assert places[0].rating > places[1].rating and not places[0].rating_known
    assert places[0].category == "history"
    assert [s[0] for s in settlements] == ["Calangute"]


def test_wikivoyage_listings():
    body = ("name=Amber Fort | alt= | url= | lat=26.9855 | long=75.8513 | hours=8AM-6PM | "
            "price=₹100 (Indians), ₹500 (foreigners) | content=This [[Rajput|Rajput]] fort-palace&nbsp;is huge. More text.")
    f = listing_fields(body)
    assert f["name"] == "Amber Fort" and f["lat"] == "26.9855"
    wikitext = ("{{see|" + body + "}}\n{{eat|name=LMB|lat=26.92|long=75.82|price=₹200-400}}\n"
                "{{see|name=No coordinates here}}")
    sights, food = parse_wikivoyage({"parse": {"title": "Jaipur", "wikitext": {"*": wikitext}}}, JAIPUR)
    (fort, qid), = sights
    assert fort.fee_per_person == 100 and not fort.fee_is_estimate
    assert fort.hours == "08:00–18:00" and fort.description == "This Rajput fort-palace is huge."
    assert food[0].name == "LMB" and food[0].cost_per_person == 300


def test_fees_and_descriptions_from_wikivoyage_text():
    assert parse_fee("Rs. 50 for Indians, Rs. 200 others") == 50
    assert parse_fee("Free entry") == 0
    assert parse_fee("Donations welcome") is None
    assert _first_sentence("Built by the king {{circa|1799}}. It has 953 windows.") == "Built by the king ."


def test_names_keep_old_goa_whole():
    assert clean_name("Old Goa", GOA) == "Old Goa"
    assert clean_name("Churches and Convents of Goa", GOA) == "Churches and Convents of Goa"
    assert clean_name("Calangute Beach Goa", GOA) == "Calangute Beach"


def test_spelling_variants_are_merged():
    def place(name, rating):
        return Place(id=name, name=name, category="nature", area="Manali", rating=rating, lat=32.3, lng=77.2,
                     fee_per_person=0, duration_min=60, hours="", description="")
    kept = drop_spelling_variants([place("Brighu Lake", 4.2), place("Bhrigu Lake", 4.5), place("Rahala waterfalls", 4.3),
                                   place("Rehala Falls", 4.4), place("Beas Kund", 4.3)])
    assert sorted(p.name for p in kept) == ["Beas Kund", "Bhrigu Lake", "Rehala Falls"]


@pytest.mark.parametrize("city,expect", [
    ("Jaipur", {"Hawa Mahal", "Amber Fort", "City Palace", "Jantar Mantar"}),
    ("Goa", {"Basilica of Bom Jesus", "Se Cathedral", "Calangute Beach"}),
    ("Manali", {"Hidimba Devi Temple", "Solang Valley", "Rohtang Pass"}),
    ("Gokarna", {"Om Beach", "Kudle Beach", "Mahabaleshwar Temple"}),
])
def test_real_saved_responses(monkeypatch, city, expect):
    monkeypatch.setattr(get_settings(), "geoapify_key", "test-key")
    with patch.object(open_places, "cached_get", replay(city)):
        places, tags, food, credits = asyncio.run(open_places.fetch_open(resolve_city(city)))
    assert expect <= {p.name for p in places}
    assert len(food) >= 20 and all(r.cost_per_person > 0 for r in food)
    assert all(p.area and "taluk" not in p.area.lower() for p in places)
    assert all("&nbsp;" not in p.description for p in places)
    assert len({p.name.lower() for p in places}) == len(places)
