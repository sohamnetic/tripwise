"""Replays saved Wikidata / Wikivoyage / Geoapify responses (tests/fixtures/open) instead of the network."""

import json
from pathlib import Path

FIX = Path(__file__).parent / "fixtures" / "open"


def replay(city_name: str):
    food_calls = {"n": 0}

    async def fake_cached_get(url, params, ttl_hours, secret=None, headers=None):
        if "wikidata" in url:
            kind = "wikidata"
        elif "wikivoyage" in url:
            kind = "wikivoyage"
        elif params["categories"] == "beach":
            kind = "geo_beach"
        else:
            kind = f"geo_food{food_calls['n']}"
            food_calls["n"] += 1
        path = FIX / f"{city_name.lower()}_{kind}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"features": []}

    return fake_cached_get
