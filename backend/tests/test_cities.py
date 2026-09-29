import json
import re
from pathlib import Path

import pytest

from app.providers.geocode import _cities, resolve_city, search_cities

ROOT = Path(__file__).resolve().parents[2]


def test_every_city_is_well_formed():
    for c in _cities():
        assert re.fullmatch(r"[A-Z]{3}", c["iata"]), c["name"]
        assert -40 < c["lat"] < 40 and 50 < c["lng"] < 120, c["name"]
        assert resolve_city(c["name"]).name == c["name"]
        for alias in c["aliases"]:
            assert resolve_city(alias).name == c["name"], alias


@pytest.mark.parametrize("query,expected", [
    ("havelock", "Havelock Island"), ("mcleod ganj", "Dharamshala"), ("ajanta", "Aurangabad"),
    ("rann of kutch", "Bhuj"), ("vrindavan", "Mathura"), ("corbett", "Jim Corbett"), ("trivandrum", "Thiruvananthapuram"),
])
def test_popular_aliases(query, expected):
    assert resolve_city(query).name == expected


def test_search_prefix_first():
    assert search_cities("ha")[0].name in {"Hyderabad", "Haridwar", "Hampi", "Havelock Island"}


def test_every_city_has_a_scene_on_the_frontend():
    """frontend/src/lib/vibes.ts must have a look for every city we can plan."""
    src = (ROOT / "frontend" / "src" / "lib" / "vibes.ts").read_text(encoding="utf-8")
    looks = set(re.findall(r'^\s+"?([a-z ]+)"?: \[S\(', src, re.M))
    cities = {c["name"].lower() for c in _cities()}
    assert cities == looks, {"missing look": cities - looks, "look without city": looks - cities}
